#!/usr/bin/env python3
"""Portable monthly driver-based business model (v1, stdlib only).

Inputs: JSON documented in schemas/project.schema.json. Outputs: monthly.json,
metrics.json and sources-and-assumptions.json. Conservative scope: prices and costs
NET of VAT, same-month collections, explicit WC adjustments, simple tax schedules.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
SCENARIO_DEFAULTS = {
    "volume_multiplier": 1.0, "price_multiplier": 1.0,
    "variable_cost_multiplier": 1.0, "fixed_cost_multiplier": 1.0,
    "retention_delta": 0.0, "conversion_multiplier": 1.0,
}


def month_vector(value: Any, n: int, name: str, *, signed: bool = False) -> list[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        values = [float(value)] * n
    elif isinstance(value, list) and len(value) == n:
        values = [float(x) for x in value]
    else:
        raise ValueError(f"{name}: expected numeric scalar or exactly {n} monthly values")
    if any(not math.isfinite(x) or (not signed and x < 0) for x in values):
        raise ValueError(f"{name}: invalid/non-finite/negative value")
    return values


def vector_field(section: dict, field: str, n: int, default=0.0, signed=False):
    return month_vector(section.get(field, default), n, field, signed=signed)


def rate(section: dict, field: str, default=0.0, *, max_value=1.0) -> float:
    v = float(section.get(field, default))
    if not 0 <= v <= max_value or not math.isfinite(v):
        raise ValueError(f"Invalid {field}: {v}")
    return v


def month_label(start: str, offset: int) -> str:
    y, m = (int(x) for x in start.split("-"))
    absolute = y * 12 + m - 1 + offset
    return f"{absolute // 12:04d}-{absolute % 12 + 1:02d}"


def irr_monthly(values: list[float]) -> float | None:
    """Unique-root IRR only; multiple sign changes return None."""
    signs = [1 if x > 1e-10 else -1 for x in values if abs(x) > 1e-10]
    if not signs or 1 not in signs or -1 not in signs:
        return None
    changes = sum(a != b for a, b in zip(signs, signs[1:]))
    if changes != 1:
        return None

    def npv(r):
        return sum(v / ((1 + r) ** i) for i, v in enumerate(values))

    lo, hi = -0.999, 8.0
    a, b = npv(lo), npv(hi)
    if not (math.isfinite(a) and math.isfinite(b)) or a * b > 0:
        return None
    for _ in range(180):
        mid = (lo + hi) / 2
        c = npv(mid)
        if a * c > 0:
            lo, a = mid, c
        else:
            hi = mid
    return (lo + hi) / 2


def pv_monthly(flows: list[float], annual_rate: float) -> float:
    rm = (1 + annual_rate) ** (1 / 12) - 1
    return sum(v / ((1 + rm) ** (i + 1)) for i, v in enumerate(flows))


def first_positive_month(rows: list[dict], key: str, *, strictly_positive=True):
    for row in rows:
        if (row[key] > 1e-7) if strictly_positive else (row[key] >= -1e-7):
            return row["month_number"]
    return None


def first_sustained_positive_month(rows, key):
    """Sustained means all subsequent observed months positive, NOT forever."""
    for i, row in enumerate(rows):
        if row[key] > 1e-7 and all(r[key] > 1e-7 for r in rows[i:]):
            return row["month_number"]
    return None


def make_tranches(rows: list[dict], min_reserve: float, period=3, initial_topup=0.0) -> list[dict]:
    """Quarterly-available tranche plan to protect reserve after *committed* funding."""
    schedule = []
    extra = initial_topup
    for s in range(0, len(rows), period):
        window = rows[s:s + period]
        lowest = min(r["ending_cash_committed"] + extra for r in window)
        needed = max(0.0, min_reserve - lowest)
        if needed > 1e-6:
            extra += needed
            schedule.append({"month_number": window[0]["month_number"], "month": window[0]["month"], "amount": round(needed, 2)})
    return schedule


def verify_input(data: dict) -> list[str]:
    errors = []
    try:
        project = data["project"]
        n = project["months"]
        assert isinstance(n, int) and 1 <= n <= 36
        assert re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", project["start_month"])
        assert all(project.get(k) for k in ("name", "currency", "country", "tax_regime"))
    except (KeyError, AssertionError, TypeError) as ex:
        return [f"project must contain name,currency,country,tax_regime,start_month,months<=36 ({ex})"]
    if not data.get("revenues"):
        errors.append("at least one revenue stream required")
    ids = [s.get("id") for s in data.get("revenues", [])]
    if len(ids) != len(set(ids)) or any(not x for x in ids):
        errors.append("revenue stream IDs must be unique and nonempty")
    for stream in data.get("revenues", []):
        kind = stream.get("kind")
        if kind not in {"units", "subscription", "freemium"}:
            errors.append(f"unknown stream kind: {kind}")
        if float(stream.get("unit_price", -1)) < 0 or float(stream.get("cogs_per_unit", -1)) < 0:
            errors.append(f"{stream.get('id')}: missing/negative unit_price/cogs_per_unit")
        for field in ("paid_retention_rate", "free_retention_rate", "processing_fee_rate", "limit_conversion_rate", "later_conversion_rate"):
            if field in stream:
                try:
                    rate(stream, field)
                except ValueError as ex:
                    errors.append(str(ex))
        for fld in ("monthly_units", "new_paid", "new_free"):
            if fld in stream:
                try:
                    month_vector(stream[fld], n, f"{stream['id']}.{fld}")
                except (ValueError, TypeError) as ex:
                    errors.append(str(ex))
    for section, fields in (("operating", ("fixed_monthly", "payroll_monthly", "marketing_monthly", "capex_monthly")),
                            ("financing", ("equity_injections_monthly", "debt_draws_monthly", "debt_principal_monthly", "dividends_monthly", "investor_contributions_monthly"))):
        for fld in fields:
            if fld in data.get(section, {}):
                try:
                    month_vector(data[section][fld], n, f"{section}.{fld}")
                except (ValueError, TypeError) as ex:
                    errors.append(str(ex))
    for fld in ("employer_payroll_rate", "corporate_income_rate", "turnover_tax_rate", "vat_rate", "vat_taxable_revenue_share", "vat_creditable_opex_share", "vat_creditable_capex_share"):
        if fld in data.get("taxes", {}):
            try:
                rate(data["taxes"], fld)
            except ValueError as ex:
                errors.append(str(ex))
    if data.get("taxes", {}).get("verified") is not True:
        # provenance is a readiness blocker, not a runtime failure
        pass
    elif not data.get("taxes", {}).get("source") or not data.get("taxes", {}).get("effective_date"):
        errors.append("verified taxes require a source and effective_date")
    return errors


def simulate(data: dict, scenario: dict) -> dict:
    p, op, tax, funding, val = (data.get(k, {}) for k in ("project", "operating", "taxes", "financing", "valuation"))
    n = int(p["months"])
    cfg = {**SCENARIO_DEFAULTS, **scenario}
    vm, pm = cfg["volume_multiplier"], cfg["price_multiplier"]
    cm, fm = cfg["variable_cost_multiplier"], cfg["fixed_cost_multiplier"]
    rd, convm = cfg["retention_delta"], cfg["conversion_multiplier"]
    fixed = vector_field(op, "fixed_monthly", n)
    wages = vector_field(op, "payroll_monthly", n)
    marketing = vector_field(op, "marketing_monthly", n)
    capex = vector_field(op, "capex_monthly", n)
    wc = vector_field(op, "working_capital_delta_monthly", n, signed=True)
    depreciation_override = op.get("depreciation_monthly_override")
    dep = (month_vector(depreciation_override, n, "depreciation_monthly_override") if depreciation_override is not None
           else [sum(capex[k] / int(op.get("capex_useful_life_months", 36)) for k in range(max(0, i - int(op.get("capex_useful_life_months", 36)) + 1), i + 1)) for i in range(n)])
    equity = vector_field(funding, "equity_injections_monthly", n)
    debt_draw = vector_field(funding, "debt_draws_monthly", n)
    principal = vector_field(funding, "debt_principal_monthly", n)
    dividends = vector_field(funding, "dividends_monthly", n)
    investor_contrib = vector_field(funding, "investor_contributions_monthly", n)
    exit_proceeds = vector_field(val, "exit_proceeds_monthly", n)
    ownership = rate(val, "investor_equity_fraction", 0)
    loan_interest = rate(funding, "debt_interest_rate_monthly", 0)
    corporate_rate = rate(tax, "corporate_income_rate", 0)
    employer_rate = rate(tax, "employer_payroll_rate", 0)
    turnover_rate = rate(tax, "turnover_tax_rate", 0)
    vat_rate = rate(tax, "vat_rate", 0)
    vat_rev_share = rate(tax, "vat_taxable_revenue_share", 1.0 if vat_rate else 0)
    vat_opex_share = rate(tax, "vat_creditable_opex_share", 0)
    vat_capex_share = rate(tax, "vat_creditable_capex_share", 0)
    inc_lag = int(tax.get("corporate_tax_payment_lag_months", 0))
    vat_lag = int(tax.get("vat_payment_lag_months", 0))
    if not 0 <= inc_lag <= n or not 0 <= vat_lag <= n:
        raise ValueError("invalid tax payment lag")
    cash = float(funding.get("opening_cash", 0))
    floor = float(funding.get("minimum_cash_reserve", 0))
    debt = 0.0
    carry_loss, vat_credit = 0.0, 0.0
    streams_state = {s["id"]: {"paid": 0.0, "free": 0.0} for s in data["revenues"]}
    tax_due = [0.0] * (n + inc_lag + 1)
    vat_due = [0.0] * (n + vat_lag + 1)
    rows = []
    proj_cumulative = 0.0
    investor_cumulative = 0.0
    investor_flows = []
    all_new_paid = all_marketing = all_subs_contribution = 0.0
    all_revenue = all_ebitda = 0.0
    project_fcf_list = []
    ppe_net = cumulative_wc = corporate_payable = vat_net_payable = book_equity = 0.0
    book_equity = float(funding.get("opening_cash", 0))
    investor_paid_in = 0.0
    investor_distributed = 0.0
    for i in range(n):
        details = {}
        rev = cogs = fees = free_cost = newly_paid = 0.0
        for s in data["revenues"]:
            state = streams_state[s["id"]]
            typ = s["kind"]
            price = float(s["unit_price"]) * pm
            cost = float(s["cogs_per_unit"]) * cm
            fee_rate = rate(s, "processing_fee_rate", 0)
            converted = free_active = new_paid = 0.0
            if typ == "units":
                units = vector_field(s, "monthly_units", n)[i] * vm
            else:
                paid_retention = min(1.0, max(0.0, rate(s, "paid_retention_rate", 0.8) + rd))
                new_paid = vector_field(s, "new_paid", n)[i] * vm
                if typ == "freemium":
                    free_retention = min(1.0, max(0.0, rate(s, "free_retention_rate", 0.7) + rd))
                    new_free = vector_field(s, "new_free", n)[i] * vm
                    free_pool = state["free"] * free_retention + new_free
                    start = int(s.get("limit_month", n + 1))
                    if i + 1 == start:
                        cr = rate(s, "limit_conversion_rate", 0)
                    elif i + 1 > start:
                        cr = rate(s, "later_conversion_rate", 0)
                    else:
                        cr = 0.0
                    converted = min(free_pool, free_pool * min(1.0, cr * convm))
                    free_active = free_pool - converted
                    state["free"] = free_active
                units = state["paid"] * paid_retention + new_paid + converted
                state["paid"] = units
                newly_paid += new_paid + converted
                if typ == "freemium":
                    free_cost += free_active * float(s.get("free_service_cost", 0)) * cm
            stream_rev, stream_cogs = units * price, units * cost
            stream_fee = stream_rev * fee_rate
            rev += stream_rev
            cogs += stream_cogs
            fees += stream_fee
            details[s["id"]] = {
                "type": typ, "units": units, "new_paid": new_paid + converted,
                "converted_from_free": converted, "free_active": free_active,
                "revenue": stream_rev, "cogs": stream_cogs, "fees": stream_fee,
                "marginal_contribution_per_unit": price * (1 - fee_rate - turnover_rate) - cost
            }
            if typ != "units":
                all_subs_contribution += stream_rev - stream_cogs - stream_fee
        fixed_cost = fixed[i] * fm
        wage = wages[i] * fm
        marketing_cost = marketing[i] * fm
        payroll_tax = wage * employer_rate
        turnover_tax = rev * turnover_rate
        gross_profit = rev - cogs - free_cost
        contribution = gross_profit - fees - turnover_tax
        ebitda = contribution - fixed_cost - wage - payroll_tax - marketing_cost
        debt += debt_draw[i]
        interest = debt * loan_interest
        payment = min(principal[i], debt)
        debt -= payment
        ebit = ebitda - dep[i]
        pbt = ebit - interest
        if tax.get("loss_carryforward", False):
            if pbt < 0:
                carry_loss += -pbt
                taxable = 0.0
            else:
                covered = min(carry_loss, pbt)
                taxable = pbt - covered
                carry_loss -= covered
        else:
            taxable = max(0, pbt)
        income_tax = taxable * corporate_rate
        net_income = pbt - income_tax
        tax_due[i + inc_lag] += income_tax
        tax_paid = tax_due[i]
        # All prices/costs entered net of recoverable VAT; collect VAT on sales,
        # pay input VAT on eligible cash costs, offset output VAT at settlement.
        vat_output = rev * vat_rate * vat_rev_share
        eligible_opex = (cogs + fees + free_cost + fixed_cost + marketing_cost) * vat_opex_share
        vat_input = (eligible_opex + capex[i] * vat_capex_share) * vat_rate
        payable = vat_output - vat_input - vat_credit
        if payable >= 0:
            vat_credit = 0.0
            vat_due[i + vat_lag] += payable
        else:
            vat_credit = -payable
        vat_paid = vat_due[i]
        vat_cash_movement = vat_output - vat_input - vat_paid
        working_capital = wc[i]
        # EBITDA already includes payroll tax and turnover tax. Interest and CIT
        # are separate. No deferred receivable/revenue modeling in v1.
        operating_cash_flow = ebitda - interest - tax_paid - working_capital + vat_cash_movement
        fcf = operating_cash_flow - capex[i]
        # Approximate project FCF excluding loan interest (with income tax still
        # reflecting the debt tax shield). Exposed separately from cash-before-funding.
        project_fcf = fcf + interest
        committed_finance = equity[i] + debt_draw[i] - payment - dividends[i]
        cash += fcf + committed_finance
        proj_cumulative += project_fcf
        investors_receipts = ownership * (dividends[i] + exit_proceeds[i])
        investor_flow = investors_receipts - investor_contrib[i]
        investor_cumulative += investor_flow
        investor_flows.append(investor_flow)
        investor_paid_in += investor_contrib[i]
        investor_distributed += investors_receipts
        all_new_paid += newly_paid
        all_marketing += marketing_cost
        all_revenue += rev
        all_ebitda += ebitda
        project_fcf_list.append(project_fcf)
        ppe_net += capex[i] - dep[i]
        cumulative_wc += working_capital
        corporate_payable += income_tax - tax_paid
        vat_net_payable += vat_cash_movement
        book_equity += equity[i] + net_income - dividends[i]
        balance_assets = cash + ppe_net + max(0, cumulative_wc) + max(0, -vat_net_payable)
        balance_liabilities = debt + corporate_payable + max(0, -cumulative_wc) + max(0, vat_net_payable)
        balance_check = balance_assets - balance_liabilities - book_equity
        rows.append({
            "month_number": i + 1, "month": month_label(p["start_month"], i),
            "streams": details, "revenue": rev, "cogs": cogs + free_cost,
            "other_variable_costs": fees, "turnover_tax": turnover_tax,
            "gross_profit": gross_profit, "contribution": contribution,
            "fixed_costs": fixed_cost, "payroll": wage, "payroll_tax": payroll_tax,
            "marketing": marketing_cost, "ebitda": ebitda, "depreciation": dep[i],
            "ebit": ebit, "interest": interest, "profit_before_tax": pbt,
            "income_tax_accrued": income_tax, "income_tax_paid": tax_paid,
            "net_income": net_income, "vat_output": vat_output, "vat_input": vat_input,
            "vat_paid": vat_paid, "vat_cash_movement": vat_cash_movement,
            "working_capital_delta": working_capital, "operating_cash_flow": operating_cash_flow,
            "capex": capex[i], "free_cash_flow_before_financing": fcf,
            "project_fcf_approx_unlevered": project_fcf,
            "cumulative_project_fcf": proj_cumulative,
            "equity_injection": equity[i], "debt_draw": debt_draw[i],
            "debt_principal_paid": payment, "debt_balance": debt,
            "dividends": dividends[i], "ending_cash_committed": cash,
            "investor_contribution": investor_contrib[i],
            "investor_cash_flow": investor_flow, "cumulative_investor_cf": investor_cumulative,
            "new_paid_customers": newly_paid,
            "balance_cash": cash, "balance_ppe_net": ppe_net,
            "balance_net_working_capital": cumulative_wc,
            "balance_income_tax_payable": corporate_payable,
            "balance_net_vat_liability": vat_net_payable,
            "balance_assets": balance_assets, "balance_liabilities": balance_liabilities,
            "balance_equity": book_equity, "balance_check": balance_check
        })
    # Range/period sensitivity for break-even is local to the primary stream.
    primary = data["revenues"][0]
    target = rows[min(n, 12) - 1]
    pdet = target["streams"][primary["id"]]
    per_unit_contribution = pdet["marginal_contribution_per_unit"]
    other_contributions = sum(d["units"] * d["marginal_contribution_per_unit"] for name, d in target["streams"].items() if name != primary["id"])
    # Freemium free costs count as fixed at THIS local month, not as per-unit paid cost.
    free_costs_now = sum(d["free_active"] * float(s.get("free_service_cost", 0)) * cm
                        for s in data["revenues"] for d in [target["streams"][s["id"]]] if s["kind"] == "freemium")
    burden = target["fixed_costs"] + target["payroll"] + target["payroll_tax"] + target["marketing"] + free_costs_now
    be_units = (math.ceil(max(0, burden - other_contributions) / per_unit_contribution)
                if per_unit_contribution > 0 else None)
    baseline_cash = float(funding.get("opening_cash", 0))
    min_cash = min(float(funding.get("opening_cash", 0)), *(r["ending_cash_committed"] for r in rows))
    outstanding_income_tax = max(0, sum(tax_due[n:]))
    outstanding_vat = max(0, sum(vat_due[n:]))
    loss_carry = carry_loss
    margin_ltv = {}
    for stream in data["revenues"]:
        if stream["kind"] in {"subscription", "freemium"}:
            pr = float(stream["unit_price"]) * pm
            pc = float(stream["cogs_per_unit"]) * cm
            fee = rate(stream, "processing_fee_rate", 0)
            monthly_contribution = pr * (1 - fee - turnover_rate) - pc
            surv = min(1, max(0, rate(stream, "paid_retention_rate", 0.8) + rd))
            horizon_ltv = monthly_contribution * sum(surv**i for i in range(n))
            margin_ltv[stream["id"]] = {
                "monthly_contribution": monthly_contribution,
                "paid_retention": surv, "contribution_ltv_horizon": horizon_ltv,
                "ltv_to_blended_cac": horizon_ltv / (all_marketing / all_new_paid) if all_new_paid > 0 and all_marketing > 0 else None
            }
    be_payback = (next((r["month_number"] for r in rows if r["cumulative_project_fcf"] >= 0 and
                        min(x["cumulative_project_fcf"] for x in rows[:r["month_number"]]) < 0), None))
    inv_payback = (next((r["month_number"] for r in rows if r["cumulative_investor_cf"] >= 0 and
                         investor_paid_in > 0 and min(x["cumulative_investor_cf"] for x in rows[:r["month_number"]]) < 0), None))
    irr = irr_monthly(investor_flows)
    discount = float(val.get("annual_discount_rate", 0))
    if discount < 0: raise ValueError("annual_discount_rate must be >=0")
    metrics = {
        "scenario": cfg.get("name", "base"), "months": n, "currency": p["currency"],
        "revenue_total": all_revenue, "ebitda_total": all_ebitda,
        "gross_margin": (sum(r["gross_profit"] for r in rows) / all_revenue) if all_revenue else None,
        "contribution_margin": (sum(r["contribution"] for r in rows) / all_revenue) if all_revenue else None,
        "first_ebitda_positive_month": first_positive_month(rows, "ebitda"),
        "sustained_ebitda_positive_month_in_horizon": first_sustained_positive_month(rows, "ebitda"),
        "first_operating_cash_positive_month": first_positive_month(rows, "operating_cash_flow"),
        "project_fcf_payback_month": be_payback,
        "investor_cash_payback_month": inv_payback,
        "break_even_primary_stream": primary["id"],
        "break_even_reference_month": target["month_number"],
        "break_even_primary_active_units": be_units,
        "break_even_primary_revenue": be_units * float(primary["unit_price"]) * pm if be_units is not None else None,
        "break_even_note": "Local EBITDA break-even for primary stream, other streams/free costs fixed at reference month; changes in capacity or mix require recomputation.",
        "minimum_committed_cash": min_cash,
        "minimum_cash_month": (0 if min_cash == float(funding.get("opening_cash", 0)) else next(r["month_number"] for r in rows if r["ending_cash_committed"] == min_cash)),
        "additional_funding_required": max(0, floor - min_cash),
        "recommended_quarterly_tranches": ([{"month_number": 0, "month": "PRE-LAUNCH", "amount": round(max(0, floor-baseline_cash), 2)}] if baseline_cash < floor else []) + make_tranches(rows, floor, initial_topup=max(0, floor-baseline_cash)),
        "cash_at_horizon": cash, "project_fcf_at_horizon": proj_cumulative,
        "income_tax_payable_at_horizon": outstanding_income_tax,
        "vat_payable_at_horizon": outstanding_vat,
        "unused_vat_credit_at_horizon": vat_credit,
        "tax_loss_carried_at_horizon": loss_carry,
        "debt_outstanding_at_horizon": debt,
        "balance_sheet_reconciliation_at_horizon": rows[-1]["balance_check"],
        "blended_marketing_cac_per_new_paid": all_marketing / all_new_paid if all_new_paid else None,
        "new_paying_customers_total": all_new_paid,
        "subscription_ltv": margin_ltv,
        "project_fcf_npv": pv_monthly(project_fcf_list, discount) - baseline_cash * 0,
        "investor_monthly_irr": irr,
        "investor_annual_irr": ((1 + irr) ** 12 - 1) if irr is not None else None,
        "investor_moic": investor_distributed / investor_paid_in if investor_paid_in else None,
        "investor_npv": pv_monthly(investor_flows, discount),
        "valuation_pre_money": val.get("pre_money_valuation"),
        "valuation_post_money_simple_round": (float(val["pre_money_valuation"]) + investor_paid_in) if val.get("pre_money_valuation") is not None else None,
        "investor_ownership_implied_simple_round": (investor_paid_in / (float(val["pre_money_valuation"]) + investor_paid_in)) if val.get("pre_money_valuation") is not None and (float(val["pre_money_valuation"]) + investor_paid_in)>0 else None,
        "investor_equity_fraction": ownership,
    }
    return {"metrics": metrics, "monthly": rows}


def model(data):
    errors = verify_input(data)
    if errors: raise ValueError("Invalid input:\n- " + "\n- ".join(errors))
    scenarios = data.get("scenarios") or [
        {"name": "base", **SCENARIO_DEFAULTS},
        {"name": "downside", **{**SCENARIO_DEFAULTS, "volume_multiplier": 0.85}},
        {"name": "upside", **{**SCENARIO_DEFAULTS, "volume_multiplier": 1.15}},
    ]
    if not any(s.get("name") == "base" for s in scenarios):
        scenarios.insert(0, {"name": "base", **SCENARIO_DEFAULTS})
    names = [s["name"] for s in scenarios]
    if len(names) != len(set(names)):
        raise ValueError("Scenario names must be unique")
    results = {s["name"]: simulate(data, s) for s in scenarios}
    warnings = [
        "Prices and input costs are net of VAT, recognized and collected in the same month; revenue deferrals/receivable schedules not modeled.",
        "Project FCF is approximate and uses leveraged income tax; project valuation needs a dedicated unlevered tax adjustment when debt is material.",
        "Simplified cash/PP&E/net-WC/tax/debt/equity balance sheet is provided; inventory details, deferred revenue and advanced country tax rules are not modeled.",
    ]
    if data["taxes"].get("verified") is not True:
        warnings.insert(0, "BLOCKER: tax jurisdiction/regime/rates not verified with authoritative effective-dated sources")
    if any(s.get("kind") == "freemium" for s in data["revenues"]):
        warnings.append("Freemium free-user acquisition spend is included in blended marketing CAC; longitudinal attribution is not modeled.")
    if sum(vector_field(data.get("financing", {}), "debt_draws_monthly", data["project"]["months"])) > 0:
        warnings.append("Investor and project payback differ; assess debt tax shield, repayment and financing terms before valuation.")
    return {"project": data["project"], "model_version": VERSION, "results": results,
            "warnings": warnings}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("--out", type=Path, default=Path("results"))
    args = p.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    calculated = model(data)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "monthly.json").write_text(json.dumps({k: v["monthly"] for k, v in calculated["results"].items()}, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out / "metrics.json").write_text(json.dumps({"project": calculated["project"], "model_version": VERSION,
            "results": {k: v["metrics"] for k, v in calculated["results"].items()}, "warnings": calculated["warnings"]}, indent=2, ensure_ascii=False), encoding="utf-8")
    (args.out / "sources-and-assumptions.json").write_text(json.dumps({"evidence": data.get("evidence", []),
                "tax_provenance": {k: data["taxes"].get(k) for k in ("source", "effective_date", "verified")},
                "market": data.get("market", {}), "scenarios": data.get("scenarios", [])}, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Calculated", ", ".join(calculated["results"]), "→", args.out)
    for name, result in calculated["results"].items():
        x = result["metrics"]
        print(f"  {name}: EBITDA {x['ebitda_total']:.2f}; funding gap {x['additional_funding_required']:.2f}; payback {x['project_fcf_payback_month']}")
    for w in calculated["warnings"]:
        print("WARNING:", w)


if __name__ == "__main__":
    main()
