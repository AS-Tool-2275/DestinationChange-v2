# Destination Change App

## Streamlit entry point
`destination_change_streamlit_app.py`

## Inputs
1. `PlanDetailTimeline.csv`
2. One or more `PSW / Production Schedule.csv` files
3. One or more `DueDateCalc.xlsx` files

## Vendor-aware DueDateCalc mapping
Vendor order is detected from PSW / Production Schedule files.
- DueDateCalc #1 -> Vendor #1
- DueDateCalc #2 -> Vendor #2
- DueDateCalc #3 -> Vendor #3
- If only one DueDateCalc is uploaded, all vendors use the same transit mapping.
- If fewer DueDateCalc files than vendors are uploaded, the last uploaded file is used as fallback.

## Optimization behavior
- Main vendor Firm PO is optimized first.
- Optional Priority Rank: lower rank is processed first; equal rank is treated as the same priority group.
- Priority SI = 0 is a hard lock on the warehouse's original Firm PO quantity.
- Remaining allocation: Lowest SS% After -> Highest SI After -> Warehouse code.
- Automatic fallback equalization is applied to multiple zero-SS warehouses after the main allocation.
- Sub-vendor output mirrors the main allocation logic using Other Vendor Supply as the Firm PO pool and Main Vendor SI After as the starting SI.
- Warehouse 335 adds accumulated NET FCST from Current Week through the selected balancing week.
- The balancing week is automatically pushed forward when all warehouses of an item are above 150% SS%.

## Output
The normal download contains `Optimized Data`. Optional OSQP sheets can be added from the UI.
