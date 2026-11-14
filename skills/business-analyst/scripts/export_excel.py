#!/usr/bin/env python3
"""Export a native-formula monthly workbook from the same inputs as calculate.py.

Requires artifact_tool. All financial rows are Excel formulas; blue Inputs and
Parameters are editable. The Python calculator remains the independent QA oracle.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from artifact_tool import Workbook, SpreadsheetFile
from calculate import model, month_vector, vector_field, SCENARIO_DEFAULTS

HEADER = {"fill": "#1F2937", "font": {"color": "#FFFFFF", "bold": True}, "row_height": 24}
ACCENT = {"fill": "#E8EDF2", "font": {"color": "#111827", "bold": True}, "row_height": 21}
INPUT_COLOR = "#0000FF"
FORMULA_COLOR = "#000000"
LINK_COLOR = "#008000"


def col(n: int) -> str:
    """1-based Excel column."""
    ans = ""
    while n:
        n, rem = divmod(n - 1, 26)
        ans = chr(65 + rem) + ans
    return ans


def v(sheet, cell, value):
    sheet.get_range(cell).values = [[value]]


def f(sheet, cell, formula):
    sheet.get_range(cell).formulas = [[formula]]


def inputs_sheet(wb, data, n):
    sh = wb.worksheets.add("Inputs")
    sh.get_range("A1:D1").merge()
    v(sh, "A1", "EDITABLE MONTHLY DRIVERS · BLUE = INPUT")
    sh.get_range("A1:D1").format = HEADER
    v(sh, "A2", "MONTH")
    p = data["project"]
    y, m = map(int, p["start_month"].split("-"))
    months = [f"{(y*12+m-1+i)//12:04d}-{(y*12+m-1+i)%12+1:02d}" for i in range(n)]
    sh.get_range(f"C2:{col(n+2)}2").values = [months]
    op, fund, val = data.get("operating", {}), data.get("financing", {}), data.get("valuation", {})
    mapping = {
        "fixed": (4, op, "fixed_monthly", 0), "wages": (5, op, "payroll_monthly", 0),
        "marketing": (6, op, "marketing_monthly", 0), "capex": (7, op, "capex_monthly", 0),
        "wc": (8, op, "working_capital_delta_monthly", 0),
        "equity": (9, fund, "equity_injections_monthly", 0),
        "debt_draw": (10, fund, "debt_draws_monthly", 0),
        "principal": (11, fund, "debt_principal_monthly", 0),
        "dividends": (12, fund, "dividends_monthly", 0),
        "investor_contrib": (13, fund, "investor_contributions_monthly", 0),
        "exit": (14, val, "exit_proceeds_monthly", 0),
    }
    input_rows = {}
    for name, (row, sec, key, default) in mapping.items():
        input_rows[name] = row
        v(sh, f"A{row}", name)
        arr = vector_field(sec, key, n, default, signed=(name == "wc"))
        sh.get_range(f"C{row}:{col(n+2)}{row}").values = [arr]
    stream_rows = {}
    row = 17
    for stream in data["revenues"]:
        stream_rows[stream["id"]] = {}
        for key in ("monthly_units", "new_paid", "new_free"):
            stream_rows[stream["id"]][key] = row
            v(sh, f"A{row}", f"{stream['id']}.{key}")
            arr = vector_field(stream, key, n)
            sh.get_range(f"C{row}:{col(n+2)}{row}").values = [arr]
            row += 1
    sh.get_range(f"C4:{col(n+2)}{row-1}").format.font.color = INPUT_COLOR
    sh.get_range("A:A").format.column_width = 28
    sh.get_range(f"C:{col(n+2)}").format.column_width = 15
    sh.get_range("A2:B2").format = ACCENT
    sh.freeze_panes.freeze_rows(2)
    return sh, input_rows, stream_rows


def parameters_sheet(wb, data):
    sh = wb.worksheets.add("Parameters")
    sh.get_range("A1:D1").merge()
    v(sh, "A1", "SCENARIO-INDEPENDENT ASSUMPTIONS · BLUE = INPUT")
    sh.get_range("A1:D1").format = HEADER
    tax, fund, op, val = (data.get(k, {}) for k in ("taxes", "financing", "operating", "valuation"))
    params = [
        (2, "employer_payroll_rate", tax.get("employer_payroll_rate",0)),
        (3, "corporate_income_rate", tax.get("corporate_income_rate",0)),
        (4, "turnover_tax_rate", tax.get("turnover_tax_rate",0)),
        (5, "vat_rate", tax.get("vat_rate",0)),
        (6, "vat_taxable_revenue_share", tax.get("vat_taxable_revenue_share",1 if tax.get("vat_rate",0) else 0)),
        (7, "vat_creditable_opex_share", tax.get("vat_creditable_opex_share",0)),
        (8, "vat_creditable_capex_share", tax.get("vat_creditable_capex_share",0)),
        (9, "corporate_tax_payment_lag", tax.get("corporate_tax_payment_lag_months",0)),
        (10, "vat_payment_lag", tax.get("vat_payment_lag_months",0)),
        (11, "debt_interest_rate_monthly", fund.get("debt_interest_rate_monthly",0)),
        (12, "opening_cash", fund.get("opening_cash",0)),
        (13, "minimum_cash_reserve", fund.get("minimum_cash_reserve",0)),
        (14, "loss_carryforward", int(tax.get("loss_carryforward",False))),
        (15, "capex_useful_life_months", op.get("capex_useful_life_months",36)),
        (16, "investor_equity_fraction", val.get("investor_equity_fraction",0)),
        (17, "annual_discount_rate", val.get("annual_discount_rate",0)),
    ]
    for row, label, value in params:
        v(sh, f"A{row}", label); v(sh, f"B{row}", value)
    v(sh, "A18", "tax_provenance")
    v(sh, "B18", "verified" if tax.get("verified") else "UNVERIFIED")
    v(sh, "A19", "tax_source"); v(sh, "B19", tax.get("source", ""))
    v(sh, "A20", "tax_effective_date"); v(sh, "B20", tax.get("effective_date", ""))
    sh.get_range("A22:K22").values = [["stream_id","kind","unit_price","cogs_per_unit","processing_fee_rate","paid_retention_rate","free_retention_rate","free_service_cost","limit_month","limit_conversion_rate","later_conversion_rate"]]
    sh.get_range("A22:K22").format = ACCENT
    meta = {}
    for i, stream in enumerate(data["revenues"]):
        row = 23 + i
        meta[stream["id"]] = row
        sh.get_range(f"A{row}:K{row}").values = [[stream["id"], stream["kind"],
            stream["unit_price"], stream["cogs_per_unit"],stream.get("processing_fee_rate",0),
            stream.get("paid_retention_rate",0.8),stream.get("free_retention_rate",0.7),
            stream.get("free_service_cost",0),stream.get("limit_month",data["project"]["months"]+1),
            stream.get("limit_conversion_rate",0),stream.get("later_conversion_rate",0)]]
    sh.get_range(f"B2:B17").format.font.color = INPUT_COLOR
    sh.get_range(f"C23:K{22+len(data['revenues'])}").format.font.color = INPUT_COLOR
    sh.get_range("A:A").format.column_width = 28
    sh.get_range("B:B").format.column_width = 18
    sh.get_range("C:K").format.column_width = 19
    return sh, meta


def forecast_sheet(wb, data, config, ir, stream_rows, meta):
    name = str(config.get("name", "base"))
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", name)[:20]
    sheet_name = "Forecast_" + safe
    sh = wb.worksheets.add(sheet_name)
    n = data["project"]["months"]
    v(sh, "A1", "DRIVER-BASED FORECAST · " + name.upper())
    sh.get_range("A1:G1").merge(); sh.get_range("A1:G1").format = HEADER
    scenario_labels = [(4,"volume_multiplier"),(5,"price_multiplier"),(6,"variable_cost_multiplier"),
                       (7,"fixed_cost_multiplier"),(8,"retention_delta"),(9,"conversion_multiplier")]
    cfg={**SCENARIO_DEFAULTS,**config}
    for row,key in scenario_labels:
        v(sh, f"A{row}", key); v(sh, f"B{row}", cfg[key])
    sh.get_range("B4:B9").format.font.color = INPUT_COLOR
    v(sh, "A13", "MONTH")
    sh.get_range(f"C13:{col(n+2)}13").formulas = [[f"=Inputs!{col(i+3)}2" for i in range(n)]]
    sh.get_range(f"A13:{col(n+2)}13").format = ACCENT
    row = 16
    stream_idx = {}
    for s in data["revenues"]:
        meta_row=meta[s["id"]]
        b=row
        stream_idx[s["id"]] = {
            "free_pool":b, "converted":b+1, "free_active":b+2, "units":b+3,
            "new_paid":b+4,"revenue":b+5,"cogs":b+6,"fees":b+7,"free_cost":b+8,"contribution":b+9
        }
        for key,r in stream_idx[s["id"]].items(): v(sh, f"A{r}",f"{s['id']}.{key}")
        row += 11
    br = row + 2
    last_forecast_row = br + 53
    formula_matrix = [["=0" for _ in range(n)] for __ in range(last_forecast_row-16+1)]
    raw_formula = globals()["f"]
    def f(sheet, cell, formula):
        match = re.fullmatch(r"([A-Z]+)(\d+)", cell)
        if match and int(match.group(2)) >= 16:
            letters, rr = match.group(1), int(match.group(2))
            cc = 0
            for char in letters: cc = cc * 26 + (ord(char)-64)
            formula_matrix[rr-16][cc-3] = formula
        else:
            raw_formula(sheet, cell, formula)
    fields = ["revenue", "cogs", "fees", "turnover_tax", "gross_profit", "contribution", "fixed_cost", "payroll", "payroll_tax", "marketing", "ebitda", "depreciation", "ebit", "interest", "profit_before_tax", "tax_loss_carryforward", "taxable_profit", "income_tax_accrued", "income_tax_paid", "net_income", "vat_output", "vat_input", "vat_credit", "vat_accrued", "vat_paid", "vat_cash_movement", "working_capital_delta", "operating_cash", "capex", "free_cash_flow", "debt_draw", "debt_before_repayment", "debt_principal_paid", "debt_balance", "equity", "dividends", "ending_cash", "project_fcf_approx", "cum_project_fcf", "investor_contrib", "investor_distrib", "investor_cash_flow", "cum_investor_cf", "new_paid", "payback_crossing_flag", "balance_cash", "balance_ppe_net", "balance_wc_net", "balance_income_tax_payable", "balance_net_vat_liability", "balance_assets", "balance_liabilities", "balance_equity", "balance_check"]
    totals = {key:br+i for i,key in enumerate(fields)}
    for key,r in totals.items(): v(sh, f"A{r}",key)
    param=lambda coord: f"Parameters!${coord}"
    for i in range(n):
        c=col(i+3)
        pc=col(i+2) if i>0 else None
        prev=lambda key: f"{pc}{totals[key]}" if pc else "0"
        for s in data["revenues"]:
            idx=stream_idx[s["id"]]
            mr=meta[s["id"]]
            sf=lambda field: f"Parameters!${field}${mr}"
            inp=lambda field: f"Inputs!{c}{stream_rows[s['id']][field]}"
            rpaid=f"MAX(0,MIN(1,{sf('F')}+$B$8))"
            if s["kind"]=="units":
                for field in ("free_pool","converted","free_active","new_paid"):
                    f(sh, f"{c}{idx[field]}", "=0")
                f(sh, f"{c}{idx['units']}",f"={inp('monthly_units')}*$B$4")
            else:
                if s["kind"]=="freemium":
                    prevfree=f"{pc}{idx['free_active']}" if pc else "0"
                    f(sh,f"{c}{idx['free_pool']}",f"={prevfree}*MAX(0,MIN(1,{sf('G')}+$B$8))+{inp('new_free')}*$B$4")
                    f(sh,f"{c}{idx['converted']}",f"={c}{idx['free_pool']}*IF({i+1}={sf('I')},MIN(1,{sf('J')}*$B$9),IF({i+1}>{sf('I')},MIN(1,{sf('K')}*$B$9),0))")
                    f(sh,f"{c}{idx['free_active']}",f"={c}{idx['free_pool']}-{c}{idx['converted']}")
                else:
                    for field in ("free_pool","converted","free_active"):
                        f(sh, f"{c}{idx[field]}", "=0")
                prevpaid=f"{pc}{idx['units']}" if pc else "0"
                f(sh,f"{c}{idx['units']}",f"={prevpaid}*{rpaid}+{inp('new_paid')}*$B$4+{c}{idx['converted']}")
                f(sh,f"{c}{idx['new_paid']}",f"={inp('new_paid')}*$B$4+{c}{idx['converted']}")
            f(sh,f"{c}{idx['revenue']}",f"={c}{idx['units']}*{sf('C')}*$B$5")
            f(sh,f"{c}{idx['cogs']}",f"={c}{idx['units']}*{sf('D')}*$B$6")
            f(sh,f"{c}{idx['fees']}",f"={c}{idx['revenue']}*{sf('E')}")
            f(sh,f"{c}{idx['free_cost']}",f"={c}{idx['free_active']}*{sf('H')}*$B$6")
            f(sh,f"{c}{idx['contribution']}",f"={c}{idx['revenue']}*(1-{sf('E')}-{param('B4')})-{c}{idx['cogs']}-{c}{idx['free_cost']}")
        def sm(key):
            cells=[f"{c}{idx[key]}" for idx in stream_idx.values()]
            return "+".join(cells) if cells else "0"
        def setf(key,expr):f(sh,f"{c}{totals[key]}","="+expr)
        setf("revenue",sm("revenue"))
        setf("cogs",sm("cogs")+"+"+sm("free_cost"))
        setf("fees",sm("fees"))
        setf("turnover_tax",f"{c}{totals['revenue']}*{param('B4')}")
        setf("gross_profit",f"{c}{totals['revenue']}-{c}{totals['cogs']}")
        setf("contribution",f"{c}{totals['gross_profit']}-{c}{totals['fees']}-{c}{totals['turnover_tax']}")
        setf("fixed_cost",f"Inputs!{c}{ir['fixed']}*$B$7")
        setf("payroll",f"Inputs!{c}{ir['wages']}*$B$7")
        setf("payroll_tax",f"{c}{totals['payroll']}*{param('B2')}")
        setf("marketing",f"Inputs!{c}{ir['marketing']}*$B$7")
        setf("ebitda",f"{c}{totals['contribution']}-{c}{totals['fixed_cost']}-{c}{totals['payroll']}-{c}{totals['payroll_tax']}-{c}{totals['marketing']}")
        if "depreciation_monthly_override" in data.get("operating", {}):
            dep=month_vector(data["operating"]["depreciation_monthly_override"],n,"dep")[i]
            setf("depreciation",str(dep))
        else:
            lifetime=int(data.get("operating",{}).get("capex_useful_life_months",36))
            last=col(n+2)
            caprow=ir["capex"]
            setf("depreciation",f"SUM(INDEX(Inputs!$C${caprow}:${last}${caprow},1,MAX(1,{i+1}-{param('B15')}+1)):Inputs!{c}${caprow})/{param('B15')}")
        setf("ebit",f"{c}{totals['ebitda']}-{c}{totals['depreciation']}")
        setf("debt_draw",f"Inputs!{c}{ir['debt_draw']}")
        setf("debt_before_repayment",f"{prev('debt_balance')}+{c}{totals['debt_draw']}")
        setf("debt_principal_paid",f"MIN(Inputs!{c}{ir['principal']},{c}{totals['debt_before_repayment']})")
        setf("debt_balance",f"{c}{totals['debt_before_repayment']}-{c}{totals['debt_principal_paid']}")
        setf("interest",f"{c}{totals['debt_before_repayment']}*{param('B11')}")
        setf("profit_before_tax",f"{c}{totals['ebit']}-{c}{totals['interest']}")
        carry=prev('tax_loss_carryforward')
        setf("tax_loss_carryforward",f"IF({param('B14')}=1,IF({c}{totals['profit_before_tax']}<0,{carry}-{c}{totals['profit_before_tax']},MAX(0,{carry}-{c}{totals['profit_before_tax']})),0)")
        setf("taxable_profit",f"IF({param('B14')}=1,MAX(0,{c}{totals['profit_before_tax']}-{carry}),MAX(0,{c}{totals['profit_before_tax']}))")
        setf("income_tax_accrued",f"{c}{totals['taxable_profit']}*{param('B3')}")
        endcol=col(n+2)
        taxrow=totals["income_tax_accrued"]
        setf("income_tax_paid",f"IF({i+1}>{param('B9')},INDEX($C${taxrow}:${endcol}${taxrow},1,{i+1}-{param('B9')}),0)")
        setf("net_income",f"{c}{totals['profit_before_tax']}-{c}{totals['income_tax_accrued']}")
        setf("vat_output",f"{c}{totals['revenue']}*{param('B5')}*{param('B6')}")
        setf("capex",f"Inputs!{c}{ir['capex']}")
        setf("vat_input",f"(({c}{totals['cogs']}+{c}{totals['fees']}+{c}{totals['fixed_cost']}+{c}{totals['marketing']})*{param('B7')}+{c}{totals['capex']}*{param('B8')})*{param('B5')}")
        setf("vat_credit",f"MAX(0,{c}{totals['vat_input']}+{prev('vat_credit')}-{c}{totals['vat_output']})")
        setf("vat_accrued",f"MAX(0,{c}{totals['vat_output']}-{c}{totals['vat_input']}-{prev('vat_credit')})")
        vatrow=totals["vat_accrued"]
        setf("vat_paid",f"IF({i+1}>{param('B10')},INDEX($C${vatrow}:${endcol}${vatrow},1,{i+1}-{param('B10')}),0)")
        setf("vat_cash_movement",f"{c}{totals['vat_output']}-{c}{totals['vat_input']}-{c}{totals['vat_paid']}")
        setf("working_capital_delta",f"Inputs!{c}{ir['wc']}")
        setf("operating_cash",f"{c}{totals['ebitda']}-{c}{totals['interest']}-{c}{totals['income_tax_paid']}-{c}{totals['working_capital_delta']}+{c}{totals['vat_cash_movement']}")
        setf("free_cash_flow",f"{c}{totals['operating_cash']}-{c}{totals['capex']}")
        setf("equity",f"Inputs!{c}{ir['equity']}")
        setf("dividends",f"Inputs!{c}{ir['dividends']}")
        setf("ending_cash",f"{(prev('ending_cash') if pc else param('B12'))}+{c}{totals['free_cash_flow']}+{c}{totals['equity']}+{c}{totals['debt_draw']}-{c}{totals['debt_principal_paid']}-{c}{totals['dividends']}")
        setf("project_fcf_approx",f"{c}{totals['free_cash_flow']}+{c}{totals['interest']}")
        setf("cum_project_fcf",f"{prev('cum_project_fcf')}+{c}{totals['project_fcf_approx']}")
        setf("investor_contrib",f"Inputs!{c}{ir['investor_contrib']}")
        setf("investor_distrib",f"({c}{totals['dividends']}+Inputs!{c}{ir['exit']})*{param('B16')}")
        setf("investor_cash_flow",f"{c}{totals['investor_distrib']}-{c}{totals['investor_contrib']}")
        setf("cum_investor_cf",f"{prev('cum_investor_cf')}+{c}{totals['investor_cash_flow']}")
        setf("new_paid",sm("new_paid"))
        before_min = f"MIN($C${totals['cum_project_fcf']}:{pc}${totals['cum_project_fcf']})" if pc else "0"
        setf("payback_crossing_flag",f"IF(AND({c}{totals['cum_project_fcf']}>=0,{before_min}<0),1,0)")
        setf("balance_cash",f"{c}{totals['ending_cash']}")
        setf("balance_ppe_net",f"{prev('balance_ppe_net')}+{c}{totals['capex']}-{c}{totals['depreciation']}")
        setf("balance_wc_net",f"{prev('balance_wc_net')}+{c}{totals['working_capital_delta']}")
        setf("balance_income_tax_payable",f"{prev('balance_income_tax_payable')}+{c}{totals['income_tax_accrued']}-{c}{totals['income_tax_paid']}")
        setf("balance_net_vat_liability",f"{prev('balance_net_vat_liability')}+{c}{totals['vat_cash_movement']}")
        setf("balance_assets",f"{c}{totals['balance_cash']}+{c}{totals['balance_ppe_net']}+MAX(0,{c}{totals['balance_wc_net']})+MAX(0,-{c}{totals['balance_net_vat_liability']})")
        setf("balance_liabilities",f"{c}{totals['debt_balance']}+{c}{totals['balance_income_tax_payable']}+MAX(0,-{c}{totals['balance_wc_net']})+MAX(0,{c}{totals['balance_net_vat_liability']})")
        setf("balance_equity",f"{(prev('balance_equity') if pc else param('B12'))}+{c}{totals['equity']}+{c}{totals['net_income']}-{c}{totals['dividends']}")
        setf("balance_check",f"{c}{totals['balance_assets']}-{c}{totals['balance_liabilities']}-{c}{totals['balance_equity']}")
    sh.get_range(f"C16:{col(n+2)}{totals['balance_check']}").formulas = formula_matrix
    sh.get_range(f"C16:{col(n+2)}{totals['balance_check']}").format.font.color = FORMULA_COLOR
    for label in ("revenue","gross_profit","contribution","ebitda","net_income","operating_cash","free_cash_flow","ending_cash","cum_project_fcf"):
        sh.get_range(f"A{totals[label]}:{col(n+2)}{totals[label]}").format.fill = "#F1F5F9"
    sh.get_range("A:A").format.column_width = 34
    sh.get_range(f"C:{col(n+2)}").format.column_width = 15
    sh.freeze_panes.freeze_rows(13)
    return sheet_name, totals, stream_idx


def summary_sheet(wb, specs, data):
    sh=wb.worksheets.add("Summary")
    sh.get_range("A1:J1").merge(); v(sh,"A1","BUSINESS MODEL · SCENARIO SUMMARY")
    sh.get_range("A1:I1").format = HEADER
    headings=["Scenario","Revenue","EBITDA","Funding gap","Project FCF","Break-even units","Project payback M","Blended CAC","LTV (primary)","Balance check"]
    sh.get_range("A3:J3").values=[headings]
    sh.get_range("A3:J3").format=ACCENT
    n=data["project"]["months"]
    end=col(n+2)
    for idx,(name,totals,streams) in enumerate(specs):
        r=4+idx
        v(sh,f"A{r}",name.replace("Forecast_",""))
        q=lambda field:f"'{name}'!C{totals[field]}:{end}{totals[field]}"
        f(sh,f"B{r}",f"=SUM({q('revenue')})")
        f(sh,f"C{r}",f"=SUM({q('ebitda')})")
        f(sh,f"D{r}",f"=MAX(0,Parameters!$B$13-MIN(Parameters!$B$12,MIN({q('ending_cash')})))")
        f(sh,f"E{r}",f"='{name}'!{end}{totals['cum_project_fcf']}")
        primary=data["revenues"][0]
        pr=23
        pref=col(min(n,12)+2)
        primary_idx=streams[primary['id']]
        cm=f"(Parameters!$C${pr}*'{name}'!$B$5*(1-Parameters!$E${pr}-Parameters!$B$4)-Parameters!$D${pr}*'{name}'!$B$6)"
        other_contrib="+".join(f"('{name}'!{pref}{v['contribution']}+'{name}'!{pref}{v['free_cost']})" for sid,v in streams.items() if sid!=primary['id']) or "0"
        freecost="+".join(f"'{name}'!{pref}{v['free_cost']}" for v in streams.values())
        costs="+".join(f"'{name}'!{pref}{totals[k]}" for k in ("fixed_cost","payroll","payroll_tax","marketing"))
        f(sh,f"F{r}",f"=IF({cm}<=0,\"N/A\",ROUNDUP(MAX(0,({costs}+{freecost}-({other_contrib}))/{cm}),0))")
        f(sh,f"G{r}",f"=IFERROR(MATCH(1,{q('payback_crossing_flag')},0),\"Not reached\")")
        f(sh,f"H{r}",f"=IFERROR(SUM({q('marketing')})/SUM({q('new_paid')}),\"N/A\")")
        if primary['kind']!='units':
            src_row=pr
            payret=f"MAX(0,MIN(1,Parameters!$F${src_row}+'{name}'!$B$8))"
            cm_no=f"(Parameters!$C${src_row}*'{name}'!$B$5*(1-Parameters!$E${src_row}-Parameters!$B$4)-Parameters!$D${src_row}*'{name}'!$B$6)"
            f(sh,f"I{r}",f"={cm_no}*IF({payret}=1,{n},(1-POWER({payret},{n}))/(1-{payret}))")
        else:
            v(sh,f"I{r}","N/A (one-time)")
        f(sh,f"J{r}",f"=MAX(ABS('{name}'!C{totals['balance_check']}),ABS('{name}'!{end}{totals['balance_check']}))")
    sh.get_range("A:A").format.column_width=27
    sh.get_range("B:J").format.column_width=19
    sh.get_range("A10:I10").merge(); v(sh,"A10","Source: editable Inputs & Parameters; taxes require official validation")
    sh.get_range("A11:I11").merge(); v(sh,"A11","Break-even is a local primary-stream EBITDA threshold at month min(12,horizon), other streams fixed")
    sh.get_range("A12:I12").merge(); v(sh,"A12","Sustained EBITDA, quarterly funding tranches, investor IRR and advanced tax handling are detailed in metrics.json")
    return sh


def sources_sheet(wb, data):
    sh=wb.worksheets.add("Evidence")
    sh.get_range("A1:F1").values=[["ID","Status","Claim","Source / URL","Date","Limitations"]]
    sh.get_range("A1:F1").format=HEADER
    rows=[]
    for e in data.get("evidence",[]):
        rows.append([str(e.get("id","")),str(e.get("status","")),str(e.get("claim","")),str(e.get("source","")),str(e.get("date","")),str(e.get("limitations",""))])
    tax=data["taxes"]
    rows.append(["tax", "verified" if tax.get("verified") else "BLOCKER",data["project"].get("tax_regime",""),tax.get("source",""),tax.get("effective_date",""),"Check authoritative current law"])
    if rows: sh.get_range(f"A2:F{len(rows)+1}").values=rows
    sh.get_range("A:A").format.column_width=24
    sh.get_range("B:B").format.column_width=15
    sh.get_range("C:C").format.column_width=38
    sh.get_range("D:D").format.column_width=54
    sh.get_range("E:F").format.column_width=24
    return sh


def export(data, output: Path):
    # Validate input and calculator early, before allocating workbook resources.
    checked = model(data)
    wb=Workbook.create()
    n=data["project"]["months"]
    _, ir, stream_rows = inputs_sheet(wb,data,n)
    _, meta = parameters_sheet(wb,data)
    specs=[]
    cases=data.get("scenarios") or [
        {"name":"base",**SCENARIO_DEFAULTS},
        {"name":"downside",**{**SCENARIO_DEFAULTS,"volume_multiplier":0.85}},
        {"name":"upside",**{**SCENARIO_DEFAULTS,"volume_multiplier":1.15}},
    ]
    if not any(x.get("name")=="base" for x in cases):
        cases=[{"name":"base",**SCENARIO_DEFAULTS},*cases]
    for case in cases:
        specs.append(forecast_sheet(wb,data,case,ir,stream_rows,meta))
    summary_sheet(wb,specs,data)
    sources_sheet(wb,data)
    output.parent.mkdir(parents=True,exist_ok=True)
    SpreadsheetFile.export_xlsx(wb).save(str(output))
    return output, checked


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    file, _=export(json.loads(args.input.read_text(encoding="utf-8")),args.out)
    print("Formula-driven Excel exported:",file)
    print("All scenario formulas are editable; verify in Excel/LibreOffice after changing assumptions. Historical accounting limitations in README.")


if __name__=="__main__": main()
