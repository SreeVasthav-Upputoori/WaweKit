# Module 1 — Project Architecture · Build Notes

> These notes explain **how and why** Module 1 was built, so you can maintain
> and extend the project yourself. Read alongside `graphical_abstract.html`.

---

## 1. What we built and why

We built the **walking skeleton**: a fully launchable desktop application that
does nothing chemically yet, but establishes the structure every later module
plugs into. This is standard professional practice — get an end-to-end runnable
app first, then grow features into a codebase that already works.

Concretely, Module 1 delivers:

- A layered, `src`-layout Python package `wawekit`.
- Cross-cutting infrastructure: **constants, paths, config, logging**.
- A themed desktop shell: **MainWindow** (menus, toolbar, status bar, dock) with
  runtime **dark/light** switching.
- A **composition root** (`app.run`) and `python -m wawekit` entry point.
- Packaging, tests, docs, and full open-source governance files.

## 2. The layered architecture (the single most important idea)

```
gui  ->  services  ->  models  ->  core
```

**Dependencies point downward only.** `gui` may import `services`, `models`,
`core`; but `core`/`models`/`services` must **never** import `gui`.

Why this matters:

- **Testable** — science in `models`/`services` runs with no display.
- **Maintainable** — swap or restyle the UI without touching chemistry.
- **Paper-ready** — algorithms live independent of the GUI, so they can be
  benchmarked and reused (CLI, notebooks) for publications.

If you remember one rule from this project, remember this one.

## 3. File-by-file rationale

| File | Why it exists / key idea |
|------|--------------------------|
| `src/wawekit/__init__.py` | Single source of `__version__`. |
| `__main__.py` | `python -m wawekit`; forwards to the composition root. |
| `app.py` | **Composition root** — the one place assembly + event loop live. |
| `core/constants.py` | App identity as pure data (rename = one edit). |
| `core/paths.py` | `QStandardPaths` → correct config/data/log dirs per OS. |
| `core/config.py` | Frozen `AppConfig` dataclass; layered TOML load; never crashes on bad files. |
| `core/logging_config.py` | Console + rotating file logging; idempotent for tests. |
| `gui/main_window.py` | The shell; shared `QAction`s; DI of config + theme manager. |
| `gui/themes/theme_manager.py` | Loads `.qss` via `importlib.resources`; toggles theme. |
| `gui/themes/{dark,light}.qss` | "CSS for Qt"; kept structurally parallel. |
| `tests/conftest.py` | Forces `QT_QPA_PLATFORM=offscreen` for headless GUI tests. |
| `tests/test_smoke.py` | Proves the skeleton constructs. |
| `pyproject.toml` | Build + deps + black/ruff/pytest config in one file. |

## 4. Concepts you learned here

### Software engineering
- **Walking skeleton / tracer bullet** — runnable end-to-end before features.
- **Composition root** — assemble the object graph in exactly one place.
- **Dependency injection** — pass collaborators in; never reach for globals.
- **`src`-layout** — tests run against the *installed* package, like users get.
- **Frozen dataclass** for immutable, typed, discoverable configuration.
- **Fail-safe startup** — a bad config file or theme name logs a warning and the
  app still launches with defaults.

### Qt (PySide6)
- `QApplication` identity (`setApplicationName`/`setOrganizationName`) drives
  `QStandardPaths`, so set it *before* touching paths.
- `QMainWindow` gives you menu bar / toolbar / status bar / dock areas for free.
- **Shared `QAction`s** let one command back both a menu item and a toolbar
  button, and enable/disable them together.
- **QSS** (Qt Style Sheets) restyles the whole app from one string.
- `importlib.resources` loads packaged assets in both source and frozen builds.

### RDKit
- None yet — deliberately. RDKit enters in Module 2, and it will live in
  `models`/`services`, never in `gui`.

## 5. Tradeoffs we accepted

- **Deferred settings *writing*** to Module 15 — Module 1 only *reads* config.
- **Text-only toolbar** (no icons yet) — icons arrive with the resources module.
- **hatchling** build backend — simple and standards-based; could swap later.
- **QSS over a full design system** — pragmatic; good enough and native-looking.

## 6. Future scalability hooks already in place

- Empty `services/`, `models/`, `plugins/`, `resources/` packages so import
  paths are stable from day one.
- A left **dock** ready to host the project/data panel (Module 2).
- A placeholder central widget ready to be replaced by the real workspace.
- Idempotent logging + layered config that later modules simply reuse.

## 7. How to run and verify

```bash
pip install -e ".[dev]"
wawekit            # launches the themed shell
pytest             # smoke tests pass (offscreen)
ruff check . && black --check .
```

## 8. Research lens (starting the habit early)

Module 1 has no algorithmic novelty — it is scaffolding. But we set up the
conditions for publishable work later: because the science lives in
GUI-independent `models`/`services`, any novel method we build (e.g. a new
scaffold-analysis or chemical-space algorithm) can be benchmarked headlessly
against reference datasets and reported reproducibly. We will flag concrete
publication opportunities from Module 5 onward.
