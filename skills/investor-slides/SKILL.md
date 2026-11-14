---
name: investor-slides
description: Create and audit native-editable, brand-neutral PowerPoint investor decks from verified metrics. Use for business pitches, market sizing, investment forecasts, or slide QA; do not calculate financial inputs inside the presentation.
---

# Investor Slides · editable PowerPoint

**Goal:** an editorial-quality PPTX, not a repeated-card template. Start with brand identity supplied by the user; otherwise use the neutral `editorial-blue` preset. NEVER inherit an example project's colors, name, screenshots, typography or product claims.

1. Input: approved narrative, `metrics.json`, `monthly.json`, `market.json`, sources, and slide plan. Every numeric claim must come from a metric binding or a clearly attributed source. Market levels must share a compatible audience and monetization basis. The main deck must explicitly display applicable CAC, margin-adjusted LTV, **LTV/CAC (not the reciprocal)**, Gross Margin, Contribution Margin, and retention. A single subscription stream gets an automatic KPI slide; for multiple streams select the cohort, and never blend mismatched LTV/CAC.
2. Read `references/design.md` only while composing. Make 8–12 main slides with distinct, content-matched layouts; appendix only when useful. Keep slides readable from a distance. Never fabricate traction or competitor advantages.
3. Generate **native PPTX** using Node + PptxGenJS. The built-in renderer accepts `cover, statement, split, steps, market, matrix, pricing, bullets, numbers, unit-economics, chart, economics, timeline, image, closing` (see `examples/sample_deck.json`). Use a bespoke PptxGenJS layout if a story cannot be represented well; do not force everything into cards.
4. Command: `node scripts/generate_deck.cjs PLAN.json --metrics METRICS.json --monthly MONTHLY.json --market MARKET.json --out deck.pptx --manifest manifest.json`. Theme `preset` options: `editorial-blue` (default), `graphite-lime`, `warm-coral`; optional explicit palette overrides. A theme is NOT a product brand.
5. Audit: `python scripts/audit_deck.py deck.pptx --metrics METRICS.json --manifest manifest.json --monthly MONTHLY.json --market MARKET.json`; render *all* slides and review a montage. Read `references/visual-qa.md` only at QA time. Fix overflow, truncation, density, missing labels and inconsistent KPI figures; inspect failing slides at full size. Repeat audit after fixes.
6. Deliver a PPTX plus PDF preview when a PDF converter is available. Text, shapes, market blocks, tables and charts must remain editable; only legitimate photographs/screenshots stay raster. Mention any content/presentation limitations.

**Token economy:** do not load full external visual-audit repositories by default; no repeated web searches for decoration. One planning pass, one full visual pass, targeted re-render only. Keep source of truth in calculated JSON, not in slides.
