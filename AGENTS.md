# React Luau repository guidance

This file defines the durable working contract for coding agents in this repository.

## Ownership and intent

This is an independently maintained Paradoxum Games downstream fork of Roblox React
Luau. Facebook React and Roblox React Luau are references for behavior, history, and
useful changes; they do not determine this fork's product direction.

- Assume work is intended for this repository only. Do not optimize for or prepare an
  upstream pull request unless the user explicitly asks.
- Intentional downstream behavior is allowed when requested, tested, and documented.
  Accidental divergence is a bug.
- Do not add remotes, sync branches, rebase, cherry-pick, commit, push, open a pull
  request, publish, or release without explicit user authorization.

Read [`docs/maintainer-workflow.md`](docs/maintainer-workflow.md) before runtime,
porting, public-API, scheduler, reconciler, or renderer work.

## Repository map

- `modules/react`: public React API and Roblox-only additions.
- `modules/react-reconciler`: generic Fiber reconciler; high risk and performance
  sensitive.
- `modules/scheduler`: scheduling behavior and timing primitives.
- `modules/react-roblox`: Roblox renderer and Instance host-config boundary.
- `modules/shared`: shared types, flags, and utilities.
- `modules/roact-compat`: legacy Roact compatibility API.
- `WorkspaceStatic` and `modules/TestRunner`: Jest and test infrastructure.
- `docs`: user documentation and the canonical maintainer workflow.
- `bin`: test, CI, benchmark, and maintenance scripts.

## Classify before editing

Use one primary class and avoid mixing unrelated classes:

1. **Upstream semantic port**: adopt behavior from an exact React commit SHA or
   immutable tag; use its PR only as supporting context.
2. **Roblox platform behavior**: change Instance, host-config, scheduler, or engine
   integration behavior.
3. **Paradoxum downstream change**: behavior specifically owned by this fork.
4. **Performance change**: change a hot path without intentionally changing behavior.
5. **Tooling, docs, packaging, or release**: primarily workflow or distribution work;
   classify any runtime behavior portion separately.

If the intended compatibility is ambiguous, investigate first. Ask the user only when
different answers would materially change the result.

## Source and provenance

- Never port React behavior from memory or an unpinned `main`. Use an exact commit SHA
  or immutable tag, record it in the handoff, and use a PR only as rationale/context.
- The baseline is heterogeneous. A file's `-- ROBLOX upstream:` source is more
  authoritative than the repository's broad React 17 description.
- For an upstream port, compare old upstream, target upstream, and current Luau.
  Preserve intentional Roblox and Paradoxum behavior.
- Update a file-level upstream header only after comparing or aligning the whole file.
  For a selective hunk, keep the file baseline and cite the hunk's exact source nearby
  or in its regression test and handoff.
- Treat `js-to-lua` output as a draft. Preserve license headers, meaningful comments,
  types, test intent, and local behavior deliberately.
- Keep existing `ROBLOX deviation START/END` blocks unless their reason is removed.
- Mark a new fork-owned difference inside upstream-derived code with the
  converter-compatible form:

  ```lua
  -- ROBLOX deviation START: PARADOXUM: concise reason
  -- downstream implementation
  -- ROBLOX deviation END
  ```

- Do not mass-relabel historical deviations.
- Update `docs/deviations.md` and relevant API docs when public behavior intentionally
  differs from React or Roblox React Luau.

## Working rules

- Inspect `git status` before editing and preserve user changes.
- Keep changes behavior-focused. Avoid unrelated formatting, renaming, modernization,
  type cleanup, or comment churn.
- Only one agent may write to the working tree at a time. All subagents remain
  read-only unless writing ownership is explicitly transferred after the prior writer
  stops. Use parallel agents for source analysis, test discovery, risk analysis, and
  final review.
- Luau is not JavaScript. Check truthiness, `nil`, table holes and length, iteration
  order, equality, `.` versus `:`, errors, yields, and reentrancy explicitly.
- Flags and globals are often read at module load. Tests changing them must restore
  state and reset modules when required.
- Do not update snapshots without explicit user authorization; review every snapshot
  diff. Do not add skipped tests or a `FIXME`/`TODO` unless required and called out in
  the final report.

## Tests

- For an upstream bug fix or semantic port, port or adapt the relevant upstream
  regression test before implementation when practical.
- For a downstream change, add a regression test that fails for the intended reason
  before implementation when practical.
- Preserve meaningful upstream test names and assertion strength. Adapt platform setup
  deliberately; do not weaken a test merely to make a translation pass.
- Cover DEV warnings and release behavior when the changed code branches between them.

## Verification

Run commands from the repository root. During the transition, full runtime verification
still requires `rotrieve`, `roblox-cli`, `robloxdev-cli`, Selene, StyLua, and Bash.
Wally package verification additionally requires Python 3.11 or newer, Wally, and
Rojo.

The executable scripts under `bin` are the source of truth for command definitions.
Install workspace dependencies when `Packages` is missing or stale:

```sh
rotrieve install
```

Fast static gates (quick reference):

```sh
roblox-cli analyze --project tests.project.json
selene --config selene.toml modules/ WorkspaceStatic/
stylua -c modules bin WorkspaceStatic
```

Canonical full verification (executable source of truth):

```sh
bash bin/ci.sh
```

Canonical Wally archive and unpublished-consumer verification:

```sh
bash bin/ci-wally-packages.sh
```

The default `bin/testing.sh` path is a local DEV loop, not full CI parity.

- Scheduler, reconciler, deferred-signal, or lifecycle-ordering changes also require
  `bash bin/testing.sh --deferred` when available.
- Reconciler, scheduler, traversal, allocation, or render hot-path changes require
  `bash bin/ci-benchmarks.sh` as a smoke gate. A performance claim also requires
  baseline and candidate captures with `python bin/run-benchmarks.py --output <dir>`
  and a CSV comparison:

  ```bash
  python bin/compare-benchmarks.py <baseline.csv> <candidate.csv> --output <dir>
  ```
- Public API, project-map, package, or release changes require the full suite plus
  `bash bin/ci-wally-packages.sh` and any other affected manifest or consumer/build
  validation.
- Documentation or MkDocs navigation changes require local-link review,
  `git diff --check`, and `python -m mkdocs build --strict` when MkDocs is available.
- Run `bash bin/testing.sh --snapshot` only with explicit user authorization, then
  review every snapshot diff.

There is no dependable focused-test command in the current wrapper. Do not invent one
or claim it ran. If proprietary tools or engine access are unavailable, run the
available subset and report the rest as unverified.

## Review and handoff

Before finishing runtime work, perform a separate correctness review using the review
checklist in `docs/maintainer-workflow.md`. Confirm source links, deviation markers,
tests, DEV/release behavior, performance risk, and scope.

The final handoff must state:

- behavior changed and task class;
- exact upstream source, or `not upstream-derived`;
- deviations added, changed, preserved, or removed;
- tests and commands run with outcomes;
- checks not run and why;
- compatibility impact, remaining risk, and follow-up work.

Never describe work as fully verified when a required gate could not run.

## Approved Rokit and Wally migration

The approved target is a Rokit-managed, Wally-published monorepo:

- Keep the source in this repository. The nine Wally packages remain directories here;
  they are packages, not separate repositories.
- Publish them under the Paradoxum scope as `paradoxum/react`,
  `paradoxum/react-globals`, `paradoxum/react-is`,
  `paradoxum/react-reconciler`, `paradoxum/react-roblox`,
  `paradoxum/react-test-renderer`, `paradoxum/roact-compat`,
  `paradoxum/react-scheduler`, and `paradoxum/react-shared`.
- Use `https://github.com/paradoxum-games/wally-index` as the package registry.
- Keep the remaining modules as local development or test modules unless the user
  explicitly approves publishing another package.
- Use `rokit.toml` for repository tool pins. Adopt Rokit at the existing tool
  versions first; evaluate tool upgrades as separate changes with their own diffs and
  verification.
- Rokit 1.2 discovers and combines `rokit.toml` with legacy `foreman.toml` files. While
  the Foreman manifest remains, its private Rotriever and `rbx-aged-cli` sources mean
  plain `rokit install` is not a clean bootstrap. Do not claim otherwise or remove the
  legacy manifest before Wally test-workspace parity.

Treat the repository as transitional until the Wally workspace passes parity:

- The current Foreman and Rotriever manifests, generated `Packages` layout,
  `Packages.Dev` aliases, `_Workspace` layout, and executable `bin` commands remain
  authoritative. Do not remove them or switch CI merely because replacement manifests
  exist.
- Wally does not reproduce the current Rotriever workspace automatically. Build a
  deterministic Rojo/project-map compatibility layout that keeps local source under
  test and preserves existing package and dev aliases. Prefer that over mass-rewriting
  runtime imports.
- The Paradoxum registry or its configured fallback registries must resolve the exact
  runtime and development dependency graph. Verify actual resolution; do not infer it
  from an old lockfile or registry search.
- The package family intentionally pins `roblox/promise@3.5.2`. It pins
  `jsdotlua/luau-polyfill@1.2.7` because the fallback registry's historical
  `roblox/luau-polyfill@1.2.5` dependency chain is incomplete. Do not switch package
  lineages without regenerating and reviewing the consumer lock and artifacts.
- Do not mirror, publish, or seed registry packages without explicit user
  authorization.
- Keep all nine package manifests `private = true` and every Multipack destination
  disabled during staging. An authorized release must unlock publication in a
  dedicated, reviewed change only after all release gates pass.
- The unpublished consumer's Rojo build validates structure but does not execute
  `tests/wally-consumer/smoke.server.lua`. Before unlocking publication or completing
  the cutover, run that smoke in an engine-backed environment and record its singleton
  identity and version assertions as passing.
- Establish one repository release version before publishing. Pin internal React
  package dependencies to that exact lockstep version so a staged publish cannot
  resolve a mixed release.
- Publish in dependency order: ReactGlobals; Shared; React, Scheduler, and ReactIs;
  ReactReconciler; ReactRoblox and ReactTestRenderer; then RoactCompat.
- Every package archive must exclude tests, snapshots, Rotriever manifests, and
  development-only files, and must include its runtime source, project mapping,
  README, and MIT license. Run `bash bin/ci-wally-packages.sh` to review the actual ZIP
  contents for every member.
- Commit and review every Wally lockfile. The current unpublished-consumer fixture
  must resolve cleanly and match its committed lock. Before the final cutover, also
  validate the source-based test workspace and its development lock; after an
  authorized publish, validate the private-registry example consumer.
- Only after static analysis, DEV, release, deferred, and benchmark parity may the
  active scripts and documentation switch to Wally and the old Foreman, Rotriever,
  and legacy Multipack publication paths be removed.
- Audit first-party consumers, including `paradoxum/react-flow`, before cutover.
  Ensure they resolve one React package family; duplicate React copies can break
  singleton state and shared internals.
- Ledger is a useful convention reference, not a template to copy blindly. Regenerate
  locks after manifest identity or registry changes and verify actual package contents.

Until that cutover is complete, use the current Rotriever commands in the Verification
section above and report the migration as partial rather than complete.
