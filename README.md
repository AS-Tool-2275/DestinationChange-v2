# Destination Change Streamlit App

Main entry point: `destination_change_streamlit_app.py`

The app supports:
- PSW-based vendor detection for DueDateCalc mapping
- Multiple DueDateCalc uploads in detected PSW vendor order
- One DueDateCalc shared across all vendors, or last-file fallback when fewer files are uploaded
- Automatic balancing-week selection when all warehouses for an item are above 150% SS%
- Optional Priority Rank
- Priority SI = 0 hard lock
- Zero-SS fallback SI equalization
- Sub-vendor suggestion using Main Vendor SI After as the next baseline and the same allocation logic
- Warehouse 335 accumulated NET FCST through the selected balancing week
- Output `Optimized Data` with Firm PO and sub-vendor columns

Deploy `destination_change_streamlit_app.py` as the Streamlit main file.
