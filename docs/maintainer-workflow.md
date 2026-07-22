# Maintaining the Paradoxum React Luau fork

## Ownership model

This repository is an independent downstream React implementation maintained by
Paradoxum Games. Work here is not assumed to be submitted to Facebook React or Roblox
React Luau.

The three source layers remain useful:

1. **Facebook React** defines semantics adopted from React.
2. **Roblox React Luau** provides the original translation, Roblox host integration,
   Luau adaptations, and legacy Roact compatibility.
3. **Paradoxum React Luau** owns the current contract and may preserve, replace, or
   extend either layer.

Upstream compatibility is a deliberate design choice, not an automatic requirement.
Provenance is retained so intentional decisions stay distinguishable from translation
mistakes and future ports remain tractable.

## Baselines are per file and feature

Do not assume the repository matches one React release. The project is broadly
described as React 17, while individual files contain selective changes from other
React versions and Roblox-only implementations.

Use this precedence when identifying a baseline:

1. exact source in the file's `-- ROBLOX upstream:` header;
2. a nearby source comment for a selectively ported hunk;
3. source recorded in its regression test or change description;
4. `js-to-lua.config.js` and historical alignment records;
5. the broad README version only as orientation.

If sources conflict, record the conflict and resolve it from behavior, history, and
the intended downstream contract. Do not silently select the newest source.

## Change classes and proof

| Change class | Source of truth | Required proof |
| --- | --- | --- |
| Upstream semantic port | Exact React commit SHA or immutable tag; PR as context | Source comparison, regression test, DEV and release suites |
| Roblox platform behavior | Explicit host/engine contract | Renderer or scheduler test and platform rationale |
| Paradoxum downstream change | Requested fork-owned contract | Downstream regression test and documented compatibility impact |
| Performance change | Existing behavior plus measurement | Behavioral tests and before/after benchmark evidence |
| Tooling/docs/package/release | Repository workflow and manifests | Static checks plus affected build/consumer validation; classify runtime effects separately |

Avoid combining unrelated classes. A behavior port should not also become a broad type
cleanup, package release, or formatting pass.

## Planning upstream-derived work

Perform a three-way semantic comparison before editing:

1. **Old upstream**: exact source represented by the current Luau file.
2. **Target upstream**: exact change being considered.
3. **Current downstream**: current Luau with existing Roblox and Paradoxum deviations.

Answer these questions:

| Question | Evidence to record |
| --- | --- |
| What changed upstream? | Semantic delta, not only a textual diff |
| Why did it change? | Bug, feature, performance, cleanup, or dependency |
| What already differs in Luau? | Existing deviation blocks and platform code |
| Is the assumption valid on Roblox? | Yes, no, or a separately defined host contract |
| Which test expresses the behavior? | Upstream test, downstream test, or an identified gap |
| What must remain compatible? | Public API, renderer behavior, flags, warnings, and performance |

If the target depends on intermediate React changes, port the dependency chain or
design an explicit downstream equivalent. Do not copy a final hunk while omitting its
prerequisites.

For a purely downstream feature, begin with the intended Paradoxum contract instead of
searching for an upstream justification.

## Implementation sequence

1. Reproduce the problem or port the behavioral test.
2. Confirm the test fails for the intended reason when practical.
3. Translate or implement the smallest coherent semantic change.
4. Preserve, replace, or remove existing deviations deliberately.
5. Run fast checks and the relevant test loop.
6. Review against exact source material and the downstream contract.
7. Run full DEV and release verification.
8. Run deferred and benchmark gates when applicable.
9. Update user-visible deviation and API documentation when public behavior changes.

Generated `js-to-lua` output is a draft, not an implementation verdict. Prefer clear,
correct Luau while retaining enough source structure and provenance for future review.

## Source headers and deviation markers

Update a file-level upstream header only after the whole file has been compared or
aligned to that source. For a selective backport, keep the file baseline and cite the
new source near the hunk, in the regression test, and in the handoff as appropriate.

Existing deviation markers identify differences from Facebook React. Preserve them
unless their reason no longer exists. For a new Paradoxum-owned difference inside an
upstream-derived file, use:

```lua
-- ROBLOX deviation START: PARADOXUM: use Roblox scheduler contract
-- downstream code
-- ROBLOX deviation END
```

The `ROBLOX deviation` spelling is retained for converter and fast-follow
compatibility; `PARADOXUM` identifies the new decision's owner. Do not mass-relabel
historical blocks.

New code with no React source does not need a fake upstream link. Identify it as
downstream-only when that distinction is not obvious.

## Luau and Roblox translation hazards

Review these explicitly:

- JavaScript falsey values versus Luau truthiness for `0` and empty strings;
- `undefined` and `null` collapsing into `nil`;
- table holes, length, numeric versus string keys, and iteration order;
- identity, equality, and missing coercions;
- `obj.method()` versus `obj:method()` and implicit receivers;
- closures and mutation captured across scheduled work;
- thrown errors versus `error`, `pcall`, and protected-call depth;
- yields, task scheduling, deferred signals, reentrancy, and work-loop boundaries;
- flags and globals cached at module initialization;
- DEV-only warnings and validation versus release behavior;
- Instance creation, parenting, property order, event connection, mutation, and
  deletion;
- allocation and table-shape changes on reconciler or scheduler hot paths.

## Test policy

- Prefer an upstream regression test for upstream semantics.
- Prefer a minimal downstream regression test for a Paradoxum contract.
- Preserve meaningful test names and assertion strength.
- Adapt DOM setup to the noop renderer or ReactRoblox deliberately.
- Restore changed globals and flags, and reset modules when necessary.
- Test warnings and failures in DEV when they are part of the contract.
- Test release mode when DEV branches or feature flags are touched.
- Do not update snapshots without explicit user authorization. Do not add `skip`,
  loosen assertions, or hide warnings merely to obtain a green run.

## Verification ladder

Executable scripts under `bin` are the command source of truth; the root `AGENTS.md`
summarizes their entrypoints and requirements.

| Change | Minimum evidence |
| --- | --- |
| Documentation only | Content/link review, `git diff --check`, and strict MkDocs build when available |
| Shell/tooling | Syntax/static check and safe execution path when available |
| Luau implementation | Analysis, Selene, StyLua, and relevant tests |
| Runtime semantic port | Relevant regression test plus full DEV and release suites |
| ReactRoblox lifecycle/order | Full suites and deferred-signal coverage when relevant |
| Reconciler or scheduler | Full suites, deferred tests, benchmark smoke, and before/after comparison for performance claims |
| Public API or package | Full suites, manifest review, and consumer/build smoke test |
| Snapshot change | Explicit user authorization and review of every snapshot diff |

When proprietary tools or engine access are unavailable, label the result **partially
verified** and list the missing gates. Do not substitute a weaker command and report it
as equivalent.

The public migration gates are intentionally separate:

- `bash bin/ci-wally-packages.sh` validates the nine publishable archives and a
  clean unpublished consumer.
- `bash bin/ci-wally-workspace.sh` validates the 16-module source compatibility
  map, exact 109-suite inventory, Wally development lock, sourcemap, and Rojo build.
  It does not execute Jest.
- The protected `.github/workflows/roblox-runtime.yml` job executes the exact
  unpublished consumer smoke in separate ReactTestRenderer and
  ReactRoblox/RoactCompat Rocale sessions for DEV and release. Renderer isolation is
  required because reconciler host-config injection mutates a cached module graph.
  Its place and universe IDs must identify a dedicated CI-only place. A unique
  per-run marker is embedded in the place and checked before package loading so
  another uploaded place cannot produce a false green.

None is a substitute for the canonical suites. In particular, the source suite uses
`jest.resetModules()` extensively. Do not run it under Rocale unless a preflight
proves `debug.loadmodule` is available; ordinary `require` fallback breaks test
isolation and can produce a false-green result. The exact
`DeveloperTools@0.2.3` dependency remains a separate full-parity requirement.

## Independent review checklist

Review the complete diff separately from implementation. For complex changes, use
parallel read-only reviewers for upstream semantics, Luau/Roblox hazards, tests/flags,
and performance.

Prioritize actionable correctness findings over style. Check:

- the implementation satisfies the stated downstream contract;
- no unrequested behavior or compatibility change escaped the scope;
- public React, ReactRoblox, and RoactCompat effects are explicit;
- exact upstream sources and prerequisite commits were used where relevant;
- file headers and local source comments remain truthful;
- deviation blocks are justified, balanced, and enclose the real difference;
- errors, warnings, scheduling, cleanup, and DEV/release behavior are correct;
- tests fail without the implementation and assertions remain strong;
- flag/global state is isolated and loaded modules are reset where required;
- snapshots are explicitly authorized, and skipped tests or `FIXME`/`TODO` additions
  are intentional;
- required verification and benchmarks ran, with unavailable gates identified.

Report findings by severity:

- **P0**: data loss, security issue, widespread runtime failure, or release-blocking
  corruption.
- **P1**: incorrect common behavior, compatibility break, scheduler/reconciler defect,
  false-green verification, or significant regression.
- **P2**: edge-case defect, meaningful test gap, likely future maintenance error, or
  localized performance risk.

Every finding should include a file and line, triggering condition, impact, and the
smallest credible correction. Do not report speculative possibilities without a
concrete path.

## Handoff record

Record:

- task class and downstream intent;
- exact source commit SHAs or immutable tags, optional PR context, or `not upstream-derived`;
- source-to-Luau file and test mapping;
- deviations preserved, added, changed, or removed;
- public compatibility and documentation impact;
- commands run and results;
- commands not run and why;
- benchmark evidence when applicable;
- remaining risk and rollback considerations.

The downstream contract decides correctness. Provenance makes that decision reviewable
and maintainable.
