# GO DESi - Shift Report 2025 · Data Dictionary

_A running reference for the P1 sheets. Built sheet-by-sheet._

**Source file:** `Shift_Report_2025.xlsx` (originally a Google Sheet)
**P1 sheets (the only ones that matter):** MFG · Cooking Target · Cut pieces · WIP New · Conversion · Boondhi Production
**Confirmed:** none of the P1 sheets pull data from any other tab via formulas - each is self-contained.

**Shift key (applies workbook-wide):**
| Label | Shift | Hours |
|---|---|---|
| 1 / A | Shift 1 | 6am – 2pm |
| 2 / B | Shift 2 | 2pm – 10pm |
| 3 / C | Shift 3 | 10pm – 6am |
| G | General | 10am – 6pm |

_Note: MFG labels shifts 1/2/3/G; Cooking Target labels them A/B/C/G. Same three shifts, different notation._

---

## Sheet 1 - MFG (the master manufacturing log)

**What it is:** one row per production event - "on this date, this line, this shift cooked this much of this product."
**Real records:** ~3,838 (out of 22,129 rows; the rest are blank spacer rows - filter to rows with a Product Name).
**Date range:** Sept 2024 → present (~22 months).
**Real width:** 16 columns (A–P). Columns beyond P are empty ghost columns.

| Col | Header | Meaning | Notes |
|---|---|---|---|
| A | Date | Production day | Entered manually daily |
| B | Month | Month number | |
| C | Year | Year | |
| D | LINE | Which factory line (1 or 2; occasional 3) | 2 lines run in parallel. 14 rows say "3" - likely festival overflow or typo, worth confirming |
| E | Shift | Which shift (1/2/3/G) | Demand-driven; 3 shifts during festivals |
| F | Product Name | SKU manufactured | e.g. Kaju Katli Classic, Coconut Laddoo |
| G | BATCH SIZE (KG) | kg per batch | |
| H | NO. OF BATCHES | how many batches made | |
| I | TOTAL PRODUCTION | total kg produced | ✓ verified: **I = G × H** |
| J | Remarks | free-text notes | ~1% filled |
| K | FG UNITS (NET WEIGHT) | intended: finished-goods net weight | **effectively empty (~0%)** - floor doesn't fill it |
| L | FG UNITS (NET WEIGHT) | duplicate of K | empty |
| M | FG CONVERSION | intended: raw→finished yield | empty |
| N | REMARKS | second remarks col | ~0.1% filled |
| O | Column 1 | junk header | empty |
| P | DOWNTIME | intended: machine downtime | empty |

**Reliable columns for a dashboard:** A–I (plus occasional J remarks).
**Process gap to raise with higher-ups:** finished-goods weight, conversion yield, and downtime (K–P) are designed but not captured.

---

## Sheet 2 - Cooking Target (daily plan vs. actual)

**What it is:** one row per (date × SKU) - "we planned to cook X kg; here's how much each shift actually did." The plan-tracking counterpart to MFG.
**Real records:** ~1,287 (out of 1,294 rows - very clean).
**Date range:** Sept 2025 → present (~10 months). Started a year after MFG, so plan-vs-actual views only cover Sept 2025 onward.

| Col | Header | Meaning | Notes |
|---|---|---|---|
| A | Date | Production day | |
| B | SKU Name | Product | Same names as MFG |
| C | Target | kg planned for the day | |
| D | G - Done | kg cooked on General shift | |
| E | A-Done | kg cooked on Shift A (Shift 1) | most-used shift (~54% of rows) |
| F | B-Done | kg cooked on Shift B (Shift 2) | |
| G | C-Done | kg cooked on Shift C (Shift 3) | rare (~9%) - overnight, peak only |
| H | Achieved | total kg cooked | ✓ verified: **H = D + E + F + G** |
| I | Achieved % | Achieved ÷ Target | |
| J | Pending | Achieved − Target | **negative = behind plan**, positive = overshot |
| K | Remarks | why target missed | ~26% filled |
| L+ | (Unnamed) | stray junk | ignore |

**Reliable columns for a dashboard:** A–K, all usable.
**Dashboard hook:** Target vs Achieved vs Achieved% by SKU/date is the core "did we hit plan?" view.

---

## Sheet 3 - WIP New (work-in-progress holding / ageing)

**What it is:** tracks product from manufacture **until it's packed into secondary packaging** - the "work in progress" holding stage. One row = "as of this date, this much of this SKU (made on X date) is sitting as WIP, aged N days." Same 7-column shape as Cut pieces, but this is the holding-till-packed stage, not the cutting step.
**Real records:** ~3,829 (out of 3,835 rows - clean).
**Date range:** Aug 2025 → present.
**Width:** 7 columns.

| Col | Header | Meaning | Notes |
|---|---|---|---|
| A | Date | Entry/event day | 100% filled |
| B | Shift | Shift working (G/A/B/C) | **only ~36% filled** - weak for shift-level analysis |
| C | SKU | **Packaged** SKU name | e.g. "classic Kaju Katli Box 200 grams" |
| D | Manufacturing Date | When the product was originally made | usually a day/few before entry date |
| E | Number of boxes | count of units - **not only boxes**; can be MAP-trays depending on SKU | units, not kg |
| F | Ageing (Days) | days sitting as made-but-not-finished-good | ✓ verified: **F = A − D** (3822/3823 rows) |
| G | Remarks | free text | ~39% filled |

**Reliable columns for a dashboard:** A, C, D, E, F, G solid; B (Shift) weak.
**Dashboard hook:** WIP ageing by SKU - how long product waits before becoming finished goods.
**Data-quality flag:** ~24 rows have **negative ageing** (Manufacturing Date after entry date) - data-entry typos, filter/flag them.
**Not connected to Cut pieces:** WIP New and Cut pieces share the same 7-column shape and ageing logic, but they are **independent parallel logs** - no shared key, no data flow between them. Same structure ≠ linked. (Cut pieces = the cutting step; WIP New = holding until packed into secondary.)

---

## Sheet 4 - Conversion (yield: actual vs ideal per SKU)

**What it is:** tracks how much planned production actually converted into finished boxes, vs. each SKU's ideal yield. The concept MFG's dead columns K–M were meant to capture.
**Real records:** only **23 rows**, all from **May 20 – Jun 8, 2026** - a short-lived experiment, not an ongoing log. Thin data; use as a *formula reference*, not a data source.
**Width:** 8 columns.

| Col | Header | Meaning | Notes |
|---|---|---|---|
| A | Date | Day | |
| B | Item Name | Product | (header says "Item Name") |
| C | Actual | kg planned to make (per cooking plan) | the input quantity |
| D | Ideal Boxes | ideal box count = **C × (ideal yield %) ÷ (kg per box)** | both numbers are per-SKU; e.g. `=C×0.83/0.1` |
| E | Actual as mail WIP | actual boxes reported in the daily mail to founder/manager | manually entered, informal - but it's the actual that F measures |
| F | % Achieved Mail | **= (E × kg-per-box) ÷ C** - % of planned kg converted into finished boxes | achievement % |
| G | Ideal Conversion | per-SKU target yield % (0.77–0.95) | same % used inside D's formula |
| H | Remark | what went wrong on a miss | ~17% filled |

**Reliable columns for a dashboard:** concept is valuable (actual vs ideal yield per SKU) but data is too thin to build on. Treat as the **reference for how conversion should be calculated**; consistent capture going forward would be a process ask.

---

# Dashboard Build Notes (Streamlit + Google Sheets)

## Audience & v1 scope (decided)
**Primary audience:** decision-makers - founder / factory floor manager / production head. They want to *act*, not browse.
**v1 approach:** go **deep**, not broad. Nail **plan-vs-actual + shift performance** first. Other categories (line utilization, ageing, YoY seasonality) are v2 tabs.

**v1 spine - three linked views, one narrative:**
1. **"Are we hitting plan?"** - top-line Achieved% for the period + trend line. Green/red at a glance. Dashboard header.
2. **"Where are we bleeding?"** - SKUs ranked by worst/most-consistent misses. Surface the worst ~5, not all equally. Highest-value view for this audience.
3. **"Why - is it a shift problem?"** - per-SKU drilldown into G/A/B/C-Done contribution. Exposes patterns like "SKU X always misses on night shift." Drives staffing/supervision decisions.

**Data note for v1:** plan-vs-actual lives entirely in **Cooking Target** (starts Sept 2025, ~10 months, labels A/B/C/G). Raw shift history from MFG goes back to Sept 2024 but labels 1/2/3/G. For v1 lean on Cooking Target; bridge to MFG + normalize labels only if longer history is needed later.

## Insight categories (full menu, prioritized for this audience)
1. Plan-vs-reality (Cooking Target) - **v1 core**
2. Shift performance per SKU (unique to this data's granularity) - **v1 core**
3. Line utilization - two parallel lines, load balance - v2
4. Freshness/ageing risk (WIP New; Cut pieces separately) - v2
5. Trend & seasonality, incl. YoY around festivals (MFG, ~22mo) - v2

## Anti-crash architecture (CRITICAL - design for Streamlit Community Cloud from day 1)
**Myth to drop:** hidden tabs do NOT slow anything down. The Google Sheets API reads only the sheets/ranges you explicitly request - the other ~31 tabs are never fetched or parsed. Whitelist the ~4 needed sheets; the rest cost zero.

**What actually crashes Streamlit Cloud:** re-fetching + re-computing on every interaction (Streamlit re-runs the whole script per click). Same non-vectorized-recompute pattern that hit the SOV dashboard. Three-layer fix:
- **Layer 1 - cache the fetch:** wrap the Google Sheets pull in `@st.cache_data(ttl=300–600)` so it hits the API once per refresh window, not per click. All users share the cached copy.
- **Layer 2 - cache the cleaning:** filter-to-real-rows, ageing-typo removal, shift normalization all run once on the cached frame, not per rerun.
- **Layer 3 - vectorize + precompute:** all derived columns via pandas column ops (never per-row loops), built once up front. Filtering = slicing an already-built frame.

**Also:** Google Sheets API free tier ≈ 60 reads/min/user. Caching the fetch keeps you under quota - without it, simultaneous clicks throw rate-limit errors that look like crashes.
**Data volume is small** (low tens of thousands of rows total) - nowhere near memory limits. Crashes come from redundant work, not data size.

## Known data-cleaning steps for build time
- MFG: filter to rows with a Product Name (~3,838 of 22,129). Check the 14 "Line 3" rows.
- Cooking Target: clean stray "Shift" header-in-data value.
- Cut pieces: normalize messy Shift column (lowercase g/b, stray "2", ".A" typo).
- WIP New: Shift only ~36% filled (weak); drop/flag ~24 negative-ageing typo rows.
- Shift label normalization across sheets: MFG uses 1/2/3/G, others use A/B/C/G - map to one convention.

---

## Sheet 5 - Cut pieces (cutting + freshness log)

**What it is:** a log of the *cutting* step. After a sweet is cooked and has set/aged, it gets cut into pieces. One row = "on this date this shift cut this much of this packaged SKU; it was made on X date, so it aged N days." A quality/freshness log, NOT a plan-vs-actual sheet.
**Real records:** ~881 (out of 913 rows).
**Date range:** Nov 2025 -> present.
**Width:** 7 columns.

| Col | Header | Meaning | Notes |
|---|---|---|---|
| A | Date | Day it was **cut** | operational date of the cut, not the manufacture day; Ageing is measured from it |
| B | Shift | Shift that did the **cutting** | G/A/B/C. NOTE: this is the cutting shift, not the manufacturing shift. Messy values: lowercase g/b, a stray "2", a ".A" typo - clean before use |
| C | SKU | **Packaged** SKU name | e.g. "Kaju Katli Premium Box 180 grams" - pack-format names |
| D | Manufacturing Date | when the sweet was originally cooked | bridge back to MFG |
| E | Weight | kg cut | the quantity column for this step |
| F | Ageing (Days) | days between manufacture and cutting | verified: **F = A - D** |
| G | Remarks | free text | ~6% filled |

**Reliable columns:** all 7 usable (clean Shift first).
**Dashboard hook:** ageing by SKU - most product cut in 0-3 days, some sits 8-11. "Which SKUs age too long before cutting?"
**Twin of WIP New:** same 7-column shape and ageing math, but independent - no shared key, no data flow. Cut pieces = the cutting step; WIP New = holding until packed into secondary.

---

# BUILD BLUEPRINT - v1 Dashboard (Streamlit)

## Structure: one tab per sheet
Each tab = exactly one source sheet = one cached dataframe. Keeps sources un-mixed, maps to how sheets are maintained, and is kind to caching (switching tabs doesn't re-fetch; each sheet loads + caches once).

**Shared sidebar** (persists across tabs; each tab uses the subset that fits its data):
- TIME: Granularity toggle (Day / Week / Month / Year) + Period dropdown + "Compare to previous" toggle
- FILTERS: SKU (multi-select), Shift (G/A/B/C pills), Line (1/2 pills)

Granularity sets what one bar/point means. Period + Compare drive all "vs prev" deltas and the faint dashed previous-period overlay.

### Tab 1 - MFG (raw production, ~22 months, the volume story)
Full time controls work here (only tab with enough history for Year grain + long comparison).
- KPI row: Total produced (kg), Batches, Active SKUs - each with vs-prev delta
- Production over time (bar, by chosen grain)
- Product mix over time (stacked area, share of total)
- Line utilization (Line 1 vs Line 2 grouped bars over time)

### Tab 2 - Cooking Target (plan vs actual - THE core decision tab)
Weekly/Monthly grain (only ~10 months history; Year grain not useful yet).
- KPI row: Achieved, Target, Achieved %, Pending - each with vs-prev delta
- Target vs Achieved trend (2 lines + optional faint dashed prev period)
- By-SKU sortable table: SKU / Achieved / Achieved % / Delta prev / Pending
- Achievement rate by shift: same SKU split across G/A/B/C (grouped bars). This is the CORRECTED shift view - "does this SKU hit target better on some shifts?" NOT "which shift made it."

### Tab 3 - WIP New (work-in-progress ageing)
Shift NOT used as a control here (only ~36% filled - note it in the sidebar).
- KPI row: Avg ageing (days), Cut within 3 days (%), Aged >7 days (count)
- Ageing distribution (histogram: 0d,1d,2d,...6d+)
- Oldest sitting stock (table sorted desc by ageing)

### Tab 4 - Cut pieces (cutting freshness)
Same layout as WIP New (they're twins). Shift IS usable here, so keep it as a filter.
- Same KPI row + histogram + oldest-stock table, pointed at the cutting step.

### Tab 5 - Conversion (yield reference - deliberately light)
Thin data (23 rows, May-Jun 2026). Show an honest banner up top saying so.
- Actual vs ideal yield per SKU (bar = actual, marker line = ideal)
- Small reference table: SKU / Ideal / Achieved / Gap
- No trend charts - not enough history.

## UI RULES (apply everywhere, all tabs)
1. **Info tooltips:** a subtle (i) info-circle next to every metric and every chart. On hover, plain-language help: how to read it, how it's computed, or the caveat that matters. Examples of the voice:
   - Pending: "Achieved minus Target. A negative number means you're short by that many kilos."
   - Achievement rate by shift: "If a product does 90% on day shifts but 48% on nights, that's a night-shift gap worth a look. Only shows shifts that actually ran."
2. **Voice: direct and human.** Like a colleague explaining it. No corporate hedging, no jargon. Short.
3. **Surface data, not conclusions.** No alert banners, no auto-insights, no red/green pass-fail verdicts. Show the number/split/trend; let the human judge. (Deltas may use color for direction only, not judgment.)
4. **NO em-dashes anywhere.** Hyphens (-) only. Applies to all labels, tooltips, copy.
5. **Round every displayed number.** Integers for counts/kg, 1 decimal for percentages.

## Data caveats to respect in the build
- Year granularity + period-over-period only have deep history on MFG-sourced views (Tab 1). Cooking Target tops out ~10 months (YoY waits for more data).
- Achievement-rate-by-shift depends on Cooking Target shift columns being filled - sanity-check coverage before leaning on it.
- Conversion is a reference tab, not an analytics tab - keep it honest and light.
