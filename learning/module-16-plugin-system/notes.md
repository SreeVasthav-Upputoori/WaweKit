# Module 16 — Plugin System · Build Notes

> Built in a fast, low-ceremony pass (per user request to "complete the rest
> quickly" after the research track) — real code, real tests, a real installed
> example plugin, but no separate graphical-abstract HTML for this module.

## What we built

A plugin architecture using **Python entry points** — the same mechanism `pip`
itself uses to register console commands — so installing a third-party package
is the entire registration step; nothing inside Wawekit needs editing.

- `plugins/base.py` — `WawekitPlugin`, a `runtime_checkable` `Protocol` (not a
  base class): a plugin needs `name`, `version`, and `activate(context)`. Using
  a Protocol means a plugin author's only dependency on Wawekit is matching this
  tiny shape, not importing the whole application.
- `plugins/base.py` — `PluginContext`: the **narrow, safe** surface a plugin can
  extend through — `add_menu_action` and `add_dock`, nothing else. A plugin
  cannot reach the window, the models, or other plugins directly.
- `plugins/manager.py` — `discover_plugins()` (resolve entry points in the
  `wawekit.plugins` group) and `load_plugins(context)` (instantiate + activate
  each). Both apply the same resilience rule used by every chemistry service in
  this app: **one bad plugin (bad import, bad constructor, bad `activate()`)
  is logged and skipped, never allowed to crash the whole application** — the
  data-loss discipline from "one bad molecule must not abort the run," applied
  to untrusted third-party code instead of untrusted third-party structures.
- `MainWindow._load_plugins()` wires it in: a **Plugins** menu is created empty
  at startup, then `load_plugins` populates it via the context's callbacks.

## Verification (real, not just mocked)

Unit tests (6) mock `entry_points` to prove discovery/loading/isolation logic in
isolation — including a plugin missing the protocol shape, and one that raises
during `activate()`, both correctly isolated without affecting a co-installed
good plugin.

Beyond that, a **real reference plugin** was built and installed:
`examples/example-plugin/` is a genuine installable Python package
(`pip install -e examples/example-plugin`) declaring
`[project.entry-points."wawekit.plugins"] example = "example_plugin:ExamplePlugin"`.
After installing it into the project's venv:

```
Discovered: [('example', <class 'example_plugin.ExamplePlugin'>)]
Loaded: [('Example Plugin', '0.1.0')]
Menu actions added: ['Say Hello']
Failures: []
```

This is genuine `importlib.metadata` entry-point discovery of a real installed
package, not a simulated test double — end-to-end proof the mechanism works
exactly as a third-party plugin author would experience it.

## Tradeoffs (stated honestly, given the fast pass)

- No plugin *un*loading, sandboxing, or permission system — a plugin runs with
  full application privilege once activated. Acceptable for a v1; a security
  boundary would be a substantial separate feature.
- The extension surface (`add_menu_action`, `add_dock`) is intentionally
  minimal. Widening it (e.g. letting a plugin register a new Chemistry
  operation) is a natural v2 addition once real plugin authors ask for it.
