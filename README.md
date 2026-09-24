# Destination Change App

## Run locally

```bash
pip install -r requirements.txt
streamlit run destination_change_streamlit_app.py
```

## Main file for Streamlit Cloud

`destination_change_streamlit_app.py`

## Notes

- `legacy_compatible` mode has been removed.
- DueDateCalc offset uses `due_date` logic only.
- `SI = 0` is hard-locked.
- The app supports optional `Priority Rank` and optional auto balancing week logic.
