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

Run commands from the repository root. The reproducible migration gates use Python
3.11 or newer, Rokit 1.2.0, Wally, Rojo, Selene, StyLua, and Bash. The legacy
full-runtime scripts still invoke Roblox-internal `rotrieve`, `roblox-cli`, and
`robloxdev-cli`; the public Rokit manifest does not install them and their declared
sources are unavailable externally. Retain those commands as historical parity
targets, but do not add new dependencies on them.

Install the public Rokit toolchain while avoiding this repository's legacy Foreman
manifest:

```sh
bash bin/bootstrap-tools.sh
```

This bootstrap verifies Rokit 1.2.0 and provisions the public tools declared in
`rokit.toml`. It does not make the Roblox-internal commands available. Rocale 0.1.2
drives the protected Wally consumer smoke in
`.github/workflows/roblox-runtime.yml`; it is not the full source Jest runner.
That workflow requires `ROCALE_API_KEY` as an environment secret and
`ROCALE_PLACE_ID` plus `ROCALE_UNIVERSE_ID` as environment variables. The IDs must
name a dedicated CI-only place that no person or other workflow uploads to. Each
artifact embeds a unique run marker that both runtime tasks verify before loading the
packages. The workflow executes fresh DEV and release tasks against the exact
unpublished archives validated in the same job.

The executable scripts under `bin` are the source of truth for command definitions.
The historical workspace bootstrap, retained solely as a parity reference, is:

```sh
rotrieve install
```

Roblox-internal analyzer parity reference:

```sh
roblox-cli analyze --project tests.project.json
```

Reproducible public static subset:

```sh
selene --config selene.toml modules/ WorkspaceStatic/
selene --config selene.toml tests/wally-consumer/smoke.server.lua
selene --config selene.toml tests/wally-workspace/dependency-proxy.lua
stylua --check modules bin WorkspaceStatic \
  tests/wally-consumer/smoke.server.lua \
  tests/wally-workspace/dependency-proxy.lua
```

Legacy canonical full-verification reference (requires an authorized internal environment):

```sh
bash bin/ci.sh
```

Canonical Wally archive, consumer, and source-workspace verification:

```sh
bash bin/ci-wally-packages.sh
bash bin/ci-wally-workspace.sh
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
  `bash bin/ci-wally-packages.sh`, `bash bin/ci-wally-workspace.sh`, and any other
  affected manifest or consumer/build validation.
- Documentation or MkDocs navigation changes require local-link review,
  `git diff --check`, and `bash bin/docs.sh`.
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
  legacy manifest before Wally test-workspace parity. Use `bin/bootstrap-tools.sh` to
  avoid this repository's Foreman manifest while provisioning the public pins. Rokit
  can still discover user-home manifests; the secret-free CI job uses a clean runner.

Treat the repository as transitional until the Wally workspace passes parity:

- The current Foreman and Rotriever manifests, generated `Packages` layout,
  `Packages.Dev` aliases, `_Workspace` layout, and executable `bin` commands remain
  authoritative. Do not remove them or switch CI merely because replacement manifests
  exist.
- Wally does not reproduce the current Rotriever workspace automatically. Build a
  deterministic Rojo/project-map compatibility layout that keeps local source under
  test and preserves existing package and dev aliases. Prefer that over mass-rewriting
  runtime imports.
- Canonical DEV test discovery includes the ReactDevtoolsExtensions integration test,
  which requires exact `DeveloperTools@0.2.3`. No exact package is present in the
  Paradoxum Wally index or its configured public fallback; the legacy source requires
  authorized Roblox access. This blocks Rotriever-independent test parity. Do not omit
  the test, substitute another version, or call a reduced lane parity. Obtain and audit
  an authorized exact artifact and map it as pinned local test-only input unless the
  user separately authorizes seeding or publishing it. Handle any test-policy change
  separately.
- Rocale 0.1.2 runs `.github/workflows/roblox-runtime.yml`. The protected job builds
  an exact unpublished-consumer place from the same nine archives it validates, then
  executes fresh DEV and release smoke tasks. Keep the API key only in
  `secrets.ROCALE_API_KEY`; keep `ROCALE_PLACE_ID` and `ROCALE_UNIVERSE_ID` in
  environment variables, and reserve those IDs for this workflow alone. A unique
  per-run marker in the built place must match the value supplied to each task before
  package loading begins. This is package runtime smoke, not source-suite, deferred,
  static-analysis, benchmark, or legacy parity.
- Do not execute the 109-suite source workspace under Rocale unless a hard preflight
  proves `debug.loadmodule` works. The reduced suite contains 109
  `jest.resetModules()` calls, legacy CI explicitly enables `EnableLoadModule`, and
  Rocale exposes no equivalent FastFlag option. Without trustworthy reloads, Jest
  warns and falls back to ordinary `require`, so a green result can be false-isolated.
- `.github/workflows/quality.yml` runs the public, secret-free package, source-layout,
  formatting, lint, documentation, and whitespace gates.
  `bin/ci-wally-workspace.sh` guards the 16-module compatibility map and exact
  109-suite inventory but deliberately does not execute Jest. A green result remains
  partial verification, not legacy runtime parity.
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
- A local unpublished-consumer Rojo build validates structure but does not execute
  `tests/wally-consumer/smoke.server.lua`. The protected runtime workflow executes
  that file explicitly in fresh DEV and release sessions so errors determine the
  Rocale task result. It checks all nine exports, package version and singleton
  identities, ReactTestRenderer behavior, and an actual ReactRoblox render/unmount
  lifecycle. Treat that result as a package smoke only.
- Establish one repository release version before publishing. Pin internal React
  package dependencies to that exact lockstep version so a staged publish cannot
  resolve a mixed release.
- Publish in dependency order: ReactGlobals; Shared; React, Scheduler, and ReactIs;
  ReactReconciler; ReactRoblox and ReactTestRenderer; then RoactCompat.
- Every package archive must exclude tests, snapshots, Rotriever manifests, and
  development-only files, and must include its runtime source, project mapping,
  README, and MIT license. Run `bash bin/ci-wally-packages.sh` to review the actual ZIP
  contents for every member.
- Commit and review every Wally lockfile. The unpublished-consumer fixture must
  resolve cleanly and match its committed lock. Run `bash bin/ci-wally-workspace.sh`
  to validate the source-based compatibility layout, exact suite inventory, and
  development lock. After an authorized publish, validate the private-registry
  example consumer.
- Only after static analysis, DEV, release, deferred, and benchmark parity may the
  active scripts and documentation switch to Wally and the old Foreman, Rotriever,
  and legacy Multipack publication paths be removed.
- Audit first-party consumers, including `paradoxum/react-flow`, before cutover.
  Ensure they resolve one React package family; duplicate React copies can break
  singleton state and shared internals.
- Ledger is a useful convention reference, not a template to copy blindly. Regenerate
  locks after manifest identity or registry changes and verify actual package contents.

Until that cutover is complete, run the legacy Rotriever lanes only in an authorized
environment where those tools exist. Otherwise, run the public gates, report legacy
parity as unverified, and describe the migration as partial rather than complete.
