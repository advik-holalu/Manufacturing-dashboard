"""Map the granularity choice to a pandas period and a nice label."""

from __future__ import annotations

import pandas as pd

_FREQ = {"Day": "D", "Week": "W", "Month": "M", "Year": "Y"}
_LABEL = {
    "Day": "%d %b",
    "Week": "%d %b",
    "Month": "%b %y",
    "Year": "%Y",
}


def grouper(dates: pd.Series, grain: str) -> pd.Series:
    """Return a period-start Series to group by, aligned to the grain."""
    freq = _FREQ[grain]
    return dates.dt.to_period(freq).dt.start_time


def fmt(dates: pd.Series, grain: str) -> pd.Series:
    return dates.dt.strftime(_LABEL[grain])
