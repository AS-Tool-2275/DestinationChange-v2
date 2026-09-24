# Destination Change Streamlit App

## GitHub / Streamlit Cloud files
- `destination_change_streamlit_app.py` - main Streamlit entry point
- `destination_change_unified_flow.py` - calculation backend
- `requirements.txt` - Python dependencies

## Main logic
- PSW / Production Schedule provides Firm PO (`S/F/P = F`).
- PSW vendor order is used to map DueDateCalc files by vendor.
- One DueDateCalc file can be shared by all detected vendors; the last uploaded file is the fallback when fewer files are uploaded than vendors.
- Auto balancing week is optional and uses the configurable Healthy %SS threshold (default 150%).
- Priority Rank is optional. Lower rank is processed first; the same rank is treated as one priority group.
- Priority SI = 0 is a hard lock.
- Multiple zero-SS warehouses use an automatic SI equalization fallback pass.
- Sub-vendor balancing starts from Main Vendor SI After and mirrors the main-vendor allocation logic using Other Vendor Supply as the input quantity.
- Warehouse 335 includes accumulated Net Forecast through the selected balancing week.
