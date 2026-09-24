# Destination Change Streamlit App

## Main file
`destination_change_streamlit_app.py`

## Features
- Multi-vendor PSW vendor-order detection for DueDateCalc mapping.
- Multiple DueDateCalc uploads. One file = shared transit; fewer files than vendors = last file fallback.
- Optional Priority Rank: lower rank is processed first; same rank is treated as one priority group.
- Priority SI = 0 is a hard lock on the warehouse's original Firm PO.
- Optional automatic Firm PO week vs. balancing week. When enabled, if all warehouses for an item are above 150% SS, the balancing week moves forward until at least one warehouse is at or below 150% or the last available week is reached.
- Warehouse 335 accumulates Net Forecast directly from Current Week through the balancing week without ETA/ETD offset shifting.
- Zero-SS fallback equalization pass.
- Sub-vendor destination change suggestion starts from Main Vendor SI After and mirrors the main-vendor priority logic.
- Output column `Firm PO` is the user-facing name for the selected Firm PO quantity.

## Run
```bash
pip install -r requirements.txt
streamlit run destination_change_streamlit_app.py
```
