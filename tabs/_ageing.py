"""Shared renderer for the ageing/freshness tab (Cut pieces).
Kept as a helper so the quantity column and labels stay configurable.
"""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from utils.ui import section, context_box, style_fig, clip_range


# SOP allowed cut-piece time per product, in DAYS. 0 = No Rework (always green).
# The Cut pieces sheet uses packaged SKU names (e.g. "Kaju Katli Premium Box 180
# grams"), so a row is matched to its SOP product by case-insensitive substring;
# the LONGEST matching SOP name wins. No match -> no threshold -> green.
SOP_DAYS = {
    "Coconut Laddu": 1,
    "Badam Burfi": 2,
    "Pista Burfi": 2,
    "Kaju Kishmish Burfi": 2,
    "Dry Fruit Barfi": 7,
    "Kaju Katli Classic": 2,
    "Kaju Katli Premium": 2,
    "Jaggery Kaju Katli": 2,
    "Mysore Pak": 7,
    "Milk Cake": 7,
    "Gond Laddu": 0,
    "Besan Laddu": 0,
    "Motichoor Laddu": 0,
    "Dates Dry Fruit Laddu": 0,
    "Dry Fruit Ragi Laddu": 0,
    "Milk Peda": 0,
    "Kesar Peda": 0,
    "Dark Chocolate Kaju Katli": 0,
    "Ghewar": 0,
}
# longest names first so a longer match beats a shorter one
_SOP_SORTED = sorted(SOP_DAYS.items(), key=lambda kv: -len(kv[0]))

GREEN, AMBER, RED = "#66bb6a", "#ffca28", "#ef5350"


def sop_limit(sku):
    """Return the SOP limit in days for a SKU, or None if no SOP product matches."""
    if not isinstance(sku, str):
        return None
    s = sku.lower()
    for name, days in _SOP_SORTED:
        if name.lower() in s:
            return days
    return None


def _cell_css(age, limit) -> str:
    """Colour one Ageing cell against its product's SOP limit. Dark readable text."""
    if pd.isna(age):
        return ""
    if limit is None or pd.isna(limit):
        bg = GREEN                       # no SOP match -> no threshold
    elif int(limit) == 0:
        bg = GREEN                       # No Rework products -> always green
    elif age < limit:
        bg = GREEN
    elif age == limit:
        bg = AMBER
    else:
        bg = RED
    return f"background-color: {bg}; color: #111111;"


def _sop_row_style(row):
    """Per-row Styler function: colour only the Ageing (Days) cell using the
    row's own SOP limit (read from the SOP (days) column)."""
    styles = [""] * len(row)
    if "Ageing (Days)" in row.index:
        limit = row["SOP (days)"] if "SOP (days)" in row.index else None
        styles[row.index.get_loc("Ageing (Days)")] = _cell_css(
            row["Ageing (Days)"], limit)
    return styles


def render_ageing(df: pd.DataFrame, date_range=None, *, key: str, qty_col: str,
                  qty_label: str, use_shift: bool, sku_col: str = "SKU",
                  stage_word: str = "sits") -> None:
    context_box(df, date_range)

    f1, f2 = st.columns([2, 1.5])
    skus = sorted(df[sku_col].dropna().unique().tolist())
    pick = f1.multiselect("SKU", skus, key=f"{key}_sku",
                          placeholder="All products")
    sh = []
    if use_shift:
        sh = f2.multiselect("Shift", ["G", "A", "B", "C"], key=f"{key}_shift",
                            placeholder="All shifts")

    d = clip_range(df, date_range).copy()
    if pick:
        d = d[d[sku_col].isin(pick)]
    if use_shift and sh:
        d = d[d["Shift"].isin(sh)]
    # Negative ageing is a data-entry error (mfg date after entry); drop it here.
    if "Ageing (Days)" in d.columns:
        d = d[d["Ageing (Days)"].fillna(0) >= 0]

    if d.empty:
        st.caption("No records in the selected range.")
        return

    age = d["Ageing (Days)"].dropna()
    avg = age.mean() if len(age) else 0
    within3 = (age <= 3).mean() * 100 if len(age) else 0
    over7 = int((age > 7).sum())

    st.divider()
    section("Freshness this period")
    c1, c2, c3 = st.columns(3)
    c1.metric("Avg ageing", f"{avg:,.1f} days")
    c2.metric("Within 3 days", f"{within3:,.0f}%")
    c3.metric("Aged over 7 days", f"{over7:,.0f} lots")

    st.divider()
    section("Ageing distribution")
    b = d.dropna(subset=["Ageing (Days)"]).copy()
    b["bucket"] = b["Ageing (Days)"].clip(upper=6).astype(int)
    b["label"] = b["bucket"].map(lambda x: f"{x}d" if x < 6 else "6d+")
    order = [f"{i}d" for i in range(6)] + ["6d+"]
    hist = b.groupby("label", as_index=False).size()
    fig = go.Figure(go.Bar(
        x=hist["label"], y=hist["size"],
        texttemplate="%{y:,.0f}", textposition="outside",
        textfont=dict(size=10), cliponaxis=False,
        hovertemplate="%{x}<br>%{y:,.0f} lots<extra></extra>",
    ))
    fig.update_xaxes(title="days aged", categoryorder="array",
                     categoryarray=order)
    fig.update_yaxes(title="lots")
    style_fig(fig, height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    section("Oldest sitting stock")
    cols = [sku_col, qty_col, "Manufacturing Date", "Ageing (Days)"]
    cols = [c for c in cols if c in d.columns]
    old = (d.sort_values("Ageing (Days)", ascending=False)[cols]
           .head(25).reset_index(drop=True))
    # Per-product SOP limit next to each row so the colouring is self-explanatory
    # (blank when the SKU matches no SOP product).
    old["SOP (days)"] = old[sku_col].map(sop_limit).astype("Int64")
    # Colour only the Ageing column, per row, against that product's SOP limit.
    styled = old.style.apply(_sop_row_style, axis=1)
    st.dataframe(
        styled, use_container_width=True, hide_index=True,
        column_config={
            qty_col: st.column_config.NumberColumn(qty_label, format="%.0f"),
            "Manufacturing Date": st.column_config.DateColumn(format="DD MMM"),
            "Ageing (Days)": st.column_config.NumberColumn(
                "Ageing (days)", format="%.0f"),
            "SOP (days)": st.column_config.NumberColumn(
                "SOP (days)", format="%d"),
        },
    )
