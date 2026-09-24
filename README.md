# Destination Change Streamlit App

## Main file
`destination_change_streamlit_app.py`

## Inputs
- PlanDetailTimeline raw CSV
- One or more PSW / Production Schedule CSV files
- One or more DueDateCalc Excel files

## Vendor-aware DueDateCalc mapping
- Vendor order is detected from the uploaded PSW / Production Schedule files.
- DueDateCalc #1 maps to Vendor #1, DueDateCalc #2 maps to Vendor #2, etc.
- If only one DueDateCalc is uploaded, all detected vendors use the same transit file.
- If fewer DueDateCalc files than detected vendors are uploaded, the last uploaded file is used as fallback.

## Optimization
- Firm PO comes from PSW rows where `S/F/P = F` at the selected Firm PO Week.
- Main-vendor Firm PO is optimized first.
- Priority rules are optional.
- Priority Rank is optional: lower rank is considered first; equal rank is treated as the same priority group.
- `Priority SI = 0` is a hard lock: the warehouse keeps its original Firm PO quantity.
- Remaining allocation uses Lowest SS% After -> Highest SI After -> Warehouse code.
- For multiple zero-SS warehouses, an automatic fallback equalization pass minimizes SI spread without changing total Firm PO by item.
- Sub-vendor suggestion mirrors the main-vendor allocation logic and starts from Main Vendor SI After.

## Automatic balancing week
The option `Auto separate Firm PO week and balancing week` is optional.

When disabled:
- Firm PO Week = Balancing Week.

When enabled:
- Firm PO Week stays fixed at the selected Target Week.
- The app evaluates the Firm PO allocation at the Firm PO Week first.
- Only receiving warehouses (`Net Destination Change > 0`) are checked against the 150% SS threshold.
- If a receiving warehouse remains above 150% SS after destination change, the app moves the Balancing Week forward one available week.
- For each new Balancing Week, SI / SS are recalculated fresh from PlanDetailTimeline; the previous week's SI is not carried forward.
- Firm PO quantity and Firm PO Reconciliation Gap remain tied to the original Firm PO Week.
- The process continues until no receiver is above 150% SS or the last available week is reached.

## Warehouse 335
For warehouse 335, SI uses accumulated Net Forecast directly from Current Week through the selected Balancing Week, without ETA -> ETD offset shifting.

## Output
The normal output contains the `Optimized Data` sheet. User-facing Firm PO columns are named:
- `Firm PO`
- `Firm PO Original`
- `Firm PO After Destination Change`

The output also includes balancing-week metrics and the sub-vendor suggestion columns. PlanDetailTimeline reference fields include only:
- Item Class
- Coll. Class
- Series
- Division
- Item Status
- Future Status
- Hold/ Buy
- ABC
- Source Key

OSQP is optional and is written to separate sheets when enabled.
