# Destination Change v4.4

## Main files
- `destination_change_streamlit_app.py`
- `destination_change_unified_flow.py`

## Inputs
- PlanDetailTimeline raw CSV
- PSW / Production Schedule CSV (one or more)
- DueDateCalc / transit-time Excel (one or more; upload order follows detected vendor order)

## v4.4 logic fix
When **Auto separate Firm PO week and balancing week** is enabled:

1. Calculate SI at the selected balancing week before new supply.
2. Add `Main Vendor F + Other Vendor Supply + Firm PO Reconciliation Gap` exactly once.
3. Use that result as `Sum of SI Wk3` / `Current SI` for optimization.
4. Do not add the same supply again in `prepare_optimizer_input`.

This prevents supply from being double-counted in Auto Separate mode.

## PlanDetailTimeline metadata in Optimized Data
Only these 9 columns are added:
1. Item Class
2. Coll. Class
3. Series
4. Division
5. Item Status
6. Future Status
7. Hold/ Buy
8. ABC
9. Source Key

## Other features retained
- Optional Healthy SS% threshold, default 150%
- Priority rules and Priority Rank
- Priority SI = 0 hard lock
- Zero-SS SI equalization fallback
- Multi-vendor / sub-vendor supply flow
- Optional OSQP second-pass sheets
