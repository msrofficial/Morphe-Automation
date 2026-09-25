# Morphe-Automation Architecture (v2 independent)

4-layer design. Old `src/*` flat layout is legacy; new code lives here.

```
core/
  models.py   -> BuildTarget, AppSpec, BuildResult (dataclasses, no logic)
  fetch/      -> SourceAdapter interface + per-source plugins (Phase 2)
  patch/      -> PatchRequest + rule engine (Phase 3)
  package/    -> APK signer + module packager (Phase 3)
tools/
  tool.py     -> check|record|merge|cleanup subcommands (Phase 4)
cli.py        -> single entry: unified.json -> targets -> pipeline
```

Rules:
- New code never imports legacy `src.downloader` internals; legacy stays as shim until Phase 2-3 replace it.
- Function names are domain-based (`fetch_stock`, `apply_patches`, `package_module`), not Rookie/j-hc names.
- Every phase keeps CI green: legacy path works until new path proves green via manual run.
