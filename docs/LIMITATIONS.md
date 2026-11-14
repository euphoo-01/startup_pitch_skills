# Known limitations and safe use

The project consists of **a working driver-based calculation engine and agent instructions**, not an autonomous universal research system. Web research is performed by whichever agent has the skill, with whatever browser/search capabilities it actually possesses.

## Finance

- Supports units sold, subscriptions, freemium conversions, one currency, three scenario multipliers and manual working-capital changes.
- Monthly cash collected in the period of sale; no receivable aging, deferred revenue, inventory costing, customer refunds, detailed loan schedules or consolidation.
- Simple straight-line depreciation and selected tax-rate treatments; not a substitute for national tax code, statutory filings or audited GAAP/IFRS accounts.
- `verified=false` taxes are a blocking warning for investment-ready conclusions.
- Cash flow, balance and IRR are simplified. A complex legal entity or funding structure needs a model adapter and accounting review.

## Research

- PAM/TAM/SAM/SOM are only as credible as sources, segmentation, monetization and bottom-up attainability checks.
- A synthetic example must never be presented as validated traction, competitor fact or empirical survey.

## Slides

- The bundled generator is intended for 8–16 clean editorial slides; it is not a full design editor.
- Native charts, texts and shapes are editable, but externally supplied photos/screenshots are embedded images.
- `audit_deck.py` checks model-number bindings, chart series and native slide bounds. It does not replace human visual inspection of rendered slides.
- PDF preview requires an external converter. Fonts may differ on other machines; install a compatible face such as Inter if necessary.
