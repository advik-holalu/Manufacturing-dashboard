"""Tab 2 - Cooking Target. The core decision tab: plan vs actual.
Default Month keeps the plan-vs-actual line readable across the full span.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import streamlit as st

from utils.ui import (section, context_box, auto_grain, time_axis, style_fig,
                      clip_range, resolve_spec, _days)
from utils.timegrain import grouper

# Target reads as the neutral grey reference line; Achieved as the accent.
TARGET_C = "#9aa0a6"
ACCENT = "#f6892b"   # brand orange - the achieved fill on the donut
TRACK = "#3f3f46"    # muted dark gray - the remainder track
SHIFT_COLS = {"G": "G - Done", "A": "A-Done", "B": "B-Done", "C": "C-Done"}


def _target_donut(target: float, achieved: float) -> None:
    """Single-day view: a progress ring of Achieved / Target.

    Fill is capped at 100% so it never overflows, but the centre label shows
    the true percentage (including overshoot like 103%). Target 0 is guarded.
    """
    if pd.isna(target) or target <= 0:
        st.info("No target set.")
        return
    pct = achieved / target * 100
    fill = min(max(pct, 0), 100)
    fig = go.Figure(go.Pie(
        values=[fill, 100 - fill], hole=0.72, sort=False,
        direction="clockwise", rotation=0,
        marker=dict(colors=[ACCENT, TRACK], line=dict(width=0)),
        textinfo="none", hoverinfo="skip",
    ))
    fig.add_annotation(text=f"{pct:,.0f}%", x=0.5, y=0.55, xref="paper",
                       yref="paper", showarrow=False,
                       font=dict(size=38, color="#ffffff"))
    fig.add_annotation(text=f"{achieved:,.0f} / {target:,.0f} kg", x=0.5,
                       y=0.40, xref="paper", yref="paper", showarrow=False,
                       font=dict(size=13, color=TARGET_C))
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=300, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render(df: pd.DataFrame, date_range=None) -> None:
    context_box(df, date_range)

    grain = auto_grain(df, date_range)
    f1, f2 = st.columns([2, 1.5])
    skus = sorted(df["SKU Name"].dropna().unique().tolist())
    pick = f1.multiselect("SKU", skus, key="ct_sku", placeholder="All products")
    shifts = f2.multiselect("Shift", ["G", "A", "B", "C"], key="ct_shift",
                            placeholder="All shifts")

    d = clip_range(df, date_range).copy()
    if pick:
        d = d[d["SKU Name"].isin(pick)]

    if d.empty:
        st.caption("No records in the selected range.")
        return

    # If shifts are filtered, recompute Achieved from just those shift columns.
    if shifts:
        cols = [SHIFT_COLS[s] for s in shifts]
        d = d.copy()
        d["Achieved"] = d[cols].sum(axis=1)

    target = d["Target"].sum()
    achieved = d["Achieved"].sum()
    pct = (achieved / target * 100) if target else 0
    pending = achieved - target

    st.divider()
    section("Plan vs actual this period")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Achieved", f"{achieved:,.0f}")
    c2.metric("Target", f"{target:,.0f}")
    c3.metric("Achieved %", f"{pct:,.1f}%")
    c4.metric("Pending", f"{pending:,.0f}")

    st.divider()
    section("Target vs Achieved")
    # Single-day range -> a line of one or two dots is pointless, so show a
    # progress ring instead. Detected from the resolved range span.
    win = resolve_spec(_days(df), date_range) if date_range else None
    if win and win[0] == win[1]:
        _target_donut(target, achieved)
    else:
        g = d.dropna(subset=["Date"]).copy()
        g["bucket"] = grouper(g["Date"], grain)
        ts = g.groupby("bucket", as_index=False)[["Target", "Achieved"]].sum()
        show_text = ts["bucket"].nunique() <= 40
        mode = "lines+markers+text" if show_text else "lines+markers"
        fig = go.Figure()
        fig.add_scatter(
            x=ts["bucket"], y=ts["Target"], name="Target", mode=mode,
            line=dict(width=3.5, dash="dash", color=TARGET_C),
            marker=dict(size=8, color=TARGET_C),
            texttemplate="%{y:.2s}", textposition="top center",
            textfont=dict(size=8, color=TARGET_C),
            hovertemplate="Target<br>%{x|%b %Y}<br>%{y:,.0f} kg<extra></extra>",
        )
        fig.add_scatter(
            x=ts["bucket"], y=ts["Achieved"], name="Achieved", mode=mode,
            line=dict(width=3.5), marker=dict(size=8),
            texttemplate="%{y:.2s}", textposition="top center",
            textfont=dict(size=8),
            hovertemplate="Achieved<br>%{x|%b %Y}<br>%{y:,.0f} kg<extra></extra>",
        )
        fig.update_xaxes(**time_axis(grain))
        fig.update_yaxes(title="kg")
        style_fig(fig, height=300, legend=True)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    section("By SKU")
    by = (d.groupby("SKU Name", as_index=False)
          .agg(Target=("Target", "sum"), Achieved=("Achieved", "sum")))
    by["Achieved %"] = (by["Achieved"] / by["Target"] * 100).round(1)
    by["Pending"] = (by["Achieved"] - by["Target"]).round(0)
    by = by.sort_values("Achieved %")
    st.dataframe(
        by, use_container_width=True, hide_index=True,
        column_config={
            "Target": st.column_config.NumberColumn(format="%.0f"),
            "Achieved": st.column_config.NumberColumn(format="%.0f"),
            "Achieved %": st.column_config.NumberColumn(format="%.1f%%"),
            "Pending": st.column_config.NumberColumn(format="%.0f"),
        },
    )

    st.divider()
    section("Achievement rate by shift")
    rows = []
    src = d if not pick else d[d["SKU Name"].isin(pick)]
    for sku, grp in src.groupby("SKU Name"):
        tgt = grp["Target"].sum()
        if not tgt:
            continue
        for s, col in SHIFT_COLS.items():
            done = grp[col].sum()
            if done > 0:
                rows.append({"SKU": sku, "Shift": s,
                             "Rate": round(done / tgt * 100, 1)})
    if rows:
        rdf = pd.DataFrame(rows)
        top_skus = (rdf.groupby("SKU")["Rate"].sum()
                    .sort_values(ascending=False).head(6).index.tolist())
        rdf = rdf[rdf["SKU"].isin(top_skus)]
        st.caption("Top 6 products by combined rate, so the bars stay readable.")
        fig = px.bar(
            rdf, x="Rate", y="SKU", color="Shift", orientation="h",
            barmode="group",
            category_orders={"Shift": ["G", "A", "B", "C"]},
        )
        fig.update_traces(
            texttemplate="%{x:.0f}", textposition="outside",
            textfont=dict(size=8), cliponaxis=False,
            hovertemplate="%{y}<br>%{fullData.name}<br>%{x:.1f}<extra></extra>",
        )
        fig.update_xaxes(title="rate of target (%)")
        fig.update_yaxes(title=None, categoryorder="total ascending")
        style_fig(fig, height=max(240, 46 * len(top_skus)), legend=True)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("No shift-level data for the current selection.")
