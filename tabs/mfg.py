"""Tab 1 - MFG. Raw production: volume and line utilization.
The chart bucket (Day/Week/Month/Year) is auto-derived from the selected range,
so short ranges never render hundreds of bars.
"""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from utils.ui import (section, context_box, auto_grain, time_axis, style_fig,
                      clip_range)
from utils.timegrain import grouper


def render(df: pd.DataFrame, date_range=None) -> None:
    context_box(df, date_range)

    grain = auto_grain(df, date_range)
    f1, f2 = st.columns([2, 1.3])
    skus = sorted(df["Product Name"].dropna().unique().tolist())
    pick = f1.multiselect("SKU", skus, key="mfg_sku", placeholder="All products")
    lines = sorted([int(x) for x in df["LINE"].dropna().unique().tolist()])
    line_pick = f2.multiselect("Line", lines, key="mfg_line",
                               placeholder="All lines")

    d = clip_range(df, date_range).copy()
    if pick:
        d = d[d["Product Name"].isin(pick)]
    if line_pick:
        d = d[d["LINE"].isin(line_pick)]

    if d.empty:
        st.caption("No records in the selected range.")
        return

    total = d["TOTAL PRODUCTION"].sum()
    batches = d["NO. OF BATCHES"].sum()
    n_sku = d["Product Name"].nunique()

    st.divider()
    section("This period at a glance")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total produced", f"{total:,.0f} kg")
    c2.metric("Batches", f"{batches:,.0f}")
    c3.metric("Active SKUs", f"{n_sku:,.0f}")

    st.divider()
    section("By product")
    by = (d.groupby("Product Name", as_index=False)
          .agg(**{"Total kg": ("TOTAL PRODUCTION", "sum"),
                  "Batches": ("NO. OF BATCHES", "sum")})
          .sort_values("Total kg", ascending=False))
    if by.empty:
        st.caption("No production in this range.")
    else:
        # whole numbers, kept numeric so header sort stays numeric
        by["Total kg"] = by["Total kg"].fillna(0).round(0).astype("int64")
        by["Batches"] = by["Batches"].fillna(0).round(0).astype("int64")
        st.dataframe(
            by, use_container_width=True, hide_index=True,
            column_config={
                "Product Name": st.column_config.TextColumn("SKU"),
                "Total kg": st.column_config.NumberColumn("Total kg",
                                                          format="localized"),
                "Batches": st.column_config.NumberColumn("Batches",
                                                         format="localized"),
            },
        )

    g = d.dropna(subset=["Date"]).copy()
    g["bucket"] = grouper(g["Date"], grain)

    st.divider()
    section("Production over time")
    ts = g.groupby("bucket", as_index=False)["TOTAL PRODUCTION"].sum()
    fig = go.Figure(go.Bar(
        x=ts["bucket"], y=ts["TOTAL PRODUCTION"],
        texttemplate="%{y:.2s}", textposition="outside",
        textfont=dict(size=9), cliponaxis=False,
        hovertemplate="%{x|%d %b %Y}<br>%{y:,.0f} kg<extra></extra>",
    ))
    fig.update_xaxes(**time_axis(grain))
    fig.update_yaxes(title="kg")
    style_fig(fig, height=300)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    section("Line utilization")
    ln = g.dropna(subset=["LINE"]).copy()
    ln["Line"] = "Line " + ln["LINE"].astype(int).astype(str)
    ln = ln[ln["Line"].isin(["Line 1", "Line 2"])]
    gl = ln.groupby(["bucket", "Line"], as_index=False)["TOTAL PRODUCTION"].sum()
    fig = go.Figure()
    for name in ["Line 1", "Line 2"]:
        sub = gl[gl["Line"] == name]
        fig.add_bar(
            x=sub["bucket"], y=sub["TOTAL PRODUCTION"], name=name,
            texttemplate="%{y:.2s}", textposition="outside",
            textfont=dict(size=8), cliponaxis=False,
            hovertemplate=(name + "<br>%{x|%b %Y}<br>"
                           "%{y:,.0f} kg<extra></extra>"),
        )
    fig.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05)
    fig.update_xaxes(**time_axis(grain))
    fig.update_yaxes(title="kg")
    style_fig(fig, height=300, legend=True)
    st.plotly_chart(fig, use_container_width=True)
