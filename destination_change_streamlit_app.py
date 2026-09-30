from __future__ import annotations

import os
import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Dict

import pandas as pd
import streamlit as st

from destination_change_unified_flow import PriorityRule, detect_psw_vendors, fmt_date, normalize_pct, normalize_whse, process_files, saturday_of_current_week

st.set_page_config(page_title="Destination Change App", page_icon="📦", layout="wide")
st.title("Destination Change App")
st.caption("Optimized multi-vendor destination-change flow")

plan_file = st.file_uploader("PlanDetailTimeline raw CSV", type=["csv"])
psw_files = st.file_uploader("PSW / Production Schedule CSV", type=["csv"], accept_multiple_files=True)
due_files = st.file_uploader("DueDateCalc XLSX", type=["xlsx","xlsm","xls"], accept_multiple_files=True)

c1,c2 = st.columns(2)
with c1:
    current_week=st.date_input("Current Week", value=saturday_of_current_week(), format="MM/DD/YYYY")
with c2:
    target_week=st.date_input("Firm PO Week / Target Week", value=saturday_of_current_week()+timedelta(days=14), format="MM/DD/YYYY")

auto_balance=st.checkbox("Auto separate Firm PO week and balancing week", value=False)
healthy=st.number_input("Healthy SS% Threshold", min_value=1.0, max_value=1000.0, value=150.0, step=5.0)
use_osqp=st.checkbox("Add optional OSQP second-pass sheets", value=False)
use_rank=st.checkbox("Respect Priority Rank", value=False)

priority_df=st.data_editor(pd.DataFrame(columns=["Whse","Mode","Value","Rank"]), num_rows="dynamic")

def build_rules(df):
    rules={}
    if df is None or df.empty: return rules
    for _,r in df.iterrows():
        wh=normalize_whse(r.get("Whse","")); mode=str(r.get("Mode","")).strip().upper()
        if not wh or mode not in {"SI","SS"} or pd.isna(r.get("Value")): continue
        try: val=normalize_pct(float(r.get("Value"))); rank=int(r.get("Rank")) if not pd.isna(r.get("Rank")) else 9999
        except Exception: continue
        rules[wh]=PriorityRule(wh,mode,val,rank)
    return rules

if psw_files:
    with tempfile.TemporaryDirectory() as tmp:
        paths=[]
        for i,f in enumerate(psw_files,1):
            p=Path(tmp)/f"PSW_{i}.csv"; p.write_bytes(f.getbuffer()); paths.append(str(p))
        v=detect_psw_vendors(paths)
        if not v.empty: st.info("Detected vendor order: " + ", ".join(v["Vendor Code"].astype(str).tolist()))

if st.button("Run Full Flow", type="primary", use_container_width=True):
    if not plan_file or not psw_files or not due_files:
        st.error("Please upload PlanDetailTimeline, PSW / Production Schedule, and at least one DueDateCalc file.")
        st.stop()
    if current_week>target_week:
        st.error("Current Week cannot be later than Target Week."); st.stop()
    with tempfile.TemporaryDirectory() as tmp:
        plan_path=str(Path(tmp)/"PlanDetailTimeline.csv"); Path(plan_path).write_bytes(plan_file.getbuffer())
        psw_paths=[]
        for i,f in enumerate(psw_files,1):
            p=Path(tmp)/f"PSW_{i}.csv"; p.write_bytes(f.getbuffer()); psw_paths.append(str(p))
        due_paths=[]
        for i,f in enumerate(due_files,1):
            p=Path(tmp)/f"DueDateCalc_{i}.xlsx"; p.write_bytes(f.getbuffer()); due_paths.append(str(p))
        out_path=str(Path(tmp)/f"destination_change_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        try:
            final=process_files(plan_path,psw_paths[0],due_paths[0],out_path,target_week,current_week,build_rules(priority_df),psw_paths,due_paths,use_osqp_second_pass=use_osqp,auto_balance_week=auto_balance,healthy_ss_pct=healthy)
            st.session_state["output_bytes"]=Path(final).read_bytes(); st.session_state["output_name"]=Path(final).name
            st.success("Completed successfully.")
        except Exception as exc:
            st.error(f"Processing failed: {exc}")
            st.stop()

if "output_bytes" in st.session_state:
    st.download_button("Download Optimized Excel", st.session_state["output_bytes"], file_name=st.session_state["output_name"], mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
