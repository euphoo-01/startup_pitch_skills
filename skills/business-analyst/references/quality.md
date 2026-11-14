# QA / release gates

## Evidence gate
- Every decision-critical observation has verifiable source, observation date, period/population and confidence. Label claims as verified/estimated/hypothesis; no fabricated N or rates.
- Public data across years or geographies normalized; report uncertainty. Taxes have country, regime, effective date and official citation.

## Market gate
- PAM >= TAM >= SAM >= SOM when units are comparable; footnote non-nested opportunity definitions. Count distinct customers vs peak MAU consistently. Revenue assumptions (price, seasonality, conversion) coherent across levels. Bottom-up SOM passes channels/capacity test.

## Model gate
- Inputs in real currency, periods aligned, rates [0,1], units nonnegative, stream IDs unique. Check all subtotal identities and month-to-month cash reconciliation. No invented EBITDA-based funding calculation. Balance sheet only if assets/liabilities are fully modeled.
- Run deterministic test and scenario monotonicity checks with no misleading guaranteed outcomes. Test zero sales, negative contribution, missing payback, tax timing, churn extremes and +/-10%, +/-15% shocks.
- Unit LTV contribution vs CAC same cohort/denominator; track free acquisition and seasonal paid retention. Record investor returns distinctly from project payback.

## Artifact gate
- Excel formulas reference editable assumptions and output reasoned numbers, not just static Python values. Model-to-workbook parity must be checked within a declared rounding tolerance. Slides show metric IDs, units, scenarios, dates and source notes; editable shapes/charts preferred.
- No investor deck if material missing taxation, revenue recognition or invalid primary assumptions goes unflagged. Prefer a transparent blocker to false precision.
