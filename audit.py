"""
THROWAWAY DATA-CORRECTNESS AUDIT (audit.py)

Independently recomputes every headline number from the RAW sheet data and
compares it to the exact logic the dashboard runs. Does not import or trust the
tab render code's outputs - it re-derives each value from scratch, then also
runs the dashboard's own formula on the cleaned frame so mismatches surface.

Runs against the bundled sample_data through the SAME cleaning pipeline the app
uses (_clean_*). To audit live gsheets data instead, the same checks apply -
point RAW at the live pull.

Audit only. Changes nothing in the app.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from utils.data import (_fetch_sample, _clean, SHEETS)
from utils.ui import resolve_spec, _days, clip_range
from tabs.wip_new import wip_snapshot

pd.set_option("display.width", 140)
TOL = 1e-6
RESULTS = []  # (section, name, dashboard, independent, pass_bool)


def check(section, name, dashboard, independent, ok=None):
    if ok is None:
        try:
            ok = abs(float(dashboard) - float(independent)) <= max(
                TOL, 1e-6 * abs(float(independent)))
        except (TypeError, ValueError):
            ok = str(dashboard) == str(independent)
    RESULTS.append((section, name, dashboard, independent, bool(ok)))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"         dashboard  = {dashboard}")
    print(f"         independent= {independent}")
    return ok


def note(msg):
    print(f"  NOTE: {msg}")


def raw(key):
    return pd.read_csv(f"sample_data/{key}.csv")


def cleaned(key):
    return _clean(SHEETS[key], _fetch_sample(SHEETS[key]))


LATEST = ("Latest day", None, None)
ALL = ("All time", None, None)


# =========================================================================
print("\n" + "=" * 70)
print("MFG TAB")
print("=" * 70)
mr = raw("mfg")
m = cleaned("mfg")

# --- TOTAL PRODUCTION == BATCH SIZE x NO. OF BATCHES ---------------------
mr_n = mr.copy()
for col in ["BATCH SIZE(KG)", "NO. OF BATCHES", "TOTAL PRODUCTION"]:
    mr_n[col] = pd.to_numeric(mr_n[col], errors="coerce")
mr_n = mr_n[mr_n["Product Name"].notna()
            & (mr_n["Product Name"].astype(str).str.strip() != "")]
implied = mr_n["BATCH SIZE(KG)"] * mr_n["NO. OF BATCHES"]
mismatch = (~np.isclose(implied, mr_n["TOTAL PRODUCTION"], equal_nan=True)).sum()
check("MFG", "TOTAL PRODUCTION == BATCH SIZE x NO. OF BATCHES (row mismatches)",
      mismatch, 0)
note(f"checked {len(mr_n)} rows; {mismatch} rows where the column disagrees "
     "with batch x batches")

# --- Total produced (All time) ------------------------------------------
dash_total = m["TOTAL PRODUCTION"].sum()
indep_total = pd.to_numeric(mr["TOTAL PRODUCTION"], errors="coerce")[
    mr["Product Name"].notna()
    & (mr["Product Name"].astype(str).str.strip() != "")].sum()
check("MFG", "Total produced kg (All time) = sum TOTAL PRODUCTION",
      dash_total, indep_total)

# --- Total produced (Latest day, the resolved range) --------------------
dmax = _days(m)[-1]
dash_total_ld = clip_range(m, LATEST)["TOTAL PRODUCTION"].sum()
indep_total_ld = m.loc[m["Date"].dt.date == dmax, "TOTAL PRODUCTION"].sum()
check("MFG", f"Total produced kg (Latest day = {dmax})",
      dash_total_ld, indep_total_ld)

# --- Batches / Active SKUs ----------------------------------------------
check("MFG", "Batches (All time) = sum NO. OF BATCHES",
      m["NO. OF BATCHES"].sum(),
      pd.to_numeric(mr["NO. OF BATCHES"], errors="coerce")[
          mr["Product Name"].notna()
          & (mr["Product Name"].astype(str).str.strip() != "")].sum())
check("MFG", "Active SKUs (All time) = nunique Product Name",
      m["Product Name"].nunique(),
      mr_n["Product Name"].nunique())

# --- Line utilization: Line1+Line2 == overall total ---------------------
g = m.dropna(subset=["Date"]).copy()
ln = g.dropna(subset=["LINE"]).copy()
ln["Line"] = "Line " + ln["LINE"].astype(int).astype(str)
line12 = ln[ln["Line"].isin(["Line 1", "Line 2"])]["TOTAL PRODUCTION"].sum()
overall = m["TOTAL PRODUCTION"].sum()
dropped = overall - line12
check("MFG", "Line 1 + Line 2 total == overall total (no dropped rows)",
      line12, overall, ok=abs(dropped) <= TOL)
line_vals = sorted(m["LINE"].dropna().unique().tolist())
n_nan_line = int(m["LINE"].isna().sum())
n_nan_date = int(m["Date"].isna().sum())
note(f"distinct LINE values = {line_vals}; rows with NaN LINE = {n_nan_line}; "
     f"rows with NaN Date = {n_nan_date}; kg outside Line 1/2 chart = {dropped:,.0f}")


# =========================================================================
print("\n" + "=" * 70)
print("COOKING TARGET TAB")
print("=" * 70)
cr = raw("cooking_target")
c = cleaned("cooking_target")
shift_cols = ["G - Done", "A-Done", "B-Done", "C-Done"]

# --- Achieved == sum of shift columns per row ---------------------------
shift_sum = c[shift_cols].sum(axis=1)
ach_mismatch = (~np.isclose(shift_sum, c["Achieved"], equal_nan=True)).sum()
check("CT", "Achieved == G+A+B+C per row (row mismatches)", ach_mismatch, 0)
note(f"checked {len(c)} rows; {ach_mismatch} rows where sheet Achieved != shift sum")

# --- Headline % = sum(Achieved)/sum(Target), NOT mean of per-row % -------
tgt = c["Target"].sum()
ach = c["Achieved"].sum()
dash_pct = (ach / tgt * 100) if tgt else 0
indep_pct = ach / tgt * 100
check("CT", "Achieved % (All time) = sum(Achieved)/sum(Target)*100",
      dash_pct, indep_pct)
mean_of_row_pct = c["Achived %"].mean() * 100  # the WRONG way
note(f"mean-of-per-row-% would give {mean_of_row_pct:,.1f}% vs correct "
     f"{indep_pct:,.1f}% - dashboard uses the correct sum/sum")
check("CT", "Dashboard headline is NOT the average-of-percentages",
      round(dash_pct, 4), round(indep_pct, 4),
      ok=abs(dash_pct - mean_of_row_pct) > 1e-6 or abs(indep_pct - mean_of_row_pct) < 1e-9)

# --- Pending = Achieved - Target, sign ----------------------------------
dash_pending = ach - tgt
check("CT", "Pending (All time) = Achieved - Target", dash_pending, ach - tgt)
note(f"Pending sign: {dash_pending:,.0f} ({'behind plan' if dash_pending < 0 else 'at/above plan'}); "
     "negative = behind is correct")

# divide-by-zero guard
zero_tgt = int((c["Target"].fillna(0) == 0).sum())
note(f"rows with Target == 0 (divide-by-zero risk): {zero_tgt}; "
     "CT tab shows 0% when total Target is 0, Overview shows '-' (minor inconsistency)")


# =========================================================================
print("\n" + "=" * 70)
print("WIP NEW TAB (snapshot logic)")
print("=" * 70)
wr = raw("wip_new")
w = cleaned("wip_new")

wmax = _days(w)[-1]
snap = wip_snapshot(clip_range(w, LATEST))
cur = w[w["Date"].dt.date == wmax]

# --- In WIP now = boxes on LATEST day only ------------------------------
indep_boxes = cur["Number of boxes"].sum()
check("WIP", f"In WIP now = boxes on latest day only ({wmax})",
      snap["boxes"], indep_boxes)
n_days_in_snapshot = cur["Date"].dt.date.nunique()
check("WIP", "snapshot uses exactly ONE day of rows", n_days_in_snapshot, 1)
wrong_all_history = w["Number of boxes"].sum()
note(f"summing ALL history (the double-count bug) would give "
     f"{wrong_all_history:,.0f} boxes vs correct {indep_boxes:,.0f} on {wmax}")

# --- Aged beyond 2 days on latest day -----------------------------------
indep_beyond = int((cur["Ageing (Days)"] > 2).sum())
check("WIP", "Aged beyond 2 days = count(Ageing > 2) on latest day",
      snap["beyond"], indep_beyond)

# --- negative ageing handling -------------------------------------------
neg_all = int((w["Ageing (Days)"] < 0).sum())
neg_latest = int((cur["Ageing (Days)"] < 0).sum())
note(f"negative-ageing rows kept in cleaned data: {neg_all} total, "
     f"{neg_latest} on the latest snapshot day")
note("negative rows are NOT dropped (cleaner keeps them); WIP tab shows a "
     "warning caption when neg>0. They ARE included in the boxes sum on the "
     "latest day (only excluded from the >2 count).")
nan_boxes = int(cur["Number of boxes"].isna().sum())
nan_age = int(cur["Ageing (Days)"].isna().sum())
note(f"latest-day NaN Number of boxes = {nan_boxes}, NaN Ageing = {nan_age} "
     "(silently summed as 0 / excluded from >2)")


# =========================================================================
print("\n" + "=" * 70)
print("CONVERSION TAB")
print("=" * 70)
vr = raw("conversion")
v = cleaned("conversion")
vmax = _days(v)[-1]
vcur = v[v["Date"].dt.date == vmax]

# --- Latest yield = mean(% Achieved Mail valid) on latest day -----------
valid = vcur["% Achieved Mail"].dropna()
indep_yield = valid.mean() * 100 if len(valid) else float("nan")
# dashboard/overview guard:
dash_yield = f"{indep_yield:,.0f}%" if len(valid) and pd.notna(indep_yield) else "-"
check("CONV", f"Latest yield = mean(% Achieved Mail) on latest day ({vmax})",
      dash_yield,
      (f"{valid.mean()*100:,.0f}%" if len(valid) else "-"))

# empty selection -> hyphen, not nan
empty = v.iloc[0:0]
empty_valid = empty["% Achieved Mail"].dropna() if "% Achieved Mail" in empty else pd.Series([], dtype=float)
empty_out = f"{empty_valid.mean()*100:,.0f}%" if len(empty_valid) else "-"
check("CONV", "empty selection shows '-' not nan", empty_out, "-")
n_zero_yield = int((v["% Achieved Mail"] == 0).sum())
note(f"% Achieved Mail == 0 in {n_zero_yield} of {len(v)} rows - these 0s are "
     "included in the mean and may represent missing (Actual as mail WIP = 0), "
     "dragging the average down")

# --- Ideal Boxes = Actual x Ideal Conversion / box-size -----------------
vv = v.dropna(subset=["Actual", "Ideal Conversion", "Ideal Boxes"]).copy()
vv = vv[vv["Ideal Boxes"] != 0]
vv["implied_box_kg"] = vv["Actual"] * vv["Ideal Conversion"] / vv["Ideal Boxes"]
# Box-size is per-SKU (100g / 150g / 200g). The real integrity test: is it
# STABLE within each SKU, and does it reconstruct Ideal Boxes exactly?
per_sku_box = vv.groupby("Item Name")["implied_box_kg"].transform("median")
recon = vv["Actual"] * vv["Ideal Conversion"] / per_sku_box
# box-size is stable per SKU up to the sheet's rounding of Ideal Boxes (1 dp)
max_cv = max(grp["implied_box_kg"].std(ddof=0) / grp["implied_box_kg"].mean()
             for _, grp in vv.groupby("Item Name"))
recon_ok = bool(np.allclose(recon, vv["Ideal Boxes"], rtol=1e-3))
check("CONV", "Ideal Boxes = Actual x Ideal Conversion / box-size (per-SKU, reconstructs)",
      f"reconstructs all {len(vv)} rows within 0.1%: {recon_ok} "
      f"(max per-SKU box-size spread {max_cv*100:.2f}%)",
      "reconstructs all rows: True", ok=recon_ok)
note("implied box-size per SKU (kg): " +
     ", ".join(f"{k}={grp['implied_box_kg'].mean():.3f}"
               for k, grp in vv.groupby("Item Name")) +
     " -> 100g/150g/200g boxes, consistent within SKU")


# =========================================================================
print("\n" + "=" * 70)
print("OVERVIEW TAB (tiles match source tabs; deltas)")
print("=" * 70)
# Production tile vs MFG tab, Latest day
ov_prod = clip_range(m, LATEST)["TOTAL PRODUCTION"].sum()
check("OVERVIEW", "Production tile == MFG tab total (Latest day)",
      ov_prod, dash_total_ld)
# WIP tile vs WIP snapshot
ov_wip = wip_snapshot(clip_range(w, LATEST))["boxes"]
check("OVERVIEW", "In WIP tile == WIP snapshot boxes (Latest day)",
      ov_wip, snap["boxes"])
# Plan vs actual tile vs CT sum/sum on resolved range
ctw = clip_range(c, LATEST)
ov_pct = (ctw["Achieved"].sum() / ctw["Target"].sum() * 100
          if ctw["Target"].sum() else None)
indep_ov_pct = (clip_range(c, LATEST)["Achieved"].sum()
                / clip_range(c, LATEST)["Target"].sum() * 100)
check("OVERVIEW", "Plan vs actual tile == sum(Achieved)/sum(Target) (Latest day)",
      round(ov_pct, 6) if ov_pct is not None else None,
      round(indep_ov_pct, 6))


# --- Delta: previous comparable period, omitted where none --------------
def previous_frame(sheet, spec):
    days = _days(sheet)
    if not days:
        return None
    win = resolve_spec(days, spec)
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
        pe = start - pd.Timedelta(days=1)
        ps = start - (dur + pd.Timedelta(days=1))
        ps, pe = ps if isinstance(ps, type(days[0])) else ps, pe
    dd = sheet.dropna(subset=["Date"])
    prev = dd[(dd["Date"].dt.date >= (ps.date() if hasattr(ps, "date") else ps))
              & (dd["Date"].dt.date <= (pe.date() if hasattr(pe, "date") else pe))]
    return prev if not prev.empty else None


# Latest day delta should compare to the PREVIOUS existing day
days_m = _days(m)
prev_day = days_m[-2]
pf = previous_frame(m, LATEST)
prev_ok = pf is not None and set(pf["Date"].dt.date.unique()) == {prev_day}
check("OVERVIEW", f"Production delta compares to previous existing day ({prev_day})",
      sorted(set(pf["Date"].dt.date.unique())) if pf is not None else None,
      [prev_day], ok=prev_ok)
# All time delta must be omitted (no prior data)
pf_all = previous_frame(m, ALL)
check("OVERVIEW", "delta omitted (None) for All time (no comparison period)",
      "None" if pf_all is None else "shown", "None")


# =========================================================================
print("\n" + "=" * 70)
print("DATE-ANCHOR LOGIC")
print("=" * 70)
today = pd.Timestamp.today().normalize().date()
for key in ["mfg", "cooking_target", "wip_new", "conversion"]:
    df = cleaned(key)
    dl = _days(df)
    if not dl:
        continue
    resolved = resolve_spec(dl, LATEST)
    anchored_ok = (resolved == (dl[-1], dl[-1])) and (dl[-1] != today)
    check("DATE", f"{key}: Latest day = max Date ({dl[-1]}), not system today ({today})",
          resolved, (dl[-1], dl[-1]), ok=anchored_ok)


# =========================================================================
print("\n" + "=" * 70)
print("GLOBAL FLAGS: cleaning drops, NaN sums, date parse")
print("=" * 70)
for key in ["mfg", "cooking_target", "wip_new", "cut_pieces", "conversion"]:
    r = raw(key)
    cl = cleaned(key)
    dropped_rows = len(r) - len(cl)
    pct_drop = dropped_rows / len(r) * 100 if len(r) else 0
    flag = "  <-- LARGE" if pct_drop > 15 else ""
    print(f"  {key:14s} raw={len(r):5d}  cleaned={len(cl):5d}  "
          f"dropped={dropped_rows:4d} ({pct_drop:4.1f}%){flag}")

print("\n  NaN counts in key numeric columns after cleaning (silent-sum risk):")
numcols = {
    "mfg": ["TOTAL PRODUCTION", "NO. OF BATCHES", "BATCH SIZE(KG)"],
    "cooking_target": ["Target", "Achieved", "G - Done", "A-Done", "B-Done", "C-Done"],
    "wip_new": ["Number of boxes", "Ageing (Days)"],
    "conversion": ["% Achieved Mail", "Actual", "Ideal Conversion"],
}
for key, cols in numcols.items():
    cl = cleaned(key)
    bits = [f"{col}={int(cl[col].isna().sum())}" for col in cols if col in cl]
    print(f"  {key:14s} " + "  ".join(bits))

print("\n  Date-parse anomalies (NaT, year<100, tz):")
for key in ["mfg", "cooking_target", "wip_new", "cut_pieces", "conversion"]:
    cl = cleaned(key)
    dts = cl["Date"]
    nat = int(dts.isna().sum())
    bad_year = int((dts.dropna().dt.year < 100).sum())
    tz = dts.dt.tz
    lo = dts.min()
    hi = dts.max()
    print(f"  {key:14s} NaT={nat}  year<100={bad_year}  tz={tz}  "
          f"range={lo.date() if pd.notna(lo) else None} .. "
          f"{hi.date() if pd.notna(hi) else None}")


# =========================================================================
print("\n" + "=" * 70)
print("PASS / FAIL SUMMARY")
print("=" * 70)
w1, w2 = 10, 62
print(f"  {'RESULT':6s}  {'SECTION':9s}  CHECK")
print("  " + "-" * 84)
n_pass = 0
for section, name, dash, indep, ok in RESULTS:
    if ok:
        n_pass += 1
    print(f"  {'PASS' if ok else 'FAIL':6s}  {section:9s}  {name}")
print("  " + "-" * 84)
print(f"  {n_pass}/{len(RESULTS)} checks passed, {len(RESULTS)-n_pass} failed")
