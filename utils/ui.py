"""
Shared UI helpers - native Streamlit, almost no custom CSS.

The ONLY custom HTML in the whole app is the orange header banner below. Every
other surface is native: st.subheader / st.markdown headings, st.divider between
sections, st.metric for KPIs, st.dataframe for tables, st.caption for coverage.

No tooltips anywhere - the User Guide tab explains what each view shows.
Hyphens only, never em-dashes, in any user-facing copy.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st


_SHEET_URL = ("https://docs.google.com/spreadsheets/d/"
              "1_fcucrSa4DY3qTxpZCWp08fmU1LM2R2b_e2jWM1I6s0/edit")


def header(date_line: str = "") -> None:
    """The one branded banner - the only custom HTML allowed in the app.

    A full-width orange bar holding the title, the linked subtitle, and the
    resolved-date line (all inside the banner). Hyphens only.
    """
    line_html = (
        f"<div style='color:#ffffff;opacity:0.85;font-size:12px;"
        f"margin-top:6px;'>{date_line}</div>" if date_line else "")
    st.markdown(
        "<style>.gd-sub{color:#ffffff;opacity:0.92;text-decoration:none;}"
        ".gd-sub:hover{text-decoration:underline;}</style>"
        "<div style='background:#f6892b;border-radius:10px;width:100%;"
        "box-sizing:border-box;padding:16px 20px;margin-bottom:12px;'>"
        "<div style='color:#ffffff;font-size:22px;font-weight:700;"
        "line-height:1.2;'>GO DESi Production</div>"
        "<div style='font-size:13px;margin-top:2px;'>"
        f"<a class='gd-sub' href='{_SHEET_URL}' target='_blank' "
        "rel='noopener noreferrer'>Shift report</a></div>"
        f"{line_html}"
        "</div>",
        unsafe_allow_html=True,
    )


def section(title: str) -> None:
    """A native section heading."""
    st.markdown(f"#### {title}")


# (coverage + grain radio removed. Date context is now one st.info box via
#  context_box(); chart grain is auto-derived from the range via auto_grain().)


# --------------------------------------------------------------------------
# Global time-range control.
#
# The control produces a "range spec" - the chosen preset, plus custom dates -
# NOT a resolved (start, end). The spec is resolved PER SHEET against that
# sheet's own latest date, so a "recent" preset (Latest day, This week, ...)
# always anchors to real data and never lands on an empty range - even when
# sheets end on different dates and none of them reach the calendar today.
# --------------------------------------------------------------------------
RANGE_PRESETS = ["Latest day", "Previous day", "This week", "This month",
                 "Last 3 months", "All time", "Custom"]


def _days(df: pd.DataFrame, date_col: str = "Date"):
    """Sorted list of distinct dates present in a frame."""
    if date_col not in df.columns:
        return []
    return sorted(set(df[date_col].dropna().dt.date))


def resolve_spec(day_list, spec):
    """Resolve a range spec to (start, end) dates against a sheet's own days.

    day_list is that sheet's sorted distinct dates, so the anchor is the
    sheet's real max date, never datetime.today().
    """
    if not day_list or not spec:
        return None
    preset, cstart, cend = spec
    dmin, dmax = day_list[0], day_list[-1]

    if preset == "Custom":
        return (cstart or dmin, cend or dmax)
    if preset == "All time":
        return (dmin, dmax)
    if preset in ("Previous day", "Yesterday"):
        # the day before the max that ACTUALLY exists in the data
        prev = day_list[-2] if len(day_list) >= 2 else dmax
        return (prev, prev)

    a = pd.Timestamp(dmax)
    if preset == "This week":
        s = (a - pd.Timedelta(days=int(a.weekday()))).date()
    elif preset == "This month":
        s = a.replace(day=1).date()
    elif preset == "Last 3 months":
        s = (a - pd.DateOffset(months=3)).date()
    else:  # "Latest day" (default) / "Today" / any fallback -> single latest day
        return (dmax, dmax)
    return (max(s, dmin), dmax)


def range_control(dates: pd.Series):
    """Render the dashboard-wide range row and return a range spec.

    The spec is stored in st.session_state['range_spec'] and each tab resolves
    it against its own sheet. The caption uses the live-data anchor passed in.
    """
    day_list = sorted(set(pd.Series(dates).dropna().dt.date))
    if not day_list:
        return None
    dmin, dmax = day_list[0], day_list[-1]

    c1, c2 = st.columns([1.4, 4])
    preset = c1.selectbox(
        "Time range", RANGE_PRESETS, index=RANGE_PRESETS.index("Latest day"),
        key="range_preset")

    if preset == "Custom":
        seed = st.session_state.get("range_custom_val", (dmin, dmax))
        rng = c2.date_input(
            "Custom range", value=seed, min_value=dmin, max_value=dmax,
            key="range_custom")
        if isinstance(rng, (list, tuple)):
            cstart, cend = (rng[0], rng[-1]) if rng else (dmin, dmax)
        else:
            cstart = cend = rng
        st.session_state["range_custom_val"] = (cstart, cend)
        spec = ("Custom", cstart, cend)
    else:
        # The resolved-date line now lives inside the header banner
        # (see resolved_line + header), not beside this control.
        spec = (preset, None, None)

    st.session_state["range_spec"] = spec
    return spec


def resolved_line(dates: pd.Series, range_spec) -> str:
    """The 'Showing ...' latest-day line shown inside the header banner.

    Uses the same resolved-latest-day logic as the tabs. Hyphens only.
    """
    day_list = sorted(set(pd.Series(dates).dropna().dt.date))
    if not day_list or not range_spec:
        return ""
    win = resolve_spec(day_list, range_spec)
    if not win:
        return ""
    start, end = win
    if start == end:
        if range_spec[0] == "Latest day":
            return f"Showing {start:%d %b %Y} - the latest day with data."
        return f"Showing {start:%d %b %Y}."
    return f"Showing {start:%d %b %Y} to {end:%d %b %Y}."


def clip_range(df: pd.DataFrame, range_spec, date_col: str = "Date"):
    """Filter a frame to the range spec, resolved against ITS OWN latest date."""
    if not range_spec or date_col not in df.columns:
        return df
    win = resolve_spec(_days(df, date_col), range_spec)
    if not win:
        return df
    start, end = win
    d = df[date_col].dt.date
    return df[(d >= start) & (d <= end)]


def context_text(day_list, range_spec) -> str:
    """One-line date-context strip combining the resolved selection and the
    full available span. Middle-dot separated, hyphens only.

    Single-day windows read like:
      'Latest day: 16 Jul 2026  ·  Previous day: 15 Jul 2026  ·  Data
       available: Sep 2024 to 16 Jul 2026'
    Multi-day windows read like:
      'Showing 01 Jun 2026 to 16 Jul 2026  ·  Data available: Sep 2024 to
       16 Jul 2026'
    """
    if not day_list:
        return "No dated records."
    dmin, dmax = day_list[0], day_list[-1]
    avail = f"Data available: {dmin:%b %Y} to {dmax:%d %b %Y}"
    win = resolve_spec(day_list, range_spec) if range_spec else (dmax, dmax)
    if not win:
        return avail
    start, end = win
    if start == end:
        if end == dmax and len(day_list) >= 2:
            head = (f"Latest day: {end:%d %b %Y}  ·  "
                    f"Previous day: {day_list[-2]:%d %b %Y}")
        else:
            head = f"Showing {end:%d %b %Y}"
    else:
        head = f"Showing {start:%d %b %Y} to {end:%d %b %Y}"
    return f"{head}  ·  {avail}"


def context_box(df: pd.DataFrame, range_spec, date_col: str = "Date") -> None:
    """One native st.info() date-context strip for a single sheet's tab."""
    st.info(context_text(_days(df, date_col), range_spec))


# --------------------------------------------------------------------------
# Auto-derive the chart bucket grain from the resolved date span. Replaces the
# per-tab grain radio: the range already tells us the right resolution.
#   span <= 14 days  -> Day      span <= 120 days -> Week
#   span <= 3 years  -> Month    else             -> Year
# --------------------------------------------------------------------------
def auto_grain(df: pd.DataFrame, range_spec, date_col: str = "Date") -> str:
    days = _days(df, date_col)
    if not days:
        return "Month"
    win = resolve_spec(days, range_spec) if range_spec else (days[0], days[-1])
    start, end = win if win else (days[0], days[-1])
    span = (end - start).days + 1
    if span <= 14:
        return "Day"
    if span <= 120:
        return "Week"
    if span <= 3 * 365:
        return "Month"
    return "Year"


# --------------------------------------------------------------------------
# Plotly chart helpers - axis format pinned to the grain, dark template.
#   Day -> "07 Sep"  Week -> "07 Sep"  Month -> "Sep 25"  Year -> "2025"
# --------------------------------------------------------------------------
_TICKFMT = {"Day": "%d %b", "Week": "%d %b", "Month": "%b %y", "Year": "%Y"}
_DTICK = {"Month": "M1", "Year": "M12"}  # every month / every year; Day/Week auto


def time_axis(grain: str) -> dict:
    ax = dict(tickformat=_TICKFMT.get(grain, "%d %b"),
              tickangle=(0 if grain == "Year" else -45), title=None)
    if grain in _DTICK:
        ax["dtick"] = _DTICK[grain]
    return ax


def style_fig(fig, height: int = 300, legend: bool = False):
    """Dark-theme styling shared by every Plotly figure in the app."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=10, r=10, t=(42 if legend else 26), b=10),
        font=dict(size=12),
        showlegend=legend,
        hoverlabel=dict(font_size=12),
    )
    if legend:
        fig.update_layout(legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="left", x=0, title_text=""))
    fig.update_xaxes(gridcolor="rgba(250,250,250,0.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(250,250,250,0.08)", zeroline=False)
    return fig
