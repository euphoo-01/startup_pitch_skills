# Architecture

Two skills are intentionally independent:

1. **business-analyst** — orchestrates research and decisions, normalizes assumptions, runs deterministic business-finance code, produces a QA'd metric source. Only loads the relevant reference for each stage.
2. **investor-slides** — translates an approved thesis and metric model into a 16:9 native-editable PowerPoint. Uses a configurable visual system, renders, audits and exports.

```
Business idea / evidence / market inputs
               ↓
   Project JSON + assumption sources
               ↓
       calculate.py + sizing.py
               ↓
        monthly.json, metrics.json, market.json
               ├─────────> export_excel.py ──> formula-driven XLSX
               ├─────────> analyst report / investment verdict
               └─────────> slide plan + generate_deck.cjs
                                          ↓
                                 PPTX, binding manifest
                                          ↓
                           audit_deck.py + full visual render
                                          ↓
                                   PPTX + preview PDF
```

### Standard / Deep

Standard uses primary sources and 3–5 direct competitors, scenario drivers, and one agreed business strategy with three scenarios. Deep expands only decisive evidence gaps, valuation, sensitivity or alternative business models. Both modes retain the same evidence requirements.

### Shared metric IDs

The presentation never recomputes financial values. Numeric cards refer to keys such as `results.base.revenue_total`; market cards read `market.levels.PAM.annual_revenue_potential`. A binding manifest records displayed text and the corresponding raw metric. A source change requires recalculation, deck generation and audit.

### Limits

This is a starter platform, not a universal statutory accountant. The calculator supports finite driver types; different industries need additional adapters for stock, deferred revenue, credit timing and tax jurisdiction. Business Analyst must flag unsupported material drivers and block an investor-ready verdict. See `LIMITATIONS.md`.
