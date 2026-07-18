# Module 15 — Settings · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`
> and the screenshot in this folder.

---

## 1. What we built

**Persistence.** Preferences now survive a restart: the **theme**, the **log
level**, and — via a "remember layout" toggle — the **window size, position and
dock arrangement**. A Settings dialog edits them, changes apply live, and they're
saved to disk. Close the app in light theme with the Structure panel docked left,
reopen it, and that's how it comes back.

## 2. The foundation was laid in Module 1

`AppConfig` — a frozen dataclass loading layered TOML (defaults → shipped →
user) — has existed since Module 1, which deliberately *only read* it. Module 15
adds the other half: **writing**. Everything the app configures already flowed
through this typed object; this module just makes edits stick.

## 3. Two storage backends, each for what it's good at

A deliberate split (the memory note from Module 1 anticipated it):

- **Human-readable prefs → TOML** (`<config_dir>/settings.toml`). Theme, log
  level, the remember flag — a user can open and edit the file by hand. Written
  by a **hand-rolled 12-line serializer**: the config is a flat table of str/int/
  bool, so a real TOML-writer dependency would be overkill. The whole config
  subsystem stays dependency-free (stdlib `tomllib` reads, our `_toml_value`
  writes). One subtlety pinned by a test: **`bool` is serialized before `int`**,
  because `bool` subclasses `int` and `True` must become `true`, not `1`.
- **Opaque window state → QSettings.** Geometry and dock layout are binary
  `QByteArray`s from `saveGeometry`/`saveState` — not something to hand-edit, and
  Qt's native `QSettings` (the Windows registry here) stores them cleanly.
  `restoreState` works because every dock and the toolbar already has an
  `objectName` (set since the modules that created them — foresight paying off).

## 4. When persistence happens (and why not on every change)

- **On close** (`closeEvent`): capture the *current* runtime theme and the window
  layout, then save. This is why toggling the theme with `Ctrl+T` survives a
  restart **without** writing to disk on every toggle — the transient runtime
  state is committed once, at exit.
- **On Settings-dialog OK**: save immediately, and apply live (theme via the
  `ThemeManager`, which emits `theme_changed` so every panel re-renders; log
  level via `setup_logging`).

Order matters at startup: the window resizes to the config's default size *first*,
then `_restore_window_state` overlays a saved geometry if one exists — so a first
run gets the sensible default and later runs get the remembered layout.

## 5. The dialog is a pure editor

`SettingsDialog` takes a config in and returns a new one out; it never applies or
saves. That keeps it headlessly testable and means the *window* owns the
policy (apply + persist). `config(base)` overlays only the exposed fields onto
`base`, so untouched settings (the fallback window size) are carried through, not
silently reset. A **Restore Defaults** button resets the controls to
`AppConfig()`.

## 6. Verification

- `pytest`: **263 tests** (was 255) — config save writes readable TOML,
  save→load round-trips, `bool` serializes as `true`/`false` (not `1`), unknown
  keys are ignored on load, defaults when no file; and the dialog (loads the
  config, edits flow into a new config carrying untouched fields, Restore
  Defaults). Clean under `ruff`, `black`, and `-W error::DeprecationWarning`.
- **End-to-end check**: a script saved an edited config, reloaded it, and
  confirmed theme + log level stuck — `round-trip OK: True`.

## 7. Research lens

Settings is pure application plumbing — no methodological novelty, and it would be
dishonest to invent some. Its only research-adjacent value is indirect: together
with Module 13's `BatchConfig` and Module 14's report, persisted, serialisable
configuration is a prerequisite for the **reproducible-analysis artifact** idea
those modules pointed at — a saved settings/pipeline file is part of "exactly how
this result was produced." No new opportunity here; the standing one
(standardization-divergence benchmark) is unaffected.
