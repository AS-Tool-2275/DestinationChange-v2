# Destination Change v4.7 Optimized

This package keeps the v4.6 business logic and optimizes the Streamlit startup and rerun path.

## Main improvements
- Uses the actual Streamlit UI entry point.
- Backend optimizer is lazy-loaded, so the initial page does not import the full optimizer stack.
- PSW vendor detection is cached across Streamlit reruns.
- Multiple DueDateCalc files remain supported for vendor-specific transit mapping.
- OSQP/Scipy are optional; the default Streamlit environment does not need them for startup.
- No __pycache__ files are shipped.

## Run
1. Install `requirements.txt`.
2. Optional: install `requirements-optional-osqp.txt` to enable the OSQP second-pass.
3. Run `streamlit run destination_change_streamlit_app.py`.

## Business logic
The optimizer logic is carried forward from v4.6, including Auto Separate Firm PO Week vs Balancing Week, Healthy SS% checking, multi-vendor handling, and the v4.6 SI calculation changes.
