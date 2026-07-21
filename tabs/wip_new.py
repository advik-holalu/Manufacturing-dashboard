"""Tab 3 - WIP New. A tight LIVE BOARD - what is resting right now.

WIP New is a DAILY CARRY-OVER SNAPSHOT: every day re-lists everything still
resting in the holding area, so the same batch reappears across days (ageing +1)
until it is packed and drops off. WIP is a LIVE POSITION, never an accumulation -
so every number here uses the LATEST snapshot day ONLY and NEVER sums across days.

Rows are a MIX of units: SKUs named "individual"/"pieces"/"pcs" are counted in
PIECES, everything else in BOXES. The two are never merged into one number.

This tab is range-INDEPENDENT: the global time-range control does not affect it.
There is deliberately no time-series/trend chart. WIP New and Cut pieces are
independent sheets.
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from utils.ui import section

_PIECE_RE = re.compile(r"individual|piece|pcs", re.IGNORECASE)


def wip_unit(sku) -> str:
    """Classify a WIP row's unit from its SKU name.

    'individual', 'individuals', 'piece', 'pieces', 'pcs' (any case) -> pieces;
    everything else -> boxes.
    """
    return "pieces" if isinstance(sku, str) and _PIECE_RE.search(sku) else "boxes"


def wip_snapshot(d: pd.DataFrame) -> dict:
    """Latest-snapshot-day state from a set of WIP rows (used by the Overview
    tile). Only the most recent day is a true count of what is sitting there now.
    Quantity is split by unit - box_qty and piece_qty are never merged.
    """
    out = {"latest": None, "cur": d.iloc[0:0], "box_qty": 0, "piece_qty": 0,
           "lots": 0, "beyond": 0, "pct": 0.0}
    dd = d.dropna(subset=["Date"])
    if dd.empty:
        return out
    latest = dd["Date"].max()
    cur = dd[dd["Date"] == latest]
    lots = len(cur)
    beyond = int((cur["Ageing (Days)"] > 2).sum())
    units = cur["SKU"].map(wip_unit)
    q = cur["Number of boxes"]
    out.update(latest=latest, cur=cur, lots=lots, beyond=beyond,
               box_qty=q[units == "boxes"].sum(),
               piece_qty=q[units == "pieces"].sum(),
               pct=(beyond / lots * 100) if lots else 0.0)
    return out


def _bp(boxes, pieces) -> str:
    """Format a box/piece pair without ever merging the two units."""
    b = f"{boxes:,.0f}" if pd.notna(boxes) else "-"
    p = f"{pieces:,.0f}" if pd.notna(pieces) else "-"
    return f"{b} boxes · {p} pieces"


def render(df: pd.DataFrame, date_range=None) -> None:
    st.caption("This tab always shows the latest snapshot day - it's a live "
               "view, not a range. The global time range does not apply here.")

    skus = sorted(df["SKU"].dropna().unique().tolist())
    pick = st.multiselect("SKU", skus, key="WIP_sku", placeholder="All products")

    # Range-INDEPENDENT: ignore date_range entirely, use the whole sheet.
    d = df.copy()
    if pick:
        d = d[d["SKU"].isin(pick)]
    d = d.dropna(subset=["Date"])

    if d.empty:
        st.info("No data for this selection.")
        return

    # Latest snapshot day only - never sum across days.
    latest = d["Date"].max()
    cur = d[d["Date"] == latest]

    # Data quality: negative ageing = manufacturing date after the snapshot.
    neg = int((cur["Ageing (Days)"] < 0).sum())
    # Metrics use only valid ageing rows (>= 0; NaN excluded as NaN >= 0 is False).
    valid = cur[cur["Ageing (Days)"] >= 0].copy()

    # Split every quantity by unit - boxes and pieces stay separate.
    q = "Number of boxes"
    valid["Unit"] = valid["SKU"].map(wip_unit)
    is_box = valid["Unit"] == "boxes"
    is_pc = valid["Unit"] == "pieces"
    box_total = valid.loc[is_box, q].sum()
    piece_total = valid.loc[is_pc, q].sum()

    if "Manufacturing Date" in valid.columns:
        made_today = valid["Manufacturing Date"].dt.date == latest.date()
    else:
        made_today = pd.Series(False, index=valid.index)
    fresh_boxes = valid.loc[made_today & is_box, q].sum()
    fresh_pieces = valid.loc[made_today & is_pc, q].sum()

    age1 = valid["Ageing (Days)"] >= 1
    carry_boxes = valid.loc[age1 & is_box, q].sum()
    carry_pieces = valid.loc[age1 & is_pc, q].sum()

    lots = len(valid)
    beyond = int((valid["Ageing (Days)"] > 2).sum())
    beyond_pct = (beyond / lots * 100) if lots else None

    # ---- Section 1: In WIP right now (latest snapshot day only) ----------
    section("In WIP right now")
    st.caption(f"Latest snapshot: {latest:%d %b %Y}")
    if neg:
        st.caption(f"{neg:,.0f} rows have invalid dates - check the sheet.")

    if valid.empty:
        st.info("No valid rows on the latest snapshot day.")
    else:
        r1 = st.columns(3)
        r1[0].metric("In WIP now (boxes)", f"{box_total:,.0f}")
        r1[1].metric("In WIP now (pieces)", f"{piece_total:,.0f}")
        r1[2].metric("Aged beyond 2 days", f"{beyond:,.0f} lots")

        r2 = st.columns(2)
        r2[0].metric("Fresh (age 0)", _bp(fresh_boxes, fresh_pieces))
        r2[1].metric("Carry-over (age 1+)", _bp(carry_boxes, carry_pieces))

        parts = []
        if box_total:
            parts.append(f"{carry_boxes / box_total * 100:,.0f}% of resting "
                         "boxes")
        if piece_total:
            parts.append(f"{carry_pieces / piece_total * 100:,.0f}% of resting "
                         "pieces")
        if parts:
            st.caption("Carry-over is " + " and ".join(parts) + " - near zero "
                       "is healthy; a large or growing carry-over means product "
                       "is backing up.")
        beyond_txt = f"{beyond_pct:,.0f}%" if beyond_pct is not None else "-"
        st.caption(f"Aged beyond 2 days is {beyond_txt} of {lots:,.0f} resting "
                   "lots.")

    # ---- Section 2: Resting right now (latest snapshot day only) ---------
    st.divider()
    section("Resting right now")
    show = cur.copy()
    show["Unit"] = show["SKU"].map(wip_unit)
    cols = [c for c in ["SKU", "Number of boxes", "Unit", "Manufacturing Date",
                        "Ageing (Days)"] if c in show.columns]
    tbl = (show.sort_values("Ageing (Days)", ascending=False)[cols]
           .reset_index(drop=True))
    st.dataframe(
        tbl, use_container_width=True, hide_index=True,
        column_config={
            "Number of boxes": st.column_config.NumberColumn(
                "Quantity", format="%.0f"),
            "Unit": st.column_config.TextColumn("Unit"),
            "Manufacturing Date": st.column_config.DateColumn(
                format="DD MMM YYYY"),
            "Ageing (Days)": st.column_config.NumberColumn(
                "Ageing (days)", format="%.0f"),
        },
    )
