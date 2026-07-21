"""
Data layer - the anti-crash core.

Two-stage caching so Streamlit Cloud never re-does work on every click:
  Stage 1  load_sheet()   -> fetches + cleans ONE sheet, cached by name.
  Stage 2  the tabs       -> slice the already-clean frame (cheap).

Data source is controlled by DATA_SOURCE in config:
  "sample" -> reads bundled CSVs in /sample_data (works with zero setup)
  "gsheets" -> reads the live Google Sheet via a service account

Switching to live data = flip DATA_SOURCE to "gsheets" and add the
service-account secrets. Nothing else changes; the tabs are agnostic.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from utils.config import DATA_SOURCE, GSHEET_ID

# Logical sheet keys -> the exact tab name inside the Google Sheet.
# (Edit the right-hand side if the real sheet tabs are named differently.)
SHEETS = {
    "mfg": "MFG",
    "cooking_target": "Cooking Target",
    "wip_new": "WIP New",
    "cut_pieces": "Cut pieces",
    "conversion": "Conversion",
}

# How long a fetched sheet stays cached before a re-fetch (seconds).
# 300 = 5 min. Raise it if the sheet is edited infrequently.
CACHE_TTL = 300


# --------------------------------------------------------------------------
# Stage 1: fetch + clean, cached per sheet
# --------------------------------------------------------------------------
@st.cache_data(ttl=CACHE_TTL, show_spinner="Loading data...")
def load_sheet(sheet_name: str) -> pd.DataFrame:
    """Fetch one sheet and return a cleaned, analysis-ready dataframe.

    Cached by sheet_name, so each sheet is fetched at most once per TTL
    window and shared across every user and every rerun.
    """
    if DATA_SOURCE == "gsheets":
        raw = _fetch_gsheet(sheet_name)
    else:
        raw = _fetch_sample(sheet_name)

    return _clean(sheet_name, raw)


# --------------------------------------------------------------------------
# Fetchers
# --------------------------------------------------------------------------
def _fetch_sample(sheet_name: str) -> pd.DataFrame:
    """Read a bundled CSV so the app runs with zero cloud setup."""
    key = _key_for(sheet_name)
    return pd.read_csv(f"sample_data/{key}.csv")


def _fetch_gsheet(sheet_name: str) -> pd.DataFrame:
    """Read one tab of the live Google Sheet via a service account.

    Requires:
      - st.secrets["gcp_service_account"]  (the JSON key, as TOML)
      - the Sheet shared (view) with that service-account email
    """
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(creds)
    ws = client.open_by_key(GSHEET_ID).worksheet(sheet_name)
    # get_all_values keeps blank cells as "", which we handle in _clean.
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    header, *rows = values
    return pd.DataFrame(rows, columns=header)


# --------------------------------------------------------------------------
# Cleaning - per sheet, all vectorized
# --------------------------------------------------------------------------
def _clean(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
    key = _key_for(sheet_name)
    if df.empty:
        return df

    # Trim ghost/unnamed columns from Google Sheets.
    df = df.loc[:, [c for c in df.columns if c and not str(c).startswith("Unnamed")]]

    cleaner = {
        "mfg": _clean_mfg,
        "cooking_target": _clean_cooking_target,
        "wip_new": _clean_ageing,
        "cut_pieces": _clean_ageing,
        "conversion": _clean_conversion,
    }[key]
    return cleaner(df)


def _to_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def _to_date(s: pd.Series) -> pd.Series:
    # Tolerant parse. Sample CSVs are ISO; the live sheet (gspread) returns
    # each cell as TEXT in its display format - dd/mm/yyyy on most sheets, but
    # the Conversion sheet displays dates year-less (e.g. "20-May"), which
    # pandas parses with year 0001. Re-anchor those to a real year.
    out = pd.to_datetime(s, errors="coerce", format="mixed", dayfirst=True)

    missing = out.notna() & (out.dt.year < 100)
    if missing.any():
        today = pd.Timestamp.today().normalize()
        out.loc[missing] = out[missing].map(lambda d: _reanchor_year(d, today))
    return out


def _reanchor_year(d: pd.Timestamp, today: pd.Timestamp) -> pd.Timestamp:
    """Give a year-less parsed date (year 0001) a real year: the current year,
    rolled back one if that would put it in the future (handles a Dec/Jan wrap).
    """
    def _with_year(dt, year):
        try:
            return dt.replace(year=year)
        except ValueError:  # 29 Feb into a non-leap year
            return dt.replace(year=year, day=28)

    cand = _with_year(d, today.year)
    if cand > today:
        cand = _with_year(cand, today.year - 1)
    return cand


def _norm_shift(s: pd.Series) -> pd.Series:
    """Normalize messy shift labels to G/A/B/C.
    Handles lowercase, stray '2' (-> B), '.A' typo, and the 1/2/3 scheme.
    """
    m = {
        "1": "A", "2": "B", "3": "C", "G": "G", "A": "A", "B": "B", "C": "C",
    }
    cleaned = (
        s.astype(str).str.strip().str.upper().str.replace(".", "", regex=False)
    )
    return cleaned.map(m)


def _clean_mfg(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    df["Date"] = _to_date(df.get("Date"))
    for col in ["BATCH SIZE(KG)", "NO. OF BATCHES", "TOTAL PRODUCTION"]:
        if col in df:
            df[col] = _to_num(df[col])
    if "Shift" in df:
        df["Shift"] = _norm_shift(df["Shift"])
    if "LINE" in df:
        df["LINE"] = _to_num(df["LINE"])
    # Real records only = rows that name a product.
    df = df[df["Product Name"].notna() & (df["Product Name"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def _clean_cooking_target(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    df["Date"] = _to_date(df.get("Date"))
    for col in ["Target", "G - Done", "A-Done", "B-Done", "C-Done",
                "Achieved", "Achived %", "Pending"]:
        if col in df:
            df[col] = _to_num(df[col])
    # Drop the stray 'Shift' header-in-data and blank SKU rows.
    df = df[df["SKU Name"].notna() & (df["SKU Name"].astype(str).str.strip() != "")]
    df = df[df["SKU Name"].astype(str).str.strip().str.lower() != "shift"]
    return df.reset_index(drop=True)


def _clean_ageing(df: pd.DataFrame) -> pd.DataFrame:
    """Shared cleaner for WIP New and Cut pieces (same 7-col shape)."""
    df = df.rename(columns=lambda c: str(c).strip())
    df["Date"] = _to_date(df.get("Date"))
    if "Manufacturing Date" in df:
        df["Manufacturing Date"] = _to_date(df["Manufacturing Date"])
    if "Shift" in df:
        df["Shift"] = _norm_shift(df["Shift"])
    qty = "Number of boxes" if "Number of boxes" in df else "Weight"
    if qty in df:
        df[qty] = _to_num(df[qty])
    if "Ageing (Days)" in df:
        df["Ageing (Days)"] = _to_num(df["Ageing (Days)"])
    sku_col = "SKU" if "SKU" in df else df.columns[2]
    df = df[df[sku_col].notna() & (df[sku_col].astype(str).str.strip() != "")]
    # Negative ageing (mfg date after snapshot) is a data-entry error. Keep the
    # rows so the tabs can flag them; do not silently drop.
    return df.reset_index(drop=True)


def _clean_conversion(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns=lambda c: str(c).strip())
    df["Date"] = _to_date(df.get("Date"))
    for col in ["Actual", "Ideal Boxes", "Actual as mail WIP",
                "% Achieved Mail", "Ideal Conversion"]:
        if col in df:
            df[col] = _to_num(df[col])
    df = df[df["Item Name"].notna() & (df["Item Name"].astype(str).str.strip() != "")]
    return df.reset_index(drop=True)


def _key_for(sheet_name: str) -> str:
    for k, v in SHEETS.items():
        if v == sheet_name:
            return k
    return sheet_name
