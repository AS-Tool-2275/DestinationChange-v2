# Destination Change Streamlit App

## Main file
`destination_change_streamlit_app.py`

## Features
- PlanDetailTimeline + PSW / Production Schedule + one or more DueDateCalc files
- PSW-based vendor order detection for DueDateCalc mapping
- Optional Priority Rank (lower rank first; same rank treated together)
- Priority SI = 0 hard lock
- Automatic Firm PO week vs balancing week (optional)
- Zero-SS SI equalization fallback
- Multi-vendor / sub-vendor suggestion flow using Main Vendor SI After as the sub-vendor baseline
- Warehouse 335 accumulated NET FCST logic through the selected balancing week
- Optional OSQP second-pass sheets
- Output column naming uses `Firm PO` instead of `F Wk3`

## Streamlit Cloud
Set the main file path to:
`destination_change_streamlit_app.py`
