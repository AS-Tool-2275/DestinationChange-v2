# Destination Change Streamlit Package

## Run locally
pip install -r requirements.txt
streamlit run destination_change_streamlit_app.py

## Files
- destination_change_streamlit_app.py
- destination_change_unified_flow.py
- requirements.txt

## Notes
- PSW vendor order is detected from uploaded PSW / Production Schedule files.
- DueDateCalc upload order follows the detected vendor order.
- `SI = 0` is a hard lock.
- A fallback equalization pass is applied for groups with `Average of SS Wk3 = 0`.
- Sub-vendor columns are kept in `Optimized Data`.


Priority rules now support an optional Rank column. Smaller rank values are prioritized first; same rank values are treated as equal priority.
