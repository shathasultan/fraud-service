# Benchmarks

Numbers measured against the reference course laptop. Record your own
measurements in the same table — your machine will differ, and that is
expected; what matters is the *shape* of the result (which row is faster,
and by roughly how much), not matching these numbers exactly.

## Day 1 — Module 2 (FastAPI hardening)

| Metric | `async def` (bug) | plain `def` (fixed) |
|---|---|---|
| p50 latency | — | 15 ms |
| p99 latency | 2.4 s | 38 ms |
| Throughput (c=25) | 118 req/s | 1,410 req/s |

- Load test: `hey -n 2000 -c 25 -m POST -D sample.json`
- Malformed corpus: 40/40 payloads rejected with 4xx (`payloads/malformed/`)
- Valid-traffic error rate: 0 non-2xx responses

## Day 2 — Lab 3 (Docker) — done

| Metric | Value |
|---|---|
| Naive build — image size | 2.41 GB |
| Naive build — cold build time | 6 min 12 s |
| Multi-stage build — image size | 412 MB (target ≤ 450 MB) |
| Multi-stage build — cold build time | ~1 min (varies by machine) |
| Warm rebuild (one-line code change) | 22 s, `CACHED` on the dependency layer |
| p99 — bare metal (Lab 2, no container) | 38 ms |
| p99 — containerised | 41 ms |
| Time-to-ready (`scripts/startup_time.sh`) | 6.8 s (target: under 10 s) |

Image ships as a non-root `appuser`, healthcheck on `/v1/ready`,
`docker compose ps` shows both `fraud-api` and `feature-cache` as
`(healthy)`.

## Day 2 — Lab 4 (Tests) — done

| Metric | Value |
|---|---|
| `pytest -m "not slow"` — pass count / duration | 52 passed in ~2.1 s |
| `pytest -m slow` — pass count / duration | 3 passed in ~5.9 s (includes the 5,000-row golden-file check) |
| Branch coverage (domain + service + api) | ~99% (target ≥ 80%) |
| Malformed corpus | 40/40 rejected with 4xx |

## Day 3 — Lab 5 (CI/CD pipeline)

_Fill in as you complete each step — reference numbers from the course:_

| Metric | Value |
|---|---|
| lint job duration | |
| test job duration | |
| image-smoke — cold run | ~5 min 40 s (reference) |
| image-smoke — warm run (GHA cache) | ~1 min 02 s (reference) |
| bad-pr blocked by branch protection? | yes / no |

## Day 3 — Lab 6 (Config, Secrets & Logs)

_Fill in after Lab 6 Step 3:_

| Metric | Value |
|---|---|
| p50 latency computed from JSON logs via `jq` | |
| Fail-fast startup error (bad `FRAUD_MODEL_PATH`) confirmed? | yes / no |
| `gitleaks` clean on final commit? | yes / no |

## Day 3 — Lab 5 (CI/CD pipeline)

| Metric | Value |
|---|---|
| lint job duration | 0.4 s local · see note |
| test job duration | 5.1 s local (4.1 s fast suite + 1.0 s behavioural) |
| image-smoke — cold run | _to be read from the Actions UI_ |
| image-smoke — warm run (GHA cache) | _to be read from the Actions UI_ |
| bad-pr: blocked by branch protection? | **yes** — see below |

### How these were measured

The `lint` and `test` rows are wall-clock timings of the exact commands the
workflow runs, on the machine this repository was developed on:

```
ruff check src tests && lint-imports && mypy src/fraud_service --strict   0.4 s
pytest -m "not slow" --cov-fail-under=80                                   4.1 s
pytest -m "behavioural and not slow" -q                                    1.0 s
```

A GitHub runner will report more than this, because a job's duration also
includes checking out the repository and installing dependencies. The `cache:
pip` key on `requirements.lock` is what keeps that install in the single-digit
seconds after the first run rather than around ninety.

The two `image-smoke` rows are deliberately left for the Actions UI to fill.
They measure the GHA layer cache — `cache-from: type=gha` — and that cache
only exists inside GitHub Actions. There is no honest local equivalent: a
local `docker build` twice in a row measures Docker's own layer cache, which
is a different mechanism with a different hit rate. Recording a local number
in those rows would be reporting the wrong measurement under the right label.

Expect the warm run to come in at roughly a third of the cold one or better.
Course reference shape, for comparison rather than a target: cold ≈ 5 min 40 s,
warm ≈ 1 min 02 s.

### bad-pr — what each gate caught

Two deliberate breakages on one branch, and each was caught by a different
job, which is the point of splitting them:

**`lint` — the architecture contract**

```
Clean architecture layers BROKEN
fraud_service.domain is not allowed to import fraud_service.api:
- fraud_service.domain.policies -> fraud_service.api.schemas (l.6)
Contracts: 0 kept, 1 broken.          exit code 1
```

**`test` — the boundary regression**

```
FAILED tests/unit/test_policies.py::test_decision_bands[0.85-block]
AssertionError: assert 'review' == 'block'
1 failed, 51 passed
```

Changing `>=` to `>` moves the exact block threshold out of the "block" band.
It is a one-character edit that no reviewer reliably catches by eye, and it
silently lets through the precise case the risk-approved threshold exists to
stop. The parametrised boundary test catches it in under five seconds.

`image-smoke` declares `needs: [lint, test]`, so it never started. `publish`
declares `needs: [image-smoke]`, so it never started either. One cheap failure
stopped the whole pipeline before a single image layer was built.

**The fix was made at the source**, not by weakening a check: the unused
import was removed and `>=` restored. Neither the test nor the contract was
touched. All four checks then returned green and the branch merged clean.
