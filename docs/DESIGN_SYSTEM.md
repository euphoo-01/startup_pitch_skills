# Investor Slides — visual system

The output is an editorial investor presentation, not a themed dashboard. It **must not** inherit styles from examples or previous clients.

## Built-in palettes

| Preset | Paper | Ink | Accent | Character |
|---|---|---|---|---|
| `editorial-blue` | warm off-white | deep graphite | cobalt | modern, confident, investor-safe |
| `graphite-lime` | off-white | graphite | muted lime | energetic technology |
| `warm-coral` | warm ivory | umber-black | terracotta | warm, product-led |

Change `theme.preset` and rerun; business data is independent. Pass company colors if brand assets exist. Presets are merely fallbacks and never constitute a locked identity.

## Layout vocabulary

- **Cover / closing:** dark base, oversized typography, one vivid vertical block.
- **Statement:** large core thesis, smaller supporting evidence, significant whitespace.
- **Split:** opposing ideas, one high-contrast panel.
- **Steps / timeline:** numbered or sequential native shapes.
- **Market:** four compared PAM/TAM/SAM/SOM blocks with population and annual revenue, consistent formula.
- **Matrix:** competitor/use-case comparisons in native text/table cells.
- **Pricing:** offer and business logic in two panels.
- **Unit economics:** one dominant LTV/CAC ratio with CAC, contribution LTV, Gross Margin, Contribution Margin and retention; automatically inserted for a single subscription stream.
- **Economics / numbers:** a few legible large metrics, not a cluttered finance dashboard.
- **Chart:** native PowerPoint chart and visible units/period/forecast label.

## QA

1. Render real PPTX to PDF/PNG; use a montage and inspect any failing slides full-size.
2. Check clipping, wrapping, font fallback, contrast, source text, spacing and optical alignment.
3. Run metric audit with `--monthly`; compare all key claims to source JSON.
4. Avoid long slide-by-slide design explanations; produce concise issue list and targeted fixes.

Unslop and OpenDesign Critique are **inspirations** for a short original visual checklist. Their tools and instruction files are not copied, installed or loaded here.
