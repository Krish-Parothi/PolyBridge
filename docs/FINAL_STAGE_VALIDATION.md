# Final-stage validation notes

Validation was run on **October 24, 2026** from the repository working tree.
The working tree already contained earlier phase edits; those edits were
preserved.

## Checks

Backend:

```text
cd backend
uv sync
uv run pytest -q
```

Result: **216 passed**. Pytest emitted one Starlette/httpx deprecation warning;
it did not affect the result.

Frontend:

```text
cd frontend
npm install
npm run lint
npm run build
```

Results: **oxlint 0 warnings / 0 errors** and a successful Vite production
build.

## Independent seven-language sample matrix

The canonical sample in `backend/tests/test_phase2_compatibility.py` was
parsed, type-inferred, emitted to every target, compiled or simulated, and
compared against the source output. The matrix covered all 49 source-target
pairs:

```text
transpiled: 49
executed:   49
verified:   49
```

The matrix is a representative compatibility check, not a proof that every
construct in every language is supported.

## Important behavior

- C++ canonical `for` loops now lower to `ForRangeStmt`; C++ range-for loops
  lower to `ForEachStmt` instead of being silently discarded.
- C++ can be compiled and executed by the sandbox with `g++ -std=c++20`.
- Verilog uses Icarus Verilog when available. A missing simulator is reported as
  `runtime_unavailable`; structural text is never treated as behavioral proof.
- Arduino uses a mocked host `Serial`/`delay` core for deterministic compilation
  and execution checks. Board timing, peripherals, and electrical behavior
  still require Arduino tooling or a hardware simulator.
- `/api/verify` supports multiple `test_inputs` and returns per-case results.
- The transpile response includes before/after IR, optimization statistics, CFG,
  TAC, and parser/semantic diagnostics.

## Remaining security boundary

The runner uses subprocesses, temporary directories, bounded timeouts, cleanup,
and argument-list compiler invocations. It is not a hostile multi-tenant
sandbox: production deployment still needs container/VM isolation, filesystem
policy, cgroups or job objects for memory enforcement, and a restricted worker
service before accepting arbitrary untrusted programs.
