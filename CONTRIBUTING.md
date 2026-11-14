# Contributing

- Keep `SKILL.md` concise. Load details from `references/` only when the corresponding stage is active.
- Add tests when changing formulas, scenario semantics, metric paths, or native PPTX generation.
- No unverified financial, legal or market data without an explicit hypothesis label.
- Never hardcode the visual identity of an example product into the slides engine.
- Run `npm install`, `python -m unittest discover -s tests -v`, and `python scripts/build_demo.py` before a pull request.
- New slide layouts must be native-editable and pass a manual render review, including Cyrillic, contrast and text wrapping.
