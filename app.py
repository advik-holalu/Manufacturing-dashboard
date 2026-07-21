"""
GO DESi - Production Shift Report Dashboard
Entry point. Overview tab, one tab per source sheet, and a User Guide.

Design rules (enforced throughout):
  - Native Streamlit only. The single orange header banner is the one
    piece of custom HTML; no other custom CSS, no cards, no tooltips.
  - The date RANGE is global: one control above the tabs feeds every tab.
  - Each tab owns its grain toggle and SKU filter.
  - Surface data, not conclusions. Hyphens only, never em-dashes.
  - Cache the fetch and the cleaning; vectorize all derived columns.
"""

import pandas as pd
import streamlit as st

from utils.data import load_sheet, SHEETS
from utils.ui import header, range_control, resolved_line
from tabs import (overview, mfg, cooking_target, wip_new, cut_pieces,
                  conversion, user_guide)

st.set_page_config(
    page_title="GO DESi Production",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Reserve the top slot for the banner. It is filled AFTER the range control
# runs, so the resolved-date line can be rendered inside the banner itself.
banner_area = st.container()

# Load every sheet once (cached) so the Overview and the global range control
# can see across all of them.
dfs = {key: load_sheet(name) for key, name in SHEETS.items()}

# The range anchor is the LIVE sheets only. Conversion is a static reference
# sheet exempt from the global range, so it must not drag the anchor around.
LIVE_KEYS = ["mfg", "cooking_target", "wip_new", "cut_pieces"]
_dates = [dfs[k]["Date"] for k in LIVE_KEYS
          if k in dfs and "Date" in dfs[k].columns]
live_dates = (pd.concat(_dates).dropna() if _dates
              else pd.Series(dtype="datetime64[ns]"))

if live_dates.empty:
    st.warning("No dated records found in the live sheets.")
    date_range = None
else:
    # date_range is a range SPEC now; each tab resolves it against its own max.
    date_range = range_control(live_dates)

# Fill the reserved top slot: banner with the resolved-date line inside it.
with banner_area:
    header(resolved_line(live_dates, date_range))

tabs = st.tabs(["Overview", "MFG", "Cooking Target", "WIP New", "Cut pieces",
                "Conversion", "User Guide"])

with tabs[0]:
    overview.render(dfs, date_range)
with tabs[1]:
    mfg.render(dfs["mfg"], date_range)
with tabs[2]:
    cooking_target.render(dfs["cooking_target"], date_range)
with tabs[3]:
    wip_new.render(dfs["wip_new"], date_range)
with tabs[4]:
    cut_pieces.render(dfs["cut_pieces"], date_range)
with tabs[5]:
    conversion.render(dfs["conversion"], date_range)
with tabs[6]:
    user_guide.render()
