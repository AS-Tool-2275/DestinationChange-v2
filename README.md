# Destination Change Streamlit

## Main file
`destination_change_streamlit_app.py`

## Features
- Multi-file PSW / Production Schedule upload
- Vendor order detection from PSW for DueDateCalc mapping
- Multiple DueDateCalc files; one-file shared-transit fallback and last-file fallback
- Optional Priority Rank
- Priority SI = 0 hard lock
- Optional automatic Firm PO Week vs Balancing Week
- User-defined Healthy SS% Threshold (default 150%)
- Fresh SI / SS calculation at each balancing week; Firm PO remains tied to the selected Firm PO Week
- Automatic zero-SS SI equalization fallback
- Main vendor optimization followed by mirrored sub-vendor suggestion using Main Vendor SI After as baseline
- Warehouse 335 accumulated NET FCST through the selected balancing week
- Optimized Data includes balancing-week SI/SS% plus PlanDetailTimeline reference attributes
