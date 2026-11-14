# Input/output data contract (v2)

## Core input (`examples/sample_b2b.json`)

`project`: name, country, currency, tax regime, start month, horizon (1–36 months).

`revenues[]`: independent streams of `units`, `subscription`, or `freemium` with unit price, variable cost, transactions, paid/free cohorts, retention, conversion and source IDs.

`operating`: monthly fixed costs, payroll, marketing, CAPEX, useful life, changes in net working capital.

`taxes`: **effective-dated** source, `verified` flag, applicable payroll/income/turnover/VAT rates and modeled payment lags. Do not infer a tax scheme from geography alone.

`financing`: opening cash, minimum reserve, equity, debt, dividends, investor contributions.

`valuation`: discount rate, pre-money, investor share, optional exit cash flows.

`scenarios[]`: base/downside/upside multipliers for prices, costs, volumes, retention and conversion.

`evidence[]`: IDs, claim, provenance and status (`verified`, `estimated`, `hypothesis`). Hypothetical inputs must not be reported as actual research.

`market`: audience units and levels PAM/TAM/SAM/SOM with `source_ids`, common sizing basis and chosen monetization scenario/period.

## Calculated outputs

- `metrics.json`: keyed scenario totals and investment metrics, including nullable values when not calculable.
- `monthly.json`: each month's financial waterfall including revenue, contribution, EBITDA, tax, cash, and balance reconciliation.
- `market.json`: normalized market audience and annual potential under the same monetization basis.
- `sources-and-assumptions.json`: assumptions/provenance and readiness blockers.
- `deck_manifest.json`: slide binding checks plus chart series mapping; `audit_deck.py` checks native PPTX series against `monthly.json`.

### Interpretation rules

- Market capacity ≠ forecast of acquired customers; SOM must be checked bottom-up with actual available channels/capacity.
- Revenue LTV ≠ contribution LTV; paid retention and cohort acquisition costs drive unit economics.
- EBITDA ≠ operating cash ≠ cumulative project FCF ≠ return to investor.
- Project payback dates are valid only **within the simulated horizon**; a missing result is not an infinite return estimate.
- Figures must have explicit currency, date range, units and source/hypothesis status.

### Design contract (from `examples/sample_deck.json`)

Top level `title`, `brand`, `theme`, `slides`.

`theme.preset` one of `editorial-blue`, `graphite-lime`, `warm-coral`; `font` default Inter; optional color overrides. Every layout uses theme tokens; no fixed startup colors are allowed.

Each slide has a `type`, `title`/`headline`, `section`, optional `note`, `sources` and `speaker_note`. Types: `cover`, `statement`, `split`, `steps`, `market`, `matrix`, `pricing`, `bullets`, `numbers`, `chart`, `economics`, `timeline`, `image`, `closing`.

A numeric card must use `metric` (metric key) or an explicit `source_id` if it contains a literal numeric value. Charts name a scenario and monthly field. Rendered native figures and series are checked against the structured outputs.
