"""User Guide tab. Plain-language help, one expander per view.
This replaces the old hover tooltips. Hyphens only, no em-dashes.
"""

from __future__ import annotations

import streamlit as st


def render() -> None:
    st.markdown("#### User Guide")
    st.caption("What each view shows, how the key numbers are worked out, and "
               "how to read the charts.")

    with st.expander("Time range control (applies to every tab)"):
        st.markdown(
            "- One range control sits above the tabs and feeds every tab at "
            "once. Pick a preset or Custom.\n"
            "- Presets are worked out from the latest date present in the "
            "data, not the calendar. So Today means the most recent day that "
            "has data - a morning meeting is never looking at an empty today.\n"
            "- Each tab keeps its own SKU filter. The chart bucket "
            "(Day, Week, Month or Year) is derived automatically from the "
            "selected range, so you never set a grain by hand."
        )

    with st.expander("Overview"):
        st.markdown(
            "A glance view - the state of the factory in four tiles. Each tile "
            "is read from its own sheet's latest available day inside the "
            "chosen window, so a sheet that has not posted for the exact latest "
            "day still shows real numbers.\n\n"
            "- Production: total kilos made in the window, with the most recent "
            "production day's kilos in the caption.\n"
            "- Plan vs actual: Achieved divided by Target across the window, as "
            "a percent.\n"
            "- In WIP now: boxes resting on the latest WIP snapshot day, plus "
            "how many lots are aged beyond 2 days.\n"
            "- Latest yield: the most recent achieved conversion yield.\n\n"
            "The caption under each tile shows which sheet it came from and its "
            "as-of date."
        )

    with st.expander("MFG"):
        st.markdown(
            "Raw production - what was actually made.\n\n"
            "- Total produced: every kilo made in the window, added across all "
            "batches, lines and shifts.\n"
            "- Batches: how many production batches ran. Total kg equals batch "
            "size times number of batches.\n"
            "- Active SKUs: how many different products were made at least "
            "once.\n\n"
            "Production over time: each bar is total kilos made in one bucket. "
            "The bucket size (Day, Week, Month or Year) is chosen automatically "
            "from the selected range, so a short range shows days and a long "
            "range shows months or years. Line utilization: Line 1 and Line 2 "
            "side by side per bucket, to show how balanced the load is."
        )

    with st.expander("Cooking Target"):
        st.markdown(
            "The core decision view - plan versus actual.\n\n"
            "- Achieved: kilos actually cooked in the window.\n"
            "- Target: kilos that were planned.\n"
            "- Achieved % = Achieved / Target times 100. 100% means you cooked "
            "exactly what was planned.\n"
            "- Pending = Achieved minus Target. A negative Pending means you "
            "are behind plan by that many kilos; positive means you cooked more "
            "than planned.\n\n"
            "Target vs Achieved: the grey dashed line is the plan, the solid "
            "line is what was made - when the solid line sits below grey you "
            "missed plan that period. By SKU: sort by Achieved % to float the "
            "weakest products up, or by Pending for the biggest shortfalls in "
            "kilos. Achievement rate by shift: for the top products, how each "
            "shift did against target - a low night-shift bar points to a "
            "night-shift gap."
        )

    with st.expander("WIP New"):
        st.markdown(
            "Work-in-progress holding - a live board of what is resting right "
            "now, before it is packed.\n\n"
            "- WIP New is a daily carry-over snapshot, not an event log. Every "
            "day, everything still resting is re-listed, and the same batch "
            "appears again the next day with its ageing increased, until it is "
            "packed and drops off. So a batch is counted on every day it sat.\n"
            "- Because of that, WIP is a live position, never an accumulation - "
            "you never sum across days. Every number on this tab uses the "
            "latest snapshot day only, so the tab is range-independent: the "
            "global time range does not change it.\n"
            "- Total resting now: boxes on the latest snapshot day.\n"
            "- Fresh (age 0): boxes made that day, on their first rest "
            "(manufacturing date equals the snapshot day).\n"
            "- Carry-over (age 1+): boxes that were already resting on an "
            "earlier day and are still here. Shown as a share of the total - "
            "near zero is healthy; a large or growing carry-over means product "
            "is backing up. This is the key health flag.\n"
            "- Aged beyond 2 days: lots on the latest day older than the normal "
            "1 to 2 day resting window - the stuck ones.\n"
            "- Rows with negative ageing (manufacturing date after the "
            "snapshot) are a data-entry error; they are ignored in the metrics "
            "and flagged with a caption to fix in the sheet."
        )

    with st.expander("Cut pieces"):
        st.markdown(
            "The cutting step - freshness of product waiting to be cut.\n\n"
            "- Avg ageing: average days between being made and reaching this "
            "step. Lower is fresher.\n"
            "- Within 3 days: share of lots handled within 3 days of being "
            "made.\n"
            "- Aged over 7 days: how many lots sat longer than a week.\n\n"
            "Ageing distribution: how many lots fall in each age bucket - most "
            "should cluster at 0 to 3 days, a long tail means product is "
            "waiting too long. Oldest sitting stock: the lots that have waited "
            "longest, oldest at the top."
        )

    with st.expander("Conversion"):
        st.markdown(
            "Yield reference - how much finished product each item converts "
            "to. Deliberately light; this is a reference, not a trend.\n\n"
            "- Actual vs ideal yield: the bar is the yield actually achieved, "
            "the tick marker is that product's own ideal yield. The gap is how "
            "far short of ideal it landed.\n"
            "- Gap = Achieved minus Ideal. A negative Gap means the product "
            "came in below its own target yield.\n"
            "- Every product has its own ideal, so compare each bar to its own "
            "tick, not to the others."
        )
