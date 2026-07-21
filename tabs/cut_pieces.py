"""Tab 4 - Cut pieces. The cutting step. Shift is usable here, so keep it."""

from __future__ import annotations

import pandas as pd

from tabs._ageing import render_ageing


def render(df: pd.DataFrame, date_range=None) -> None:
    render_ageing(
        df, date_range, key="Cut", qty_col="Weight", qty_label="Weight (kg)",
        use_shift=True, stage_word="sits before it is cut",
    )
