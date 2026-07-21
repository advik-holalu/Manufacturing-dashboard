"""Tab 0 - Overview. State of the factory as clean KPI cards (native dark).

Each tile reads its OWN sheet's latest available day within the selected window,
and where a comparable prior period exists it shows a st.metric delta. Every
value is guarded against nan / divide-by-zero - a tile shows "-" rather than a
fake number.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd
import streamlit as st

from utils.ui import section, clip_range, resolve_spec, _days, context_text
from tabs.wip_new import wip_snapshot

LIVE_KEYS = ["mfg", "cooking_target", "wip_new", "cut_pieces"]

# Fixed height for all four KPI cards so the row stays level regardless of how
# many lines each sub-caption wraps to. Comfortably fits label + metric +
# delta + a two-line caption without clipping.
CARD_HEIGHT = 240


def _asof_window(sheet: pd.DataFrame, range_spec):
    """(frame, latest_day) for a sheet, resolving the spec against its OWN dates."""
    if "Date" not in sheet.columns:
        return sheet, None
    s = sheet.dropna(subset=["Date"])
    if s.empty:
        return s, None
    win = clip_range(sheet, range_spec).dropna(subset=["Date"])
    if win.empty:                       # e.g. a Custom range outside this sheet
        day = s["Date"].max()
        return s[s["Date"] == day], day
    return win, win["Date"].max()


def _previous_frame(sheet: pd.DataFrame, range_spec):
    """Rows of the comparable prior period, or None if there is no data to
    compare against. Single-day windows compare to the previous day that
    actually exists; multi-day windows to the equal-length window before."""
    if "Date" not in sheet.columns:
        return None
    days = _days(sheet)
    if not days:
        return None
    win = resolve_spec(days, range_spec) if range_spec else (days[-1], days[-1])
    if not win:
        return None
    start, end = win
    if start == end:
        earlier = [d for d in days if d < start]
        if not earlier:
            return None
        ps = pe = earlier[-1]
    else:
        dur = end - start
        pe = start - timedelta(days=1)
        ps = start - (dur + timedelta(days=1))
    d = sheet.dropna(subset=["Date"])
    prev = d[(d["Date"].dt.date >= ps) & (d["Date"].dt.date <= pe)]
    return prev if not prev.empty else None


def _asof(day) -> str:
    return day.strftime("%d %b %Y") if day is not None else "no data"


def render(dfs: dict, date_range=None) -> None:
    section("State of the factory")
    live_dates = [dfs[k]["Date"] for k in LIVE_KEYS
                  if k in dfs and "Date" in dfs[k].columns]
    live_days = (sorted(set(pd.concat(live_dates).dropna().dt.date))
                 if live_dates else [])
    st.info(context_text(live_days, date_range))

    c1, c2, c3, c4 = st.columns(4)

    # --- Production (MFG) -------------------------------------------------
    with c1:
        with st.container(border=True, height=CARD_HEIGHT):
            win, day = _asof_window(dfs["mfg"], date_range)
            total = win["TOTAL PRODUCTION"].sum() if not win.empty else 0
            last_kg = (win.loc[win["Date"] == day, "TOTAL PRODUCTION"].sum()
                       if day is not None else 0)
            prev = _previous_frame(dfs["mfg"], date_range)
            delta = None
            if prev is not None:
                diff = total - prev["TOTAL PRODUCTION"].sum()
                delta = f"{diff:+,.0f} kg"
            st.metric("Production", f"{total:,.0f} kg", delta=delta)
            st.caption(f"Latest day {last_kg:,.0f} kg - MFG as of {_asof(day)}")

    # --- Plan vs actual (Cooking Target) ---------------------------------
    with c2:
        with st.container(border=True, height=CARD_HEIGHT):
            win, day = _asof_window(dfs["cooking_target"], date_range)
            tgt = win["Target"].sum() if not win.empty else 0
            ach = win["Achieved"].sum() if not win.empty else 0
            pct = (ach / tgt * 100) if tgt else None
            val = f"{pct:,.0f}%" if pct is not None else "-"
            delta = None
            prev = _previous_frame(dfs["cooking_target"], date_range)
            if pct is not None and prev is not None:
                ptgt = prev["Target"].sum()
                if ptgt:
                    delta = f"{pct - prev['Achieved'].sum() / ptgt * 100:+,.0f} pts"
            st.metric("Plan vs actual", val, delta=delta)
            ctx = f"{ach:,.0f} of {tgt:,.0f} kg" if tgt else "No plan in window"
            st.caption(f"{ctx} - Cooking Target as of {_asof(day)}")

    # --- In WIP now (WIP New) --------------------------------------------
    with c3:
        with st.container(border=True, height=CARD_HEIGHT):
            win, day = _asof_window(dfs["wip_new"], date_range)
            snap = wip_snapshot(win)
            # No delta: WIP is a live snapshot position, not a period-over-period
            # metric - comparing to a prior period would be meaningless and the
            # "down = good" colouring would falsely imply less WIP is better.
            # Boxes go in the metric value; pieces on their own line so both are
            # fully visible - the combined string truncates in st.metric.
            if snap["latest"] is None:
                st.metric("In WIP now", "-")
            else:
                st.metric("In WIP now", f"{snap['box_qty']:,.0f} boxes")
                st.caption(f"+ {snap['piece_qty']:,.0f} pieces")
            st.caption(f"{snap['beyond']:,.0f} aged beyond 2 days - WIP as of "
                       f"{_asof(snap['latest'])}")

    # --- Latest yield (Conversion) - no delta, guarded against nan -------
    with c4:
        with st.container(border=True, height=CARD_HEIGHT):
            win, day = _asof_window(dfs["conversion"], date_range)
            val, ctx = "-", "No records in window"
            if day is not None:
                last = win[win["Date"] == day]
                series = last["% Achieved Mail"].dropna()
                if len(series):
                    y = series.mean() * 100
                    if pd.notna(y):
                        val = f"{y:,.0f}%"
                        ctx = (f"mean across "
                               f"{last['Item Name'].nunique():,.0f} products")
            st.metric("Latest yield", val)
            st.caption(f"{ctx} - Conversion as of {_asof(day)}")
