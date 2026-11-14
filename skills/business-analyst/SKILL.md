---
name: business-analyst
description: Analyze and validate any business idea, market, competitors, revenue strategy, unit economics, taxes, financial forecasts and investment terms; produce evidence-backed investor analysis and editable Excel. Trigger for business feasibility, investment readiness, PAM/TAM/SAM/SOM, CAC/LTV, break-even, payback or funding plans. Do not trigger for purely visual slide design.
---

# Business Analyst — Standard / Deep

**Language:** match the user. **Maximum forecast:** 36 monthly periods; shorter if justified. **Default:** Standard. **Deep:** only when requested or when a material ambiguity prevents a defensible decision. Optimize tool and token use without sacrificing evidence quality.

1. **Intake:** identify country, legal/tax form, customer vs payer, problem, business type, pricing, funding, stage, available evidence. Ask only material missing questions, in one concise batch. Record decisions and hypothesis IDs in `assumptions.json`.
2. **Research:** verify demand, primary sources, closest 3–5 competitors, market and observable price signals. Read `references/research.md` only at this stage. Evidence ranks: observed/verified, derived estimate, hypothesis. Counterevidence is mandatory. No invented interviews, adoption rates, source URLs or competitor claims.
3. **Market:** read `references/market.md`; compute PAM/TAM/SAM/SOM both as customers and annual revenue; document funnel and bottlenecks. If comparable market levels exist in input, run `scripts/sizing.py` to normalize all four using a single monetization basis. Distinguish theoretical market potential from company year-N forecast.
4. **Strategy gate:** compare up to 3 monetization/operating alternatives at high level. Confirm the preferred option and critical assumptions with user before full modeling.
5. **Financials:** read `references/unit-economics.md` and `references/financials.md`. Run `scripts/calculate.py` on a schema-valid JSON input. Use explicit country-specific tax rates, dates and regime. Do not certify financial outputs if material taxation/recognition rules are unknown. Simulate base, downside, upside; compute monthly EBITDA, taxes, cash, break-even units, paybacks, funding gaps and investment terms. Use code, not mental arithmetic.
6. **Investment:** read `references/investment.md` for valuation, investor return, tranches and GO / VALIDATE / PIVOT / NO-GO. Separate EBITDA-positive, sustainable break-even, project FCF recovery and investor payout.
7. **QA gate:** read `references/quality.md`; run validator. Check dimensions, periods, source traceability, tax provenance, cash reconciliation, balance limitations, sensitivities and no guaranteed forecast claims. Fix blockers before investing claims.
8. **Deliver:** evidence register, analytical report, formula-driven editable Excel, then hand off `monthly.json` + `metrics.json` to `investor-slides` if a deck is requested. Derive *all* slide figures from outputs; never retype or recalculate in presentation. Get user approval before publishing final investment recommendation.

**Execution:** `python scripts/calculate.py INPUT.json --out OUTPUT_DIR`; `python scripts/validate.py INPUT.json --results OUTPUT_DIR/metrics.json` (add `--strict` for investment-ready gating); `python scripts/export_excel.py INPUT.json --out OUTPUT.xlsx` (requires artifact_tool). Read schemas only when editing JSON shape. Code is a v1 driver model; do not claim specialized tax, inventory, deferred-revenue or consolidated accounting it does not implement.

**Token policy:** no exhaustive search by default; cache sources/assumptions; invoke one reference per relevant stage; no full narrative repetition; request further source checks only for material uncertainty. Deep extends weak evidence or valuation/sensitivity, not every section indiscriminately.
