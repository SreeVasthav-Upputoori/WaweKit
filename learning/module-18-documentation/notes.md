# Module 18 — Documentation · Build Notes

> Fast pass — a real, verified MkDocs site over the docs that already exist
> (`docs/index.md`, `docs/FEATURES.md`, and the new `docs/PACKAGING.md` from
> Module 17), not a from-scratch documentation-writing exercise.

## What we built

`mkdocs.yml` at the repo root: `readthedocs` theme (bundled with MkDocs — no
extra dependency), a three-page nav (Home / Features / Packaging), TOC +
tables + fenced-code markdown extensions.

## Verification (real, not just "the file parses")

```
mkdocs build --strict
```

`--strict` turns every warning (broken internal links, missing nav
references, bad anchors) into a build failure — the bar is "the site is
correct," not "the YAML is valid." First run surfaced one real problem:
`FEATURES.md`'s table of contents linked to
`#16-research-track--standardization-reproducibility-auditor` (double
hyphen, guessed from the heading's em dash) but MkDocs' actual generated
slug was `#16-research-track-standardization-reproducibility-auditor`
(single hyphen — the em dash is stripped, not substituted). Fixed the link;
`mkdocs build --strict` then exits 0 with zero warnings.

## Tradeoffs (stated honestly, given the fast pass)

- No auto-generated API reference (e.g. `mkdocstrings` pulling docstrings
  from `src/wawekit/`) — the existing hand-written `FEATURES.md` already
  covers every feature's mechanism and workflow in prose, which is more
  useful to a researcher-user than a raw API dump.
- Not deployed anywhere (no GitHub Pages workflow) — deploying is a release
  concern (Module 20: needs a decision on hosting), not a documentation
  *content* concern.
