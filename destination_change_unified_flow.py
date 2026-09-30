from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

OUTPUT_METADATA_COLUMNS = [
    "Item Class", "Coll. Class", "Series", "Division", "Item Status",
    "Future Status", "Hold/ Buy", "ABC", "Source Key",
]

HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
HEADER_FONT = Font(color="FFFFFF", bold=True)

DTYPE_MAP = {
    "FIRM DEMAND": "FIRM DEMANDS", "FIRM DEMANDS": "FIRM DEMANDS",
    "FIRM POS": "FIRM POS", "FIRM PO": "FIRM POS",
    "PLANNED POS": "PLANNED POS", "PLANNED PO": "PLANNED POS",
    "SHIPPABLE INV": "SHIPPABLE INV", "SHIPPABLE INVENTORY": "SHIPPABLE INV",
    "SAFETY STK": "SAFETY STK", "SAFETY STOCK": "SAFETY STK",
    "NET FCST": "NET FCST", "NET FORECAST": "NET FCST",
}

@dataclass
class PriorityRule:
    whse: str
    mode: str
    value: float
    rank: int = 9999


def normalize_item(value) -> str:
    if pd.isna(value): return ""
    text = str(value).strip()
    m = re.match(r'^=\s*"(.*)"$', text)
    if m: text = m.group(1).strip()
    text = text.strip().strip('"').strip()
    return str(int(text)) if re.fullmatch(r"0*\d+", text) else text


def normalize_whse(value) -> str:
    if pd.isna(value): return ""
    text = str(value).strip()
    m = re.match(r'^=\s*"(.*)"$', text)
    if m: text = m.group(1).strip()
    try:
        x = float(text)
        if x.is_integer(): return str(int(x))
    except Exception: pass
    return text.upper()


def normalize_vendor(value) -> str:
    if pd.isna(value): return ""
    text = str(value).strip().upper()
    m = re.match(r'^=\s*"(.*)"$', text)
    if m: text = m.group(1).strip().upper()
    if re.fullmatch(r"0*\d+", text): return str(int(text))
    return text


def vendor_match_key(value) -> str:
    text = normalize_vendor(value)
    if not text: return ""
    m = re.search(r"\((0*\d+)\)", text)
    if m: return str(int(m.group(1)))
    nums = re.findall(r"0*\d+", text)
    return str(int(nums[-1])) if nums else text


def clean_dtype(series: pd.Series) -> pd.Series:
    s = series.fillna("").astype(str).str.strip().str.upper()
    return s.map(lambda x: DTYPE_MAP.get(x, x))


def normalize_pct(value: float) -> float:
    x = float(value)
    return x / 100.0 if abs(x) > 1 else x


def safe_ss_ratio(si: float, ss: float) -> float:
    if ss <= 0:
        return math.inf if si > 0 else (-math.inf if si < 0 else 0.0)
    return si / ss


def fmt_date(d: date) -> str:
    return f"{d.month}/{d.day}/{d.year}"


def saturday_of_current_week(today: Optional[date] = None) -> date:
    today = today or date.today()
    return today + timedelta(days=(5 - today.weekday()) % 7)


def find_vendor_col(df: pd.DataFrame) -> Optional[str]:
    exact = ["Vendor", "Vendor Code", "VendorCode", "Vendor #", "Vendor#", "Supplier", "Supplier Code"]
    lower = {str(c).strip().lower(): c for c in df.columns}
    for x in exact:
        if x.lower() in lower: return lower[x.lower()]
    return next((c for c in df.columns if "vendor" in str(c).lower() or "supplier" in str(c).lower()), None)


def find_header_row(path: str, first_token="Item #") -> int:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for i, line in enumerate(f):
            if line.lstrip().startswith(first_token): return i
    raise ValueError(f"Could not find CSV header starting with '{first_token}': {path}")


def read_report_csv(path: str) -> pd.DataFrame:
    header_row = find_header_row(path)
    df = pd.read_csv(path, skiprows=header_row, dtype=str, low_memory=False)
    df.columns = [str(c).strip() for c in df.columns]
    return df


def parse_date_col(c) -> Optional[date]:
    try: return pd.to_datetime(str(c).strip()).date()
    except Exception: return None


def load_due_date_offsets(path: str) -> Dict[str, int]:
    raw = pd.read_excel(path, sheet_name=0, header=None)
    header_idx = None
    for i in range(len(raw)):
        vals = [str(x).strip() for x in raw.iloc[i].tolist()]
        if "Warehouse" in vals and any("Delivery Days" in v for v in vals):
            header_idx = i; break
    if header_idx is None: raise ValueError("DueDateCalc header not found.")
    df = pd.read_excel(path, sheet_name=0, header=header_idx)
    df.columns = [str(c).strip() for c in df.columns]
    dcol = next((c for c in df.columns if "Delivery Days" in c), None)
    if dcol is None: raise ValueError("DueDateCalc Delivery Days column not found.")
    out = {}
    for _, r in df.iterrows():
        raw_wh = str(r.get("Warehouse", "")).strip()
        days = pd.to_numeric(r.get(dcol), errors="coerce")
        if not raw_wh or pd.isna(days): continue
        wh = normalize_whse(raw_wh.split("-", 1)[0])
        if wh: out[wh] = max(1, int(math.ceil(float(days) / 7.0)))
    if not out: raise ValueError("No warehouse offsets found in DueDateCalc.")
    return out


def detect_psw_vendors(paths: List[str]) -> pd.DataFrame:
    rows, seen, order = [], set(), 1
    for file_order, path in enumerate(paths or [], 1):
        try: df = read_report_csv(path)
        except Exception: continue
        vc = find_vendor_col(df)
        if not vc: continue
        vals = df[vc].map(normalize_vendor).map(vendor_match_key)
        for key in vals:
            if not key or key in seen: continue
            seen.add(key)
            rows.append({"Vendor Order": order, "Vendor Code": key, "Source PSW File Order": file_order})
            order += 1
    return pd.DataFrame(rows)


def build_vendor_offset_maps(vendor_df: pd.DataFrame, due_paths: List[str]) -> Dict[str, Dict[str, int]]:
    cache = {}
    out = {}
    if vendor_df is None or vendor_df.empty or not due_paths: return out
    for _, r in vendor_df.iterrows():
        key = str(r["Vendor Code"])
        order = int(r["Vendor Order"])
        path = due_paths[min(max(order - 1, 0), len(due_paths) - 1)]
        if path not in cache: cache[path] = load_due_date_offsets(path)
        out[key] = cache[path]
    return out


def load_plan_raw(path: str) -> Tuple[pd.DataFrame, Dict[date, str]]:
    raw = read_report_csv(path)
    required = ["Item #", "Whse", "Data Type", "Coll. Class", "MakeBuy Code"]
    missing = [c for c in required if c not in raw.columns]
    if missing: raise ValueError(f"PlanDetailTimeline missing columns: {missing}")
    raw["Item"] = raw["Item #"].map(normalize_item)
    raw["Whse"] = raw["Whse"].map(normalize_whse)
    raw["Data Type"] = clean_dtype(raw["Data Type"])
    raw["MakeBuy Code"] = raw["MakeBuy Code"].fillna("").astype(str).str.strip().str.upper()
    raw["Coll. Class"] = raw["Coll. Class"].fillna("").astype(str).str.strip()
    vc = find_vendor_col(raw)
    if vc:
        raw["Vendor"] = raw[vc].map(normalize_vendor)
        raw["Vendor Key"] = raw["Vendor"].map(vendor_match_key)
    else:
        raw["Vendor"] = ""; raw["Vendor Key"] = ""
    date_map = {d: c for c in raw.columns if (d := parse_date_col(c)) is not None}
    if not date_map: raise ValueError("No weekly date columns found in PlanDetailTimeline.")
    return raw, date_map


def load_psw_supply(paths: List[str], target_week: date, current_week: date,
                    main_offsets: Dict[str, int], vendor_offsets: Dict[str, Dict[str, int]]) -> pd.DataFrame:
    parts = []
    for file_order, path in enumerate(paths or [], 1):
        df = read_report_csv(path)
        req = ["Item #", "Whse", "S/F/P"]
        miss = [c for c in req if c not in df.columns]
        if miss: raise ValueError(f"PSW missing columns {miss}: {path}")
        vc = find_vendor_col(df)
        if vc is None: df["Vendor"] = ""; vc = "Vendor"
        df["Item"] = df["Item #"].map(normalize_item)
        df["Whse"] = df["Whse"].map(normalize_whse)
        df["Vendor"] = df[vc].map(normalize_vendor)
        df["Vendor Key"] = df["Vendor"].map(vendor_match_key)
        df["S/F/P"] = df["S/F/P"].fillna("").astype(str).str.strip().str.upper()
        f = df[df["S/F/P"] == "F"].copy()
        date_cols = []
        report_date = None
        try:
            with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
                for _ in range(10):
                    line = fh.readline()
                    if "Report Date" in line:
                        report_date = pd.to_datetime(line.split(":",1)[-1].strip()).date(); break
        except Exception: pass
        base_year = report_date.year if report_date else target_week.year
        for c in df.columns:
            m = re.fullmatch(r"(\d{1,2})/(\d{1,2})", str(c).strip())
            if m: date_cols.append(c)
        year = base_year
        prev_m = None
        mapping = {}
        for c in date_cols:
            m, d = map(int, str(c).split("/"))
            if prev_m is not None and m < prev_m: year += 1
            prev_m = m; mapping[date(year,m,d)] = c
        for wk, c in mapping.items():
            qty = pd.to_numeric(f[c], errors="coerce").fillna(0.0)
            x = f.loc[qty != 0, ["Item", "Whse", "Vendor", "Vendor Key"]].copy()
            if x.empty: continue
            x["PSW Week"] = wk
            x["PSW Quantity"] = qty.loc[qty != 0].to_numpy()
            x["Source PSW File Order"] = file_order
            x["Warehouse Offset Weeks"] = x["Whse"].map(main_offsets).fillna(0).astype(int)
            x["Vendor Transit Weeks"] = [vendor_offsets.get(vk, main_offsets).get(wh, main_offsets.get(wh, 0))
                                         for vk, wh in zip(x["Vendor Key"], x["Whse"])]
            x["Adjusted Supply Week"] = [wk + timedelta(days=7*(int(vt)-int(wo)))
                                          for wk, vt, wo in zip(x["PSW Week"], x["Vendor Transit Weeks"], x["Warehouse Offset Weeks"])]
            parts.append(x)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=["Item","Whse","Vendor","Vendor Key","PSW Week","PSW Quantity","Adjusted Supply Week"])


def prepare_supply_table(raw: pd.DataFrame, date_map: Dict[date,str], first_etd_week: date,
                         firm_week: date, current_week: date, offset_map: Dict[str,int],
                         supply_detail: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, pd.DataFrame]]:
    b = raw[raw["MakeBuy Code"] == "B"].copy()
    if b.empty: raise ValueError("No Buy (B) rows in PlanDetailTimeline.")
    date_cache = {d: pd.to_numeric(b[c], errors="coerce").fillna(0.0) for d,c in date_map.items()}
    vendor_map = b[["Item","Whse","Vendor","Vendor Key"]].drop_duplicates(["Item","Whse"])
    offsets = b["Whse"].map(offset_map).fillna(0).astype(int)
    b["_offset"] = offsets
    # Vectorized row-level target/planned/net metrics using grouped offsets.
    b["_target"] = 0.0; b["_planned"] = 0.0; b["_net"] = 0.0
    for off, idx in b.groupby("_offset", sort=False).groups.items():
        src_target = date_map.get(firm_week + timedelta(days=7*int(off)))
        if src_target:
            b.loc[idx, "_target"] = pd.to_numeric(b.loc[idx, src_target], errors="coerce").fillna(0.0)
        pdates = [d + timedelta(days=7*int(off)) for d in sorted(date_map) if first_etd_week <= d <= firm_week]
        pcols = [date_map[d] for d in pdates if d in date_map]
        if pcols:
            b.loc[idx, "_planned"] = b.loc[idx, pcols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
        ndates = [d for d in sorted(date_map) if current_week <= d <= firm_week]
        ncols = [date_map[d + timedelta(days=7*int(off))] for d in ndates if d + timedelta(days=7*int(off)) in date_map]
        if ncols:
            b.loc[idx, "_net"] = b.loc[idx, ncols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    key = ["Item","Whse","Coll. Class"]
    def agg(dt, val, name): return b[b["Data Type"] == dt].groupby(key, as_index=False)[val].sum().rename(columns={val:name})
    out = b[key].drop_duplicates().merge(agg("SHIPPABLE INV","_target","Base_SI"), on=key, how="left")
    for dt, val, name in [("PLANNED POS","_planned","PlannedPOS"),("FIRM POS","_target","Timeline Firm PO"),("NET FCST","_net","NetFcst"),("SAFETY STK","_target","SS")]:
        out = out.merge(agg(dt,val,name), on=key, how="left")
    for c in ["Base_SI","PlannedPOS","Timeline Firm PO","NetFcst","SS"]: out[c] = out[c].fillna(0.0)
    out = out.merge(vendor_map, on=["Item","Whse"], how="left")
    # Main vendor = Timeline vendor. Match PSW rows by normalized vendor key.
    out["Main F Wk3"] = 0.0
    out["Other Vendor Supply"] = 0.0
    out["Other Vendor List"] = ""
    if supply_detail is not None and not supply_detail.empty:
        joined = supply_detail.merge(
            vendor_map[["Item","Whse","Vendor Key"]],
            on=["Item","Whse"], how="left", suffixes=("_psw","_tl")
        )
        main = joined[(joined["Vendor Key_psw"] == joined["Vendor Key_tl"]) & (joined["PSW Week"] == firm_week)]
        if not main.empty:
            main_g = main.groupby(["Item","Whse"], as_index=False)["PSW Quantity"].sum().rename(columns={"PSW Quantity":"Main F Wk3"})
            out = out.merge(main_g,on=["Item","Whse"],how="left",suffixes=("","_m"))
            out["Main F Wk3"] = pd.to_numeric(out.get("Main F Wk3_m",out["Main F Wk3"]),errors="coerce").fillna(out["Main F Wk3"])
            if "Main F Wk3_m" in out.columns: out=out.drop(columns=["Main F Wk3_m"])
        other = joined[(joined["Vendor Key_psw"] != joined["Vendor Key_tl"])].copy()
        if "Adjusted Supply Week" in other.columns:
            other = other[(pd.to_datetime(other["Adjusted Supply Week"]).dt.date >= current_week) & (pd.to_datetime(other["Adjusted Supply Week"]).dt.date <= firm_week)]
        if not other.empty:
            og = other.groupby(["Item","Whse"],as_index=False)["PSW Quantity"].sum().rename(columns={"PSW Quantity":"Other Vendor Supply"})
            vg = other.groupby(["Item","Whse"])["Vendor"].agg(lambda s: ", ".join(sorted(set(x for x in s if x)))).reset_index().rename(columns={"Vendor":"Other Vendor List"})
            out=out.merge(og,on=["Item","Whse"],how="left",suffixes=("","_o")).merge(vg,on=["Item","Whse"],how="left",suffixes=("","_v"))
            out["Other Vendor Supply"] = pd.to_numeric(out.get("Other Vendor Supply_o",out["Other Vendor Supply"]),errors="coerce").fillna(out["Other Vendor Supply"])
            if "Other Vendor Supply_o" in out.columns: out=out.drop(columns=["Other Vendor Supply_o"])
            out["Other Vendor List"] = out.get("Other Vendor List_v",out["Other Vendor List"]).fillna("") if hasattr(out.get("Other Vendor List_v"),"fillna") else out["Other Vendor List"]
            if "Other Vendor List_v" in out.columns: out=out.drop(columns=["Other Vendor List_v"])

    out["Current SI"] = out["Base_SI"] - out["PlannedPOS"] - out["Timeline Firm PO"]
    out["Current SI-SS"] = out["Current SI"] - out["SS"]
    out["F Wk3"] = out["Main F Wk3"]
    out["Balance Week"] = firm_week
    return out, {"raw": b}


def build_balance_metrics(raw: pd.DataFrame, date_map: Dict[date,str], eval_week: date, current_week: date,
                          offset_map: Dict[str,int]) -> pd.DataFrame:
    b = raw[raw["MakeBuy Code"] == "B"].copy()
    b["_offset"] = b["Whse"].map(offset_map).fillna(0).astype(int)
    # Compute using same direct metric basis but for arbitrary eval week.
    b["_target"] = 0.0; b["_planned"] = 0.0; b["_net"] = 0.0
    for off, idx in b.groupby("_offset", sort=False).groups.items():
        tc = date_map.get(eval_week + timedelta(days=7*int(off)))
        if tc: b.loc[idx,"_target"] = pd.to_numeric(b.loc[idx,tc], errors="coerce").fillna(0.0)
        pdates = [d + timedelta(days=7*int(off)) for d in sorted(date_map) if min(date_map) <= d <= eval_week]
        pcols = [date_map[d] for d in pdates if d in date_map]
        if pcols: b.loc[idx,"_planned"] = b.loc[idx,pcols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
        ndates = [d for d in sorted(date_map) if current_week <= d <= eval_week]
        ncols = [date_map[d + timedelta(days=7*int(off))] for d in ndates if d + timedelta(days=7*int(off)) in date_map]
        if ncols: b.loc[idx,"_net"] = b.loc[idx,ncols].apply(pd.to_numeric, errors="coerce").fillna(0).sum(axis=1)
    key=["Item","Whse","Coll. Class"]
    def agg(dt,name,val):
        return b[b["Data Type"]==dt].groupby(key,as_index=False)[name].sum().rename(columns={name:val})
    out=b[key].drop_duplicates().merge(agg("SHIPPABLE INV","_target","Base_SI"),on=key,how="left")
    for dt,name,val in [("PLANNED POS","_planned","PlannedPOS"),("FIRM POS","_target","FirmPO"),("NET FCST","_net","NetFcst"),("SAFETY STK","_target","SS")]: out=out.merge(agg(dt,name,val),on=key,how="left")
    for c in ["Base_SI","PlannedPOS","FirmPO","NetFcst","SS"]: out[c]=out[c].fillna(0.0)
    out["Current SI"] = out["Base_SI"]-out["PlannedPOS"]-out["FirmPO"]
    out["Current SI-SS"] = out["Current SI"]-out["SS"]
    return out


def choose_recipient(rows, ranks=False):
    cand=[]
    for i,r in enumerate(rows):
        if r["locked"]: continue
        ss_pct=safe_ss_ratio(r["si_after"],r["ss"])
        rank = r["rank"] if ranks else 9999
        cand.append((rank,ss_pct,-r["si_after"],r["whse"],i))
    return sorted(cand)[0][-1] if cand else None


def allocate_item(group: pd.DataFrame, rules: Dict[str,PriorityRule], respect_rank=False) -> pd.DataFrame:
    rows=[]
    for _,r in group.iterrows():
        rr=rules.get(str(r["Whse"]))
        rows.append({
            "whse":str(r["Whse"]), "orig_f":int(round(r["F Wk3"])),
            "final_f":0, "si":float(r["Current SI"]), "si_after":float(r["Current SI"]),
            "ss":float(r["SS"]), "locked": bool(rr and rr.mode=="SI" and abs(rr.value)<=1e-12),
            "rank": rr.rank if rr else 9999,
        })
    total=sum(x["orig_f"] for x in rows); locked=sum(x["orig_f"] for x in rows if x["locked"]); rem=total-locked
    if rem<0: raise ValueError(f"Hard-locked Firm PO exceeds total for item {group['Item'].iloc[0]}.")
    # Priority-rule targets first.
    for x in rows:
        rr=rules.get(x["whse"])
        if rr and rr.mode in {"SI","SS"} and not x["locked"] and rr.value>0:
            target = max(0, int(math.ceil(rr.value*max(x["ss"],1)))) if rr.mode=="SS" else max(0, int(round(rr.value*max(x["si"],0))))
            add=max(0, target-x["final_f"])
            take=min(add,rem); x["final_f"]+=take; x["si_after"]+=take; rem-=take
    while rem>0:
        idx=choose_recipient(rows,respect_rank)
        if idx is None: break
        rows[idx]["final_f"]+=1; rows[idx]["si_after"]+=1; rem-=1
    if rem>0: raise ValueError(f"Could not allocate all Firm PO for item {group['Item'].iloc[0]}.")
    out=group.copy().reset_index(drop=True)
    out["F Wk3 Original"]=[x["orig_f"] for x in rows]
    out["F Wk3 After Destination Change"]=[x["final_f"] for x in rows]
    out["Net Destination Change"]=out["F Wk3 After Destination Change"]-out["F Wk3 Original"]
    out["Current SI After"]=out["Current SI"]+out["Net Destination Change"]
    out["SS % After"]=[safe_ss_ratio(si,ss) for si,ss in zip(out["Current SI After"],out["SS"])]
    return out


def apply_zero_ss_equalization(df):
    d = df.copy()
    for item, g in d.groupby("Item", sort=False):
        eligible = g[(pd.to_numeric(g["SS"], errors="coerce").fillna(0) <= 0)].copy()
        if len(eligible) < 2:
            continue
        idxs = eligible.index.tolist()
        current_f = {i: int(d.at[i, "F Wk3 After Destination Change"]) for i in idxs}
        current_si = {i: float(d.at[i, "Current SI After"]) for i in idxs}
        guard = 0
        while guard < 100000:
            guard += 1
            donor = max(idxs, key=lambda i: current_si[i])
            recipient = min(idxs, key=lambda i: current_si[i])
            if current_si[donor] - current_si[recipient] <= 1:
                break
            if current_f[donor] <= 0:
                break
            current_f[donor] -= 1
            current_f[recipient] += 1
            current_si[donor] -= 1
            current_si[recipient] += 1
        for i in idxs:
            d.at[i, "F Wk3 After Destination Change"] = current_f[i]
            d.at[i, "Current SI After"] = current_si[i]
            d.at[i, "Net Destination Change"] = current_f[i] - int(d.at[i, "F Wk3 Original"])
            d.at[i, "SS % After"] = safe_ss_ratio(current_si[i], float(d.at[i, "SS"]))
    return d


def auto_balance_week_map(raw,date_map,firm_week,current_week,offset_map,fixed_supply,rules,respect_rank,threshold):
    weeks=sorted([d for d in date_map if d>=firm_week] or [firm_week])
    items=raw["Item"].dropna().astype(str).unique().tolist(); selected={}; debug=[]
    # cache candidate metrics once per week; only evaluate unresolved items
    for wk in weeks:
        metrics=build_balance_metrics(raw,date_map,wk,current_week,offset_map)
        if metrics.empty: continue
        cand=metrics.merge(fixed_supply[[c for c in ["Item","Whse","Main F Wk3","Other Vendor Supply","Timeline Firm PO","Other Vendor List"] if c in fixed_supply.columns]].drop_duplicates(),on=["Item","Whse"],how="left")
        for c in ["Main F Wk3","Other Vendor Supply","Timeline Firm PO"]:
            if c not in cand: cand[c]=0.0
            cand[c]=pd.to_numeric(cand[c],errors="coerce").fillna(0.0)
        cand["F Wk3"]=cand["Main F Wk3"]
        cand["Current SI"] += cand["Main F Wk3"]+cand["Other Vendor Supply"]
        cand["Balance Week"]=wk
        for item in items:
            if item in selected: continue
            g=cand[cand["Item"].astype(str)==item].copy()
            if g.empty: continue
            alloc=allocate_item(g,{w:r for w,r in rules.items() if w in set(g["Whse"].astype(str))},respect_rank)
            ratios=pd.to_numeric(alloc["SS % After"],errors="coerce")
            recv=alloc[alloc["Net Destination Change"]>0]
            ok=not recv.empty and bool((pd.to_numeric(recv["SS % After"],errors="coerce")<=threshold).all())
            if ok or wk==weeks[-1]:
                selected[item]=wk
                debug.append([item,fmt_date(wk),float(ratios.min()) if not ratios.empty else None,float(ratios.max()) if not ratios.empty else None,len(recv),"Healthy" if ok else "Last available week"])
    for item in items:
        selected.setdefault(item,weeks[-1]);
    return selected,pd.DataFrame(debug,columns=["Item","Selected Balance Week","Min Receiver SS% After","Max Receiver SS% After","Receiver Count","Reason"])


def secondary_vendor_allocate(detail_full: pd.DataFrame, auto_balance: bool, healthy_threshold: float,
                              raw, date_map, firm_week, current_week, offset_map, rules, respect_rank) -> pd.DataFrame:
    d=detail_full.copy(); d["Other Vendor Supply"]=pd.to_numeric(d.get("Other Vendor Supply",0),errors="coerce").fillna(0.0)
    d["Sub Vendor Auto Balance Applied"] = False
    d["Sub Vendor Balance Week"] = firm_week
    # Main has actually applied auto-balance at item-level when Balance Week differs from firm week.
    for item,g in d.groupby("Item",sort=False):
        sub_orig=np.rint(g["Other Vendor Supply"].to_numpy()).astype(int)
        main_has_firm=float(g["F Wk3 Original"].sum())>0
        # "Applied" means the main-vendor auto-balance routine was executed for this Item,
        # not necessarily that the selected week moved away from Firm PO Week.
        main_auto_applied=bool(auto_balance and main_has_firm)
        sub_needs_auto = not (main_has_firm and main_auto_applied)
        if not sub_needs_auto:
            sub_final=np.rint(g["Other Vendor Supply"].to_numpy()).astype(int)
            d.loc[g.index,"Sub Vendor Auto Balance Applied"]=False
            d.loc[g.index,"Sub Vendor Balance Week"]=firm_week
        else:
            if sub_orig.sum()==0:
                sub_final=sub_orig
            else:
                # Sub vendor auto-balance uses the main-vendor completed SI baseline.
                temp=g.copy(); temp["F Wk3"]=sub_orig; temp["Current SI"]=temp["Current SI After"]; temp["SS"]=temp["SS"]
                # Sub-vendor Auto Separate is evaluated independently when the main-vendor
                # auto-balance was not actually applied for this Item.
                available=sorted([x for x in date_map if x>=firm_week] or [firm_week])
                chosen=firm_week
                for wk in available:
                    m=build_balance_metrics(raw,date_map,wk,current_week,offset_map)
                    gg=m[m["Item"].astype(str)==item].merge(g[["Whse","Current SI After","SS"]],on="Whse",how="left",suffixes=("","_main"))
                    gg["Current SI"]=gg["Current SI After"]
                    gg["F Wk3"]=gg["Whse"].map(dict(zip(g["Whse"],sub_orig))).fillna(0)
                    if not gg.empty:
                        a=allocate_item(gg,{w:r for w,r in rules.items() if w in set(gg["Whse"])},respect_rank)
                        rec=a[a["Net Destination Change"]>0]
                        if not rec.empty and bool((rec["SS % After"]<=healthy_threshold).all()):
                            chosen=wk; break
                    chosen=wk
                d.loc[g.index,"Sub Vendor Balance Week"]=chosen
                d.loc[g.index,"Sub Vendor Auto Balance Applied"]=True
                a=allocate_item(temp,{w:r for w,r in rules.items() if w in set(temp["Whse"])},respect_rank)
                sub_final=a["F Wk3 After Destination Change"].to_numpy(dtype=int)
        d.loc[g.index,"Sub Vendor F Original"]=sub_orig
        d.loc[g.index,"Sub Vendor F After Destination Change"]=sub_final
        d.loc[g.index,"Sub Vendor Net Destination Change"]=sub_final-sub_orig
        d.loc[g.index,"Sub Vendor SI Before"]=pd.to_numeric(g["Current SI After"],errors="coerce").fillna(0).to_numpy()
        d.loc[g.index,"Sub Vendor SI After"]=d.loc[g.index,"Sub Vendor SI Before"]+d.loc[g.index,"Sub Vendor Net Destination Change"]
        d.loc[g.index,"Sub Vendor SS% After"]=[safe_ss_ratio(si,ss) for si,ss in zip(d.loc[g.index,"Sub Vendor SI After"],d.loc[g.index,"SS"])]
    return d


def build_detail_output(detail_full: pd.DataFrame, metadata: Optional[pd.DataFrame]=None) -> pd.DataFrame:
    if detail_full is None or detail_full.empty: return pd.DataFrame()
    raw_cols=["Item","ProdResourceID","Whse","F Wk3","F Wk3 Original","F Wk3 After Destination Change",
              "Net Destination Change","Current SI After","SS % After","Firm PO Total","Main Vendor","Main F Wk3",
              "Other Vendor Supply","Other Vendor List","Sub Vendor F Original","Sub Vendor F After Destination Change",
              "Sub Vendor Net Destination Change","Sub Vendor SI Before","Sub Vendor SI After","Sub Vendor SS% After",
              "Sub Vendor Auto Balance Applied","Sub Vendor Balance Week","Balance Week"]
    cols=[c for c in raw_cols if c in detail_full.columns]
    out=detail_full[cols].copy()
    out=out.rename(columns={"F Wk3":"Firm PO","F Wk3 Original":"Firm PO Original",
                            "F Wk3 After Destination Change":"Firm PO After Destination Change",
                            "Current SI After":"SI After"})
    if metadata is not None and not metadata.empty:
        m=metadata[[c for c in ["Item","Whse"]+OUTPUT_METADATA_COLUMNS if c in metadata.columns]].drop_duplicates(["Item","Whse"])
        out=out.merge(m,on=["Item","Whse"],how="left")
    final=[c for c in ["Item","ProdResourceID","Whse","Firm PO","Firm PO Original","Firm PO After Destination Change",
                       "Net Destination Change","SI After","SS % After","Firm PO Total","Main Vendor","Main F Wk3",
                       "Other Vendor Supply","Other Vendor List","Sub Vendor F Original","Sub Vendor F After Destination Change",
                       "Sub Vendor Net Destination Change","Sub Vendor SI Before","Sub Vendor SI After","Sub Vendor SS% After",
                       "Sub Vendor Auto Balance Applied","Sub Vendor Balance Week","Balance Week"] if c in out.columns]
    final += [c for c in OUTPUT_METADATA_COLUMNS if c in out.columns]
    return out[final]


def metadata_from_plan(raw: pd.DataFrame) -> pd.DataFrame:
    candidates={c.lower():c for c in raw.columns}
    def get(name): return candidates.get(name.lower())
    rename={get(c):c for c in OUTPUT_METADATA_COLUMNS if get(c)}
    if "Item" not in raw or "Whse" not in raw: return pd.DataFrame()
    m=raw[["Item","Whse"]+[x for x in rename if x]].copy()
    m=m.rename(columns=rename)
    for c in OUTPUT_METADATA_COLUMNS:
        if c not in m: m[c]=""
    return m[["Item","Whse"]+OUTPUT_METADATA_COLUMNS].drop_duplicates(["Item","Whse"])


def write_excel_output(path: str, optimized: pd.DataFrame, summary: pd.DataFrame, debug: Dict[str,pd.DataFrame], osqp=None) -> str:
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        optimized.to_excel(writer,sheet_name="Optimized Data",index=False)
        if summary is not None and not summary.empty: summary.to_excel(writer,sheet_name="Summary",index=False)
        if osqp:
            for name,df in osqp.items():
                if df is not None and not df.empty: df.to_excel(writer,sheet_name=name[:31],index=False)
        # Debug sheets intentionally omitted from normal output to keep workbook lean.
        wb=writer.book
        for ws in wb.worksheets:
            ws.freeze_panes="A2"
            for cell in ws[1]: cell.fill=HEADER_FILL; cell.font=HEADER_FONT
            for cells in ws.columns:
                width=min(max(len(str(c.value)) if c.value is not None else 0 for c in cells)+2,45)
                ws.column_dimensions[get_column_letter(cells[0].column)].width=width
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    if cell.column and ws.cell(1,cell.column).value and "%" in str(ws.cell(1,cell.column).value):
                        if isinstance(cell.value,(int,float)) and math.isfinite(cell.value): cell.number_format="0.0%"
    return path


def build_osqp_sheets(detail_full: pd.DataFrame) -> Dict[str,pd.DataFrame]:
    try:
        import osqp
        from scipy import sparse
    except Exception:
        return {}
    if detail_full is None or detail_full.empty: return {}
    sheets={"OSQP Main Vendor":[],"OSQP Sub Vendor":[]}
    for _,g in detail_full.groupby("Item",sort=True):
        g=g.reset_index(); n=len(g)
        ss=pd.to_numeric(g["SS"],errors="coerce").fillna(0).to_numpy(float)
        si=pd.to_numeric(g["Current SI"],errors="coerce").fillna(0).to_numpy(float)
        f=np.rint(pd.to_numeric(g["F Wk3 Original"],errors="coerce").fillna(0)).astype(int).to_numpy()
        total=int(f.sum())
        if total>0 and n>0:
            mean_ss=float(np.mean(ss[ss>0])) if np.any(ss>0) else 1.0
            k=np.where(ss>0,1.0/np.maximum(ss,1e-9),0.0)
            c=np.where(ss>0,(si-f)/np.maximum(ss,1e-9)-1.0,0.0)
            w=np.where(ss>0,np.clip(ss/max(mean_ss,1e-9),0.1,10.0),0.1)
            P=sparse.diags(2*w*k*k+2e-5,format="csc")
            q=2*w*k*c-2e-5*f
            A=sparse.vstack([sparse.csr_matrix(np.ones((1,n))),sparse.eye(n,format="csc")],format="csc")
            prob=osqp.OSQP(); prob.setup(P=P,q=q,A=A,l=np.r_[total,np.zeros(n)],u=np.r_[total,np.full(n,total*2+max(total,1))],verbose=False,polishing=True)
            res=prob.solve(); x=np.rint(res.x).astype(int) if res.x is not None else f.copy()
            x=np.clip(x,0,None); diff=total-int(x.sum())
            while diff>0: x[np.argmin(np.maximum(si+x-f,0))]+=1; diff-=1
            while diff<0:
                cand=np.where(x>0)[0]
                if len(cand)==0: break
                x[cand[np.argmax(x[cand])]]-=1; diff+=1
        else: x=f.copy()
        for i in range(n):
            row={"Item":g.loc[i,"Item"],"Whse":g.loc[i,"Whse"],"Firm PO Original":int(f[i]),"OSQP Firm PO After":int(x[i]),"OSQP Net Destination Change":int(x[i]-f[i]),"OSQP SI After":float(si[i]+x[i]-f[i]),"OSQP SS% After":safe_ss_ratio(float(si[i]+x[i]-f[i]),float(ss[i]))}
            sheets["OSQP Main Vendor"].append(row)
        sub=np.rint(pd.to_numeric(g["Other Vendor Supply"],errors="coerce").fillna(0)).astype(int).to_numpy() if "Other Vendor Supply" in g else np.zeros(n,dtype=int)
        for i in range(n):
            sheets["OSQP Sub Vendor"].append({"Item":g.loc[i,"Item"],"Whse":g.loc[i,"Whse"],"Sub Vendor F Original":int(sub[i]),"OSQP Sub Vendor F After":int(sub[i]),"OSQP Sub Vendor Net Destination Change":0,"OSQP Sub Vendor SI After":float(si[i]),"OSQP Sub Vendor SS% After":safe_ss_ratio(float(si[i]),float(ss[i]))})
    return {k:pd.DataFrame(v) for k,v in sheets.items() if v}


def process_files(plan_detail_csv: str, production_schedule_csv: str, due_date_calc_xlsx: str, output_path: str,
                  target_week: date, current_week: Optional[date]=None, priority_rules=None,
                  psw_csv_paths=None, due_date_calc_xlsx_list=None, respect_priority_rank=False,
                  use_osqp_second_pass=False, auto_balance_week=False, healthy_ss_pct: float=150.0) -> str:
    current_week=current_week or saturday_of_current_week()
    if current_week>target_week: raise ValueError("Current Week cannot be later than Target Week.")
    due_paths=[x for x in (due_date_calc_xlsx_list or []) if x] or [due_date_calc_xlsx]
    psw_paths=psw_csv_paths or [production_schedule_csv]
    main_offsets=load_due_date_offsets(due_paths[0])
    vendor_df=detect_psw_vendors(psw_paths)
    vendor_offsets=build_vendor_offset_maps(vendor_df,due_paths)
    raw,date_map=load_plan_raw(plan_detail_csv)
    supply=load_psw_supply(psw_paths,target_week,current_week,main_offsets,vendor_offsets)
    base,_=prepare_supply_table(raw,date_map,min(date_map),target_week,current_week,main_offsets,supply)
    base["Firm PO"] = base["Main F Wk3"]
    base["F Wk3"] = base["Main F Wk3"]
    base["Current SI"] = base["Current SI"] + base["Main F Wk3"] + base["Other Vendor Supply"]
    base["Current SI-SS"] = base["Current SI"] - base["SS"]
    base["Firm PO Total"] = base.groupby("Item")["F Wk3"].transform("sum")
    if auto_balance_week:
        selected,debug_balance=auto_balance_week_map(raw,date_map,target_week,current_week,main_offsets,base,priority_rules or {},respect_priority_rank,float(healthy_ss_pct)/100.0)
        frames=[]
        for wk in sorted(set(selected.values())):
            m=build_balance_metrics(raw,date_map,wk,current_week,main_offsets)
            its=[i for i,v in selected.items() if v==wk]
            m=m[m["Item"].astype(str).isin(its)].copy()
            if m.empty: continue
            keep=[c for c in ["Item","Whse","Main F Wk3","Other Vendor Supply","Other Vendor List"] if c in base.columns]
            m=m.merge(base[keep].drop_duplicates(),on=["Item","Whse"],how="left")
            for c in ["Main F Wk3","Other Vendor Supply"]: m[c]=pd.to_numeric(m.get(c,0),errors="coerce").fillna(0.0)
            m["F Wk3"]=m["Main F Wk3"]; m["Current SI"]=m["Current SI"]+m["Main F Wk3"]+m["Other Vendor Supply"]; m["Balance Week"]=wk
            m["Firm PO Total"]=m.groupby("Item")["F Wk3"].transform("sum")
            frames.append(m)
        optimizer_input=pd.concat(frames,ignore_index=True) if frames else base.copy()
    else:
        debug_balance=pd.DataFrame()
        optimizer_input=base.copy(); optimizer_input["Balance Week"]=target_week
    records=[]
    for _,g in optimizer_input.groupby("Item",sort=True):
        rules={w:r for w,r in (priority_rules or {}).items() if w in set(g["Whse"].astype(str))}
        records.append(allocate_item(g.copy(),rules,respect_priority_rank))
    detail_full=pd.concat(records,ignore_index=True) if records else pd.DataFrame()
    detail_full=apply_zero_ss_equalization(detail_full)
    detail_full=secondary_vendor_allocate(detail_full,auto_balance_week, float(healthy_ss_pct)/100.0, raw,date_map,target_week,current_week,main_offsets,priority_rules or {},respect_priority_rank)
    # conservation: main Firm PO preserved; sub-vendor supply preserved item-by-item.
    if not detail_full.empty:
        before=detail_full.groupby("Item")["F Wk3 Original"].sum(); after=detail_full.groupby("Item")["F Wk3 After Destination Change"].sum()
        if not before.equals(after): raise ValueError("Main Firm PO total was not preserved.")
    metadata=metadata_from_plan(raw)
    optimized=build_detail_output(detail_full,metadata)
    summary=(optimized.groupby("Item",as_index=False).agg({"Firm PO After Destination Change":"sum","SI After":"min","SS % After":"min"}) if not optimized.empty else pd.DataFrame())
    dbg={"Balance Week Debug":debug_balance}
    osqp=build_osqp_sheets(detail_full) if use_osqp_second_pass else None
    return write_excel_output(output_path,optimized,summary,dbg,osqp=osqp)
