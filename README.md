# Destination Change v4.1 - Optimized Multi-Vendor Package

## Streamlit app
Run `run_app.bat` or `streamlit run destination_change_streamlit_app.py`.

## Inputs
- PlanDetailTimeline raw CSV
- One or more PSW / Production Schedule CSV files
- One or more DueDateCalc / Transit Time XLSX files

The Streamlit UI detects vendor codes from the uploaded PSW files and shows the DueDateCalc mapping. DueDateCalc files are matched by vendor order; one file is reused for all vendors, and the last file is used as fallback when fewer files are uploaded than detected vendors.

## Main / Sub vendor Auto Separate rule
- If Main Vendor has Firm PO and Main Auto Separate is applied for the item, Sub Vendor uses normal allocation starting from Main Vendor After.
- If Main Vendor has no Firm PO or Main Auto Separate is not applied, Sub Vendor is allowed to run its own Auto Separate Balance Week logic.
- Healthy SS% defaults to 150% and is user-adjustable.

## Output
`Optimized Data` includes the approved optimization fields plus exactly these 9 PlanDetailTimeline metadata columns:
1. Item Class
2. Coll. Class
3. Series
4. Division
5. Item Status
6. Future Status
7. Hold/ Buy
8. ABC
9. Source Key

## Robustness / performance
- Make/Buy column names are recognized across common Ashley export variants such as `MakeBuy Code`, `Make Buy Code`, `Make/Buy Code`, and `Make-Buy Code`.
- Buy values such as `B`, `BUY`, and `B - Buy` are normalized to `B`.
- PlanDetailTimeline weekly date columns are detected from header values rather than fixed positions.
- Balance-week candidate metrics are cached per week to reduce repeated recalculation.
