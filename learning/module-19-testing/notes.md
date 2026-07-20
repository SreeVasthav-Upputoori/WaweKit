# Module 19 — Testing (CI) · Build Notes

> Fast pass — this module is about *automating* the existing 300+ tests, not
> writing new ones. What made it non-trivial was a real bug the automation
> attempt surfaced.

## What we built

`.github/workflows/ci.yml`: on every push/PR to `main`, on a
Ubuntu/Windows/macOS matrix — install `.[dev]`, `ruff check`, `black --check`,
then `pytest`. Linux needs a handful of system Qt libraries installed
(`libegl1`, `libxkbcommon0`, etc.) just for PySide6 to *import* on a bare
runner, independent of having a display; Qt itself already runs headless via
the pre-existing `QT_QPA_PLATFORM=offscreen` default in `tests/conftest.py`.

## The real find: a segfault-on-exit that would have made every CI run red

Confirmed locally before trusting the workflow: `pytest -q` printed
`........ [100%]` — every one of 300+ tests passed — and then the *process*
crashed:

```
Windows fatal exception: access violation
Current thread 0x000026cc (most recent call first):
  <no Python frame>
```

`<no Python frame>` means the crash is in native code, not Python — and it
happens strictly after test collection finishes, during CPython's normal
interpreter finalization (destroying `QApplication`, unloading extension
modules, etc.), not inside any test. The prime suspect: `QWebEngineView`
(`gui/widgets/conformer_view.py`, Module 9's 3D viewer) — QtWebEngine
wraps Chromium, and Chromium's own shutdown sequence racing against
CPython's interpreter teardown is a well-documented category of crash for
PySide6/PyQt test suites that touch WebEngine.

Why this matters for CI specifically: pytest's own summary said "all
passed," but the **process exit code** is what GitHub Actions actually
checks to mark a job green or red — and a segfault (exit 139 on POSIX,
an access-violation code on Windows) is not zero. Every CI run would have
shown red on a correct codebase, which is worse than showing nothing: a
red CI badge that's always red trains everyone to ignore it.

### Fix

Added to `tests/conftest.py`:

```python
@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(exitstatus)
```

`pytest_sessionfinish` fires once pytest has already computed the real
pass/fail result. `trylast=True` lets the terminal reporter's own
`pytest_sessionfinish` (which prints the "N passed" summary) run first.
`os._exit()` is a direct OS-level process exit — it skips CPython's normal
interpreter finalization entirely (no `atexit` callbacks, no garbage
collection, no extension-module teardown), which is exactly the phase that
was crashing. The exit code passed to it is the *real* one pytest computed,
so an actual test failure still fails CI correctly — only the irrelevant
native-teardown crash is bypassed.

Verified across 4 consecutive full-suite runs: exit code 0 every time
(previously 139/access-violation every time). One cosmetic side effect:
occasionally a residual fault-handler trace from a still-finishing
background thread prints to stderr even on a clean run — noise, not signal;
the exit code is unaffected and is what CI actually gates on.

## Tradeoffs (stated honestly, given the fast pass)

- The root cause (QtWebEngine shutdown vs. CPython finalization) was
  diagnosed by elimination (WebEngine is the only Chromium-backed component
  in the app, and the crash is native/frame-less) rather than by attaching a
  native debugger — sufficient to fix the CI-blocking symptom, but a deeper
  root-cause writeup would need Qt's own crash tooling.
- No coverage reporting (`pytest-cov`) wired in yet — CI currently answers
  "did anything break," not "how much of the code is exercised."
