"""Tab 5 - Conversion. Yield reference. Deliberately light - thin data."""

from __future__ import annotations

import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from utils.ui import section, context_box, style_fig


def render(df: pd.DataFrame, date_range=None) -> None:
    # Conversion is exempt from the global range - it always shows all rows, so
    # its context box reflects its full span, not the selected window.
    context_box(df, ("All time", None, None))

    skus = sorted(df["Item Name"].dropna().unique().tolist())
    pick = st.multiselect("SKU", skus, key="conv_sku",
                          placeholder="All products")
    st.caption("Only a small set of records (a few weeks in mid 2026). This is "
               "a reference view, not enough history to trend yet.")

    # Conversion is a static reference sheet - always show all its rows. The
    # global time-range control only applies to the live sheets, so date_range
    # is deliberately ignored here.
    d = df.copy()
    if pick:
        d = d[d["Item Name"].isin(pick)]

    if d.empty:
        st.caption("No records to show.")
        return

    by = (d.groupby("Item Name", as_index=False)
          .agg(Ideal=("Ideal Conversion", "mean"),
               Achieved=("% Achieved Mail", "mean")))
    by["Ideal"] = (by["Ideal"] * 100).round(1)
    by["Achieved"] = (by["Achieved"] * 100).round(1)
    by["Gap"] = (by["Achieved"] - by["Ideal"]).round(1)

    st.divider()
    section("Actual vs ideal yield")
    by = by.sort_values("Achieved")  # highest lands at the top (h-bars)
    fig = go.Figure()
    fig.add_bar(
        x=by["Achieved"], y=by["Item Name"], orientation="h", name="Actual",
        texttemplate="%{x:.0f}", textposition="outside",
        textfont=dict(size=9), cliponaxis=False,
        hovertemplate="%{y}<br>Actual %{x:.1f}<extra></extra>",
    )
    fig.add_scatter(
        x=by["Ideal"], y=by["Item Name"], mode="markers", name="Ideal",
        marker=dict(symbol="line-ns", size=18, line=dict(width=3)),
        hovertemplate="%{y}<br>Ideal %{x:.1f}<extra></extra>",
    )
    fig.update_xaxes(title="yield (%)")
    fig.update_yaxes(title=None)
    style_fig(fig, height=max(220, 42 * len(by)), legend=True)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    section("Reference table")
    st.dataframe(
        by[["Item Name", "Ideal", "Achieved", "Gap"]],
        use_container_width=True, hide_index=True,
        column_config={
            "Ideal": st.column_config.NumberColumn(format="%.1f%%"),
            "Achieved": st.column_config.NumberColumn(format="%.1f%%"),
            "Gap": st.column_config.NumberColumn(format="%.1f"),
        },
    )
