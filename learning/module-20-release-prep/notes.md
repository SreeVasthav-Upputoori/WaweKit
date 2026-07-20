# Module 20 — Release Preparation · Build Notes

> Fast pass — this module is a checklist, not a build. What was actually done
> vs. flagged as needing the user's own input is stated plainly below.

## What we did

- `RELEASE_NOTES.md` — a user-facing summary of the 0.1.0 release: highlights
  (full workflow, the reproducibility research flagship, plugins, packaging,
  docs, CI), the complete 20-module list, and an honest **Known limitations**
  section (no code signing/installer, no plugin sandboxing, the benchmark is
  illustrative-scale, no auto-update).
- `CHANGELOG.md` — converted from one long-running `[Unreleased]` block
  (accumulated across the entire build) into a dated `[0.1.0] - 2026-07-18`
  entry, per Keep a Changelog convention, with a fresh empty `[Unreleased]`
  above it for future work.
- `README.md` — fixed a **stale status line** that still described only
  Modules 1–8 (left over from early in the project) to reflect the actual
  current state: all 20 modules plus the research track. Roadmap checklist
  now shows all 20 items checked, with a link to `RELEASE_NOTES.md`.
- Verified `LICENSE` (MIT, real name), `CONTRIBUTING.md`, and
  `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1) are all already in order —
  no placeholder text, generic-but-correct enforcement contact language.

## Flagged, not silently guessed — since resolved

`pyproject.toml`'s `[project.urls]` (`Homepage`/`Repository`) and
`mkdocs.yml`'s `repo_url` originally pointed at a `github.com/your-org/wawekit`
placeholder. Fixing it needed the actual GitHub account the project would be
published under — the author's decision, not something to invent — so it was
left as a placeholder and called out here rather than filled with a guess.

**Resolved:** all three now point at the real repository,
`https://github.com/SreeVasthav-Upputoori/WaweKit`, matching the `PROJECT_URL`
already set in `core/constants.py`.

## Tradeoffs (stated honestly)

- No git tag or GitHub Release was created — that's a repository-level
  action (and this whole project is still uncommitted; see the standing
  recommendation to commit first).
- No PyPI publishing config/workflow — `pyproject.toml` is publish-ready
  (name, version, classifiers, entry points all present) but no `twine`/
  trusted-publishing CI step exists yet; deferred until the org/URL
  placeholder above is resolved and a real release cadence is decided.
