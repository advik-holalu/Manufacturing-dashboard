"""
Central config. The two things you touch when going live.
"""

# "sample"  -> runs on bundled CSVs, zero setup (use this first)
# "gsheets" -> reads the live Google Sheet (needs service-account secrets)
DATA_SOURCE = "gsheets"

# The ID from your Google Sheet URL:
# https://docs.google.com/spreadsheets/d/THIS_PART/edit
# Only needed when DATA_SOURCE = "gsheets".
GSHEET_ID = "1_fcucrSa4DY3qTxpZCWp08fmU1LM2R2b_e2jWM1I6s0"
