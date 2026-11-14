#!/usr/bin/env python3
"""Consistent PAM/TAM/SAM/SOM numerical normalization (optional module).

A project must explicitly define the same audience basis for all levels;
normalized annual revenue is an *illustrative potential*, not a forecast.
"""
import argparse
import json
from pathlib import Path
from calculate import model

LEVELS = ("PAM", "TAM", "SAM", "SOM")


def size_market(data):
    market = data.get("market") or {}
    levels = market.get("levels")
    if not levels or any(k not in levels for k in LEVELS):
        raise ValueError("market.levels must contain PAM, TAM, SAM and SOM")
    basis = market.get("sizing_basis")
    if not basis: raise ValueError("market.sizing_basis required; e.g. annual_unique_addressable_buyers")
    result = {}
    for level in LEVELS:
        item=levels[level]
        if item.get("basis") != basis:
            raise ValueError(f"{level}: basis '{item.get('basis')}' differs from '{basis}'. Normalize or keep separate.")
        a = float(item["audience"])
        if a < 0: raise ValueError(f"{level}: audience must be nonnegative")
        result[level] = {"audience":a,"basis":basis,"source_ids":item.get("source_ids",[])}
    audience_list=[result[k]["audience"] for k in LEVELS]
    if any(x < y for x,y in zip(audience_list,audience_list[1:])):
        raise ValueError("PAM >= TAM >= SAM >= SOM must hold for nested segment counts")
    mon=market.get("monetization",{})
    method=mon.get("method")
    if method=="explicit":
        annual_per_unit=float(mon["annual_net_revenue_per_audience"])
        source = "explicit documented annual net-revenue assumption"
    elif method=="from_model":
        calculated=model(data)
        sc=mon.get("scenario","base")
        if sc not in calculated["results"]:
            raise ValueError(f"Scenario {sc} not found")
        rows=calculated["results"][sc]["monthly"]
        end=int(mon.get("end_month",len(rows)))
        if end < 12 or end > len(rows):
            raise ValueError("Need a complete 12-month revenue window within the model")
        chosen=mon.get("revenue_stream_ids") or [s["id"] for s in data["revenues"]]
        all_ids={s["id"] for s in data["revenues"]}
        if any(k not in all_ids for k in chosen): raise ValueError("Unknown revenue_stream_ids")
        revenue=sum(sum(r["streams"][sid]["revenue"] for sid in chosen) for r in rows[end-12:end])
        som=result["SOM"]["audience"]
        if not som: raise ValueError("SOM audience must be positive")
        annual_per_unit=revenue/som
        source=f"model scenario={sc}; 12 months M{end-11}–M{end}; stream ids={','.join(chosen)}"
    else:
        raise ValueError("market.monetization.method must be 'explicit' or 'from_model'")
    if annual_per_unit < 0: raise ValueError("Annual value cannot be negative")
    for level in LEVELS:
        result[level]["annual_revenue_potential"]=result[level]["audience"]*annual_per_unit
    return {"sizing_basis":basis,"currency":data["project"]["currency"],
            "annual_net_revenue_per_audience":annual_per_unit,
            "scenario_method":source,"levels":result,
            "caution":"Normalized market capacity at SAME scenario economics. It is not proven demand; do not equate it with achievable sales or investor return."}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    report=size_market(json.loads(args.input.read_text(encoding="utf-8")))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Market model written:",args.out)
    for k,v in report["levels"].items():
        print(k,f"{v['audience']:,.0f}",f"{v['annual_revenue_potential']:,.0f} {report['currency']}/year")


if __name__=="__main__":main()
