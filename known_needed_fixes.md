# Known Needed Fixes

This checklist captures the follow-up work requested in review for the smoke
test branch. It is based on the current branch state after the `uv` work was
merged elsewhere.

## Checklist

- [ ] Replace tolerance checks like `abs(...) <= ...` with `math.isclose(...)`
      in the smoke tests.
  - Current example: `integration_test/smoke/test_smoke.py`

- [ ] Move smoke runtime state off-repo into a per-run temporary directory
      instead of `integration_test/runtime/`.
  - Update all references in:
    - `integration_test/smoke/run_smoke_stack.py`
    - `integration_test/smoke/nicos.conf`
    - `integration_test/smoke/setups/system.py`
    - `integration_test/smoke/test_smoke.py`
    - `integration_test/smoke/Dockerfile`
    - `integration_test/smoke/docker-compose.ci.yml`
    - `integration_test/README.md`

- [ ] Remove the script-style import/path hack and make the smoke test code a
      proper installable module in the repo packaging.
  - Current symptom: `sys.path.insert(...)` in
    `integration_test/smoke/run_smoke_stack.py`

- [ ] Modernize the smoke test container to use supported Python plus `uv`.
  - Remove the Python 3.8 base image.
  - Stop hardcoding installation via `pip` and `requirements.txt`.
  - Rework CI/container setup to install from the repo's current packaging.

- [ ] Remove unnecessary image build dependencies after the Python/`uv`
      migration if wheels are already available from the package index.

- [ ] Revisit the development workflow and decide whether to keep the custom
      host-side orchestration script or simplify to a compose-driven test
      container flow.
  - If the compose-driven flow is adopted, remove now-redundant compose
    probing, Kafka readiness, and topic bootstrap code from
    `integration_test/smoke/run_smoke_stack.py`

- [ ] Update documentation to match the final workflow.
  - Run commands
  - Docker requirement
  - Tempdir/runtime behavior
  - Compose layout and CI flow

## Suggested Order

1. Switch Dockerfile and CI smoke setup to supported Python and `uv`.
2. Package the smoke code properly and remove the `sys.path` workaround.
3. Move runtime files to a tempdir and thread that through config, tests, and
   docs.
4. Decide whether the custom runner still justifies its complexity.
5. Apply the small test cleanup (`math.isclose`) and final doc polish.

## Notes

- The earlier review dependency on waiting for the `uv`/newer-Python work is
  already satisfied.
- The remaining work is mostly cleanup and simplification around the smoke test
  packaging, runtime layout, and Docker workflow.
