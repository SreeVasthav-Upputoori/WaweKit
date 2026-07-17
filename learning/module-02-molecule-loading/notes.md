# Module 2 — Molecule Loading · Build Notes

> How and why this module was built. Read alongside `graphical_abstract.html`.

---

## 1. What we built

The complete input pipeline: **SDF / MOL / SMILES files → background parsing →
sortable molecule table**, entered via *File → Open* or drag-and-drop, with a
progress bar, per-record error reporting, and a loaded-files list in the dock.

## 2. The three big ideas

### Idea 1 — Partial failure is normal (errors are data)

Real chemical files are dirty. The loader returns a `LoadReport` containing
**both** `records` (successes) and `errors` (failures with locations like
`"record 5"` / `"line 12"`). Nothing raises for a bad *record*; only a bad
*file* (missing, unsupported extension) raises. The GUI turns errors into a
summary dialog — the loader never knows the GUI exists.

**Why:** if a 10,000-molecule vendor SDF has 12 broken records, users need the
9,988 good ones *and* a list of the 12 bad ones. Exceptions can't express
"mostly succeeded"; a report object can.

### Idea 2 — Never block the GUI thread

Parsing runs inside `FunctionWorker` (a `QRunnable`) on `QThreadPool`. Results
return via **signals**, which Qt automatically queues onto the GUI thread's
event loop — that's why slots in `MainWindow` can touch widgets without locks.

Key implementation details you should understand:

- `QRunnable` is *not* a `QObject`, so it can't own signals. The standard idiom
  is a companion `WorkerSignals(QObject)` — memorize this pattern.
- `setAutoDelete(False)` + holding a Python reference (`self._active_worker`)
  prevents both premature garbage collection and the classic
  "Internal C++ object already deleted" crash.
- `inject_progress=True` passes `signals.progress.emit` as the loader's plain
  `progress` callback — the loader reports progress **without importing Qt**.
- Progress is throttled (every 100 records) so we don't flood the GUI event
  loop with thousands of queued signal deliveries.
- Why `QThreadPool`/`QRunnable` and not subclassing `QThread`? The pool reuses
  threads, scales to many tasks, and avoids manual thread lifetime management —
  it's the professional default for "run this function in the background."

### Idea 3 — Qt Model/View (data ≠ presentation)

`MoleculeTableModel` (a `QAbstractTableModel`) *adapts* our record list;
`QTableView` paints it; `QSortFilterProxyModel` re-orders rows in between.

- The view only asks for **visible** cells → smooth with 100k rows.
- `DisplayRole` returns text; `UserRole` returns raw values (`int` for heavy
  atoms) and the proxy sorts by `UserRole` — so 100 sorts after 20, not before.
- `beginInsertRows`/`endInsertRows` is a transactional protocol: views update
  incrementally instead of rebuilding.
- Selections live in *proxy* coordinates; `mapToSource` translates back —
  forget this and clicking row 1 after sorting returns the wrong molecule.

## 3. RDKit concepts introduced

| Concept | What you learned |
|---|---|
| `Chem.Mol` | The molecule object; wrapped, never passed around raw. |
| `SDMolSupplier` | Indexed SDF reader; supports `len()`; yields `None` for bad records. |
| **Sanitization** | RDKit's valence/aromaticity validation — the usual reason records fail. |
| `MolFromSmiles` / `MolFromMolFile` | Return `None` on failure (no exception!) — we translate `None` → `LoadError`. |
| `GetPropsAsDict()` / `_Name` | SDF data fields and the title line; preserved as `record.properties` / `record.name`. |
| Canonical SMILES | `MolToSmiles` gives one unique string per molecule; cached because views repaint constantly. |

## 4. File-by-file rationale

| File | Why |
|---|---|
| `models/molecule.py` | `MoleculeRecord` = Mol + identity + provenance. Pure Python/RDKit; lazy-cached `smiles`/`formula`. |
| `services/io/molecule_loader.py` | Format detection, per-format parsers, `LoadReport`. UI-free, progress via plain callback. |
| `services/workers.py` | Generic reusable background worker — the seam every heavy module (5, 6, 9, 11, 13…) will reuse. |
| `gui/widgets/molecule_table.py` | Model + proxy + view bundled behind a small API (`append_records`, `selected_records`). |
| `gui/main_window.py` | Open action, drag-drop, sequential load queue, progress bar, error dialog, sources dock. |

## 5. Layering rule refined

- `models` — pure Python + RDKit, **zero Qt**.
- `services` — may use **QtCore only** (signals/threads). Never QtWidgets.
- `gui` — the only layer that imports QtWidgets.

## 6. What the linters taught us (real fixes from this module)

Running `ruff` surfaced 24 issues that we fixed — this is what "professional
quality" means in practice:

- **D413/UP037/I001** — auto-fixed (`ruff --fix`): docstring section spacing,
  unnecessary quoted annotations, import sorting.
- **D401** — docstring first lines must be imperative ("Return the…", not
  "Returns the…"); reworded by hand.
- **D301** — a docstring containing `\W` Windows paths needs an `r"""` prefix.
- **D107** — we made a *policy decision*: `__init__` args are documented in the
  class docstring (numpy convention), so D107 went into the ignore list with a
  comment explaining why. Lint config is engineering, not bureaucracy.

## 7. Tradeoffs accepted

- **CSV-with-SMILES-column deferred** — needs a column-picker dialog; will
  arrive with a proper import wizard rather than a guessy heuristic.
- **No cancellation button** — deferred to Module 13 (batch processing).
- **Duplicates allowed** — loading a file twice appends again; dataset
  management/dedup belongs to standardization (Module 4).
- **Whole file loads into memory** — fine below ~1M molecules; out-of-core
  loading would be a Module 13+ concern.

## 8. Verification (actually run, not just claimed)

- `pytest`: **18/18 passing** — includes corrupt-SDF recovery, SMILES
  header-row hint, progress-callback contract, table model roles, and headless
  window construction (`QT_QPA_PLATFORM=offscreen`).
- `ruff check .`: clean. `black`: formatted.
- Environment: Python 3.13.2 venv, PySide6 6.11.1, pytest-qt 4.5.

## 9. Research lens

Loading itself is commodity engineering — no publishable novelty here, and we
should be honest about that. But note a gap worth remembering: most tools
*silently drop* unparseable records. Wawekit records **provenance of failure**
(`LoadError` with location). When we reach standardization (Module 4), a
systematic study of "what fraction of public datasets fail sanitization and
why, with an auto-repair taxonomy" is a genuine, citable contribution —
tools like this exist in fragments (e.g. ChEMBL curation pipelines) but a
reproducible, open benchmark of molecule-loading robustness does not.
