# Destination Change v4.0

This package implements the current Destination Change flow with the agreed multi-vendor Auto Separate behavior and a faster execution path.

## Key updates
- Main vendor: Auto Separate Firm PO Week vs Balancing Week can run per Item.
- Sub vendor: Auto Separate is applied when the main vendor has no Firm PO or when main Auto Separate was not actually applied for that Item.
- Sub vendor: when main vendor has Firm PO and main Auto Separate was actually applied, sub vendor uses normal allocation logic from the completed Main Vendor result.
- PlanDetailTimeline metadata added to `Optimized Data`: exactly 9 columns only:
  `Item Class`, `Coll. Class`, `Series`, `Division`, `Item Status`, `Future Status`, `Hold/ Buy`, `ABC`, `Source Key`.
- Output uses an explicit whitelist so unexpected PlanDetailTimeline columns are not appended.
- PlanDetailTimeline weekly calculations are grouped by offset instead of recalculated row-by-row for each candidate week.

## Run
```bash
pip install -r requirements.txt
streamlit run destination_change_streamlit_app.py
```
