# Destination Change Streamlit App

## Main file
Run Streamlit with:

```bash
streamlit run destination_change_streamlit_app.py
```

## Key features
- PlanDetailTimeline + Production Schedule + DueDateCalc pipeline
- Optional priority rules with `SI` / `SS`
- Optional `Priority Rank` for ordered priority handling
- Optional `Auto separate firm week and balancing week`
- `SI = 0` behaves as a hard lock
- Warehouse 335 keeps its special SI logic with accumulated forecast to the selected week

## Notes
- Keep `destination_change_streamlit_app.py` and `destination_change_unified_flow.py` in the same folder.
- Upload order of PSW files is used to help map DueDateCalc files by vendor order.
