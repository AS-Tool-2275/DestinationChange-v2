# Destination Change v4.5

## Main files
- `destination_change_streamlit_app.py` - Streamlit UI
- `destination_change_unified_flow.py` - optimization backend
- `requirements.txt` - Python dependencies

## v4.5 logic updates
- Auto Separate Firm PO Week / Balancing Week checks Healthy SS% across **all eligible Buy warehouses for each item**, not only destination-change receivers.
- Eligibility excludes fixed Warehouse 335 and hard-locked warehouses.
- Firm PO Week remains fixed at the selected Target Week.
- Balance Week can move forward while inventory metrics are recalculated fresh from PlanDetailTimeline.
- SI baseline at a candidate Balance Week is: Base SI at Balance Week - Planned POS through Balance Week - Firm PO anchored to Firm PO Week; Warehouse 335 additionally uses accumulated NET FCST under the existing rule.
- Main / other vendor supply and reconciliation gap are added exactly once.
- The approved PlanDetailTimeline metadata in `Optimized Data` remains exactly these 9 columns: Item Class, Coll. Class, Series, Division, Item Status, Future Status, Hold/ Buy, ABC, Source Key.
- Multiple DueDateCalc files remain supported and are mapped by detected PSW vendor order.

### v4.6 SI rule
When Auto Separate Firm PO Week / Balance Week is enabled, SI at the Balance Week subtracts all Timeline Firm PO from the selected Firm PO Week through the selected Balance Week, inclusive (using the existing ETA-to-ETD warehouse offset). The Firm PO at the selected Firm PO Week remains separately available for reconciliation. Main/other vendor supply and reconciliation are added only once.
