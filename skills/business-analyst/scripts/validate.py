#!/usr/bin/env python3
"""Audit financial identities, assumptions and scenario results. Exit 2 on errors."""
import argparse
import json
import math
import sys
from pathlib import Path

from calculate import model, verify_input

TOL = 1e-5


def approx(a, b, title, errors):
    if not math.isclose(a, b, rel_tol=TOL, abs_tol=TOL):
        errors.append(f"{title}: {a:.6f} != {b:.6f}")


def audit(data: dict, output: dict | None = None, strict=False):
    errors = verify_input(data)
    blockers, warnings = [], []
    if errors:
        return {"errors": errors, "blockers": [], "warnings": []}
    p = data["project"]
    tax = data["taxes"]
    if not tax.get("verified") or not tax.get("source") or not tax.get("effective_date"):
        blockers.append("Tax rates/regime are not source-verified for country and effective date")
    if data.get("operating", {}).get("working_capital_delta_monthly", 0) == 0:
        warnings.append("Working capital is assumed zero; verify inventory/receivable/payable cycles")
    if data.get("market") and not data["market"].get("sizing_basis"):
        blockers.append("Market levels have no comparable sizing_basis for PAM/TAM/SAM/SOM")
    n = p["months"]
    funding = data.get("financing", {})
    equity = funding.get("equity_injections_monthly", 0)
    investor = funding.get("investor_contributions_monthly", 0)
    if not isinstance(equity, list): equity = [equity] * n
    if not isinstance(investor, list): investor = [investor] * n
    if any(iv > ev + TOL for ev, iv in zip(equity, investor)):
        blockers.append("Investor contributions exceed total equity injected for at least one month")
    if strict and blockers:
        errors.extend(blockers)

    result = model(data)
    for name, sc in result["results"].items():
        cash_before = float(funding.get("opening_cash", 0))
        prev_debt = 0.0
        for row in sc["monthly"]:
            prefix = f"{name} M{row['month_number']}"
            approx(row["revenue"] - row["cogs"], row["gross_profit"], prefix + " gross profit", errors)
            approx(row["gross_profit"] - row["other_variable_costs"] - row["turnover_tax"], row["contribution"], prefix + " contribution", errors)
            approx(row["contribution"] - row["fixed_costs"] - row["payroll"] - row["payroll_tax"] - row["marketing"], row["ebitda"], prefix + " EBITDA", errors)
            approx(row["ebitda"] - row["depreciation"], row["ebit"], prefix + " EBIT", errors)
            approx(row["ebit"] - row["interest"], row["profit_before_tax"], prefix + " PBT", errors)
            approx(row["profit_before_tax"] - row["income_tax_accrued"], row["net_income"], prefix + " NI", errors)
            approx(row["operating_cash_flow"] - row["capex"], row["free_cash_flow_before_financing"], prefix + " FCF", errors)
            approx(row["vat_output"] - row["vat_input"] - row["vat_paid"], row["vat_cash_movement"], prefix + " VAT cash", errors)
            cash = cash_before + row["free_cash_flow_before_financing"] + row["equity_injection"] + row["debt_draw"] - row["debt_principal_paid"] - row["dividends"]
            approx(row["ending_cash_committed"], cash, prefix + " cash bridge", errors)
            approx(row["debt_balance"], prev_debt + row["debt_draw"] - row["debt_principal_paid"], prefix + " debt bridge", errors)
            if row["debt_balance"] < -TOL: errors.append(prefix + " negative debt")
            if any(not math.isfinite(float(v)) for k, v in row.items() if isinstance(v, (int, float))):
                errors.append(prefix + " NaN or infinite output")
            cash_before, prev_debt = cash, row["debt_balance"]
        if sc["monthly"]:
            m = sc["metrics"]
            approx(sum(r["ebitda"] for r in sc["monthly"]), m["ebitda_total"], name + " total EBITDA", errors)
            approx(sum(r["revenue"] for r in sc["monthly"]), m["revenue_total"], name + " revenue total", errors)
            expected_gap = max(0, float(funding.get("minimum_cash_reserve", 0)) - min(float(funding.get("opening_cash", 0)), *(r["ending_cash_committed"] for r in sc["monthly"])))
            approx(m["additional_funding_required"], expected_gap, name + " funding gap", errors)
    if output:
        for name, new in result["results"].items():
            old = output.get("results", {}).get(name)
            if not old:
                errors.append(f"Saved output missing {name}")
                continue
            for field in ("ebitda_total", "revenue_total", "additional_funding_required", "project_fcf_at_horizon"):
                approx(old[field], new["metrics"][field], f"{name} output stale: {field}", errors)
    return {"errors": errors, "blockers": blockers, "warnings": warnings,
            "result": "FAIL" if errors else "NOT_INVESTOR_READY" if blockers else "PASS"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--results", type=Path)
    p.add_argument("--strict", action="store_true", help="treat unverified tax/market as errors")
    args = p.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    saved = json.loads(args.results.read_text(encoding="utf-8")) if args.results else None
    outcome = audit(data, saved, args.strict)
    print(json.dumps(outcome, indent=2, ensure_ascii=False))
    if outcome["errors"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
