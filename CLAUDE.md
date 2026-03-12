# Bin Label Maker - Project Guide

## 1. Project Mission

Help Brennan Industries employees produce customer-facing bin label sheets quickly, accurately, and with minimal friction. The output is a print-ready PDF formatted for standard Avery label stock.

**This app is** a focused job builder for customer bin labels, used daily by non-developer warehouse and sales staff, distributed as a single Windows .exe with no installer.

**This app is NOT** a generic label-design platform, a broad enterprise labeling suite, a project-management system, or a catalog browser with label output attached.

Every feature should serve the path from "I need labels for this customer" to "here is the PDF."

## 2. Definition of Good

- **Fast path to output.** Fewest reasonable steps from opening the app to a finished PDF.
- **Clear workflows.** Users always know where they are and what happens next.
- **Low ambiguity.** Every field, button, and action means one thing.
- **Low mistake rate.** The UI catches common errors before they reach the PDF.
- **Reliable persistence.** Save, load, and export do what users expect. No silent data loss.
- **Trustworthy preview.** What you see matches what will print.
- **Approachable.** A new employee can use it without training.
- **Focused scope.** Do fewer things well rather than many things poorly.

## 3. Dominant User Workflow

1. **Start a job.** Create new or reopen saved.
2. **Set job context.** Customer, sheet format, logo, description mode, cross-reference manufacturer, QR URL.
3. **Add parts.** Manual entry, spreadsheet import, or catalog search.
4. **Review and organize.** Edit, reorder, duplicate, remove, fill remaining slots.
5. **Preview.** Verify the sheet layout visually.
6. **Export.** Generate the print-ready PDF.
7. **Save.** Persist for later reopening or sharing.

Steps can be combined or streamlined, but the mental model must stay unified. Do not fragment it into competing workflows.

## 4. Core Product Principles

- Optimize for the common case. Power features must not slow the typical path.
- Actions should be visible and predictable. No important behavior buried or surprising.
- Users think in terms of "a label job with parts on sheets." Do not introduce competing abstractions unless they are clearly distinct.
- A smooth end-to-end flow matters more than a long feature list.
- Validate early. Warn about blank labels, missing data, or layout problems before PDF generation.
- The UI should look like a Brennan Industries tool. Use the brand theme consistently.

## 5. Architectural Principles

- **MVP with constructor DI.** Models hold data, views display and capture input, presenters mediate. All wiring in the composition root.
- **Presenters never import views.** They communicate through injected interfaces.
- **Business logic stays out of UI code.** Views are thin. Calculations, validation, data transformation, and workflow logic belong in presenters or services.
- **State has a clear owner.** The current job is owned by the presenter layer. Views reflect state; they do not independently store it.
- **Services are cohesive and testable.** Each does one thing (layout geometry, PDF rendering, API communication, file I/O, QR generation). Services must not depend on UI.
- **Layout engine is pure geometry.** Computes positions and dimensions. Renderers consume that geometry. This separation must be preserved.
- **Data source abstraction.** Catalog access goes through an abstract interface with live and mock implementations — enables testing and graceful fallback.
- **Theme is centralized.** Brand colors, stylesheets, and asset paths live in one module. Components consume the theme; they do not define their own brand styles.
- **Clarity over cleverness.** Simple readable code beats elegant abstractions that obscure intent.

## 6. State and Interaction Rules

- **Dirty tracking must be trustworthy.** User changes set dirty. Programmatic refreshes must not.
- **UI refreshes are not user edits.** Updating the UI to reflect state must not trigger change handlers.
- **Actions report outcomes.** Save, export, import, and search always tell the user what happened.
- **Workflows leave the UI consistent.** After any action, the label list, preview, and selection must all agree.
- **No hidden side effects.** A method that does X should not also quietly do Y.
- **Explicit state transitions.** Changes flow through the presenter, not through accidental signal chains.

## 7. Persistence and Portability

- **Perfect round-trips.** Every user-settable field must survive save-then-load identically.
- **Forward-compatible JSON.** New fields get defaults on load; unknown fields are tolerated.
- **Deliberate path handling.** Absolute paths break portability. The persistence layer manages path resolution for sharing between machines.
- **Safe filenames.** Sanitize user input used in filenames. No path traversal, no illegal characters.
- **No silent corruption.** Failed saves or loads must be reported. Partial writes must not leave files unreadable.
- **Self-contained .exe.** All assets bundled via PyInstaller. The app works from any directory without external dependencies.

## 8. Workflow Area Guidance

**Manual Editing** — Direct in-table editing with immediate preview feedback. Tab/Enter navigation should feel natural.

**Spreadsheet Import** — Handle common column-naming variations. Show what was imported. Report bad rows; do not silently drop them.

**Catalog Search** — Fast, forgiving search (partial matches, case-insensitive). Clear indication of which parts are being added. Graceful degradation when the API is unavailable. Cross-reference manufacturer selection controls which customer part number is pulled.

**Review and Cleanup** — Blank or incomplete labels should be easy to spot. Duplicate, remove, and reorder should be low-friction. Fill-sheet should be obvious in what it will do.

**Preview** — Must visually match the printed PDF. Simple page navigation. Selecting a label in the list highlights it in the preview.

**Export** — Validate before generating. Print-ready for the selected Avery sheet format. Page geometry (margins, gutters, label dimensions) must be exact.

**Save/Load** — Default to sensible filenames. Guard unsaved changes. Restore the complete job state.

**Sheet Usage** — Start-offset works correctly. Fill-sheet respects the offset. Preview shows which positions are used and which are skipped.

## 9. Validation and QA Expectations

- **Blank labels.** Warn before exporting sheets with empty labels.
- **Clipped content.** Long descriptions or part numbers must fit within label bounds. Truncation or scaling must be deliberate.
- **Import edge cases.** Missing columns, extra columns, empty rows, special characters, long values.
- **Layout math.** Label positions, page breaks, margins, and offsets must be exact for print. Pagination off-by-one errors are critical bugs.
- **Save/load roundtrip.** Every field and setting survives identically.
- **State consistency.** After any action sequence, the label list, preview, selection index, and dirty flag are all correct.
- **Path handling.** Developed cross-platform, deployed on Windows. Separators and case sensitivity matter.

## 10. Security and Configuration

- API tokens must not be committed to new files. The composition root is the single source for credentials.
- Secrets must not appear in logs.
- Graceful fallback when API is unreachable or credentials are invalid, with clear user feedback.
- Mock and live data flows are clearly separated.
- All user input used in file operations is sanitized.

## 11. Testing Priorities

1. Save/load roundtrip fidelity
2. Layout and pagination math (positions, page counts, offsets)
3. Import parsing (normal, edge-case, malformed)
4. Validation and preflight checks
5. Dirty tracking (user edits vs. programmatic updates)
6. Presenter logic against mock data source
7. Path handling and portability
8. PDF output geometry and content placement

## 12. Refactor Priorities

1. **Correctness** — wrong output, data loss, crashes
2. **Workflow clarity** — user confusion, unnecessary steps, misleading UI
3. **Reliability** — save/load, paths, edge cases
4. **Polish** — speed, visual refinement, interaction smoothness
5. **Code quality** — structure, duplication, clarity

Do not refactor for its own sake. Do not add complexity without workflow justification. Do not rewrite working code just to match a pattern. Prefer focused incremental improvement over architectural overhauls.

## 13. Decision Heuristics

- If a feature complicates the mental model, simplify or cut it.
- If two concepts overlap, unify them or distinguish them sharply.
- If a behavior is important, make it visible. Hidden magic is a liability.
- If an operation can fail silently, surface the result.
- If a feature helps rare cases but adds major complexity, be cautious.
- If a workflow is powerful but confusing, redesign the workflow before adding capability.
- If a refactor improves code but worsens usability, it is not a win.
- When unsure whether a change is needed, lean toward not making it.

## 14. Working Instructions for Claude Code

- Read and understand existing code before modifying it.
- Map affected code paths before invasive changes.
- Propose a plan for anything beyond a simple bug fix.
- The core flow (add parts, preview, export PDF) must always work. Do not break it in pursuit of improvements.
- Large changes should be broken into steps, each leaving the app working.
- Add or update tests for meaningful behavior changes.
- Do not over-engineer. Solve the problem at hand.
- Every change should make it easier, faster, or more reliable to produce correct bin label PDFs.
- The app ships as a PyInstaller .exe on Windows. Respect file path, bundled asset, and system dependency assumptions.

---

## Reference: Project Structure

```
main.py                            # Entry point
src/bootstrap.py                   # Composition root — all DI wiring and API config
src/models/                        # Data classes (template, label, Avery geometry)
src/presenters/                    # Workflow orchestration and state management
src/services/                      # Business logic (layout, rendering, API, I/O, QR)
src/views/                         # PySide6 UI (main window, panels, dialogs, theme)
assets/                            # Brennan logos and brand assets
bin_label_maker.spec               # PyInstaller packaging config
.github/workflows/build.yml        # CI/CD pipeline
```

## Reference: Catsy PIM Integration

- **API**: REST v4 at `api.catsy.com`, Bearer Token auth in composition root
- **Search**: Filter-based product search. Only `contains` and `is` operators work server-side; `starts_with` must be filtered client-side.
- **Rate limits**: 2 req/sec, burst 10, HTTP 429 with exponential backoff
- **Catalog**: 122k+ products
- **Fallback**: Mock data source when API is unreachable
- **Key fields**: `number` (Brennan P/N), `description` (full), `short_description` (compact), `series_description` (generic, not useful for labels), 18+ manufacturer cross-reference fields, product images from S3
- **Cross-references**: User selects manufacturer per job; that determines which customer P/N field is used

## Reference: Brennan Brand

- **Primary Blue**: `#006293`
- All styling centralized in the theme module
- Logos bundled in assets directory via PyInstaller
- New jobs default to the Brennan circle icon logo

## Reference: Build and Release

- **CI/CD**: GitHub Actions, triggered by `v*` tags
- **Output**: Single `BinLabelMaker.exe` attached to a GitHub Release
- **Stack**: Python 3.12, PySide6, ReportLab, qrcode, Pillow, requests, openpyxl, PyInstaller

```bash
git tag v1.x
git push --tags
```

## Reference: Code Conventions

- All dependency wiring in the composition root. Nowhere else.
- Presenters communicate with views through injected interfaces, never by importing view modules.
- Button variants: `setProperty("cssClass", "secondary")` or `"danger"`.
- Inline QSS scoping: `setObjectName()` with `#id` selectors to prevent style leaks.
- Never use `setFixedWidth()` on buttons — breaks at Windows DPI scaling.
- Brand theme centralized in the theme module. Components consume it; they do not define their own.
