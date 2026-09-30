# Destination Change v4.2 Optimized

## Streamlit
Run:
`streamlit run destination_change_streamlit_app.py`

## Inputs
- PlanDetailTimeline raw CSV
- One or more PSW / Production Schedule CSV files
- One or more DueDateCalc / Transit Time Excel files

DueDateCalc files are mapped to detected PSW vendors by vendor order. One file may be reused for all vendors.

## Key logic
- Make/Buy Code is detected from common Ashley column-name variants.
- MakeBuy is treated as an Item + Warehouse attribute, so partially populated MakeBuy columns remain usable.
- Only MakeBuy = B / Buy items are optimized.
- Main vendor Firm PO is processed first.
- Sub vendor uses Main Vendor After as its baseline.
- Sub vendor Auto Separate is applied when the main vendor has no Firm PO or main Auto Separate was not applied for that item.
- When the main vendor has Firm PO and main Auto Separate was applied, sub vendor uses normal allocation logic.
- Healthy SS% defaults to 150% and is user-adjustable.
- Optional OSQP second-pass sheets are available.
- Optimized Data receives exactly 9 PlanDetailTimeline metadata columns:
  Item Class, Coll. Class, Series, Division, Item Status, Future Status, Hold/ Buy, ABC, Source Key.
