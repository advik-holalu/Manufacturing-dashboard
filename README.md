# GO DESi - Production Dashboard

Five tabs, one per source sheet of the Shift Report workbook: MFG, Cooking
Target, WIP New, Cut pieces, Conversion.

## Run it now (sample data, zero setup)

```bash
cd godesi_dashboard
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

It opens in your browser on http://localhost:8501 using the bundled sample
data in `sample_data/`. Everything works - filters, tabs, charts - so you can
see the whole thing before touching Google Cloud.

## Go live on the real Google Sheet

Two edits, both covered step by step when we do the linking together:

1. In `utils/config.py`:
   - set `DATA_SOURCE = "gsheets"`
   - set `GSHEET_ID` to the ID in your sheet URL
2. Add your service-account key: copy `.streamlit/secrets.toml.example` to
   `.streamlit/secrets.toml` and fill it in, then share the Google Sheet
   (view access) with the service-account email.

If a sheet tab is named differently from what the code expects, fix the
right-hand side of the `SHEETS` map in `utils/data.py`.

## Layout

```
app.py                 entry point, the five tabs
utils/
  config.py            DATA_SOURCE toggle + sheet ID
  data.py              fetch + clean + cache (the anti-crash core)
  ui.py                styling, info tooltips, metric cards, sidebar controls
  timegrain.py         day/week/month/year grouping
tabs/
  mfg.py               production volume, mix, line utilization
  cooking_target.py    plan vs actual, miss table, shift achievement rate
  wip_new.py           work-in-progress ageing
  cut_pieces.py        cutting freshness
  conversion.py        yield reference (thin data)
  _ageing.py           shared renderer for the two ageing tabs
sample_data/           bundled CSVs so it runs offline
```

## Design rules baked in

- One tab per sheet; each tab owns its own filters (unique widget keys, so
  switching tabs never disturbs another tab's selection).
- Surface data, not conclusions - no auto-insights, no pass/fail verdicts.
- An info (i) tooltip next to every metric and chart, in plain language.
- Hyphens only, never em-dashes.
- The fetch and the cleaning are cached; all derived columns are vectorized,
  so Streamlit Cloud does not re-do work on every click.
