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

| Metric | Value |
|---|---|
| lint job duration | **35 s** |
| test job duration | **44 s** |
| image-smoke — cold run | **111 s** |
| image-smoke — warm run (GHA cache) | **33 s** |
| publish job duration | **78 s** |
| cache speed-up | **3.4×** |
| bad-pr blocked by branch protection? | **yes** |

Measured on `ubuntu-latest`, runs
[#2](https://github.com/shathasultan/fraud-service/actions/runs/35720653766)
(cold) and
[#3](https://github.com/shathasultan/fraud-service/actions/runs/35720874880)
(warm, triggered by an empty commit).

Published image, tagged by commit SHA and never `:latest`:

```
ghcr.io/shathasultan/fraud-service:128142db72f219677c5e8f2c4366cfeb847e18c4
digest sha256:a4ce291b92c4846543e85fbe6d9d051c2bd183ab9f84e36a5d328d833cce0315
```

Both `image-smoke` rows come from the Actions UI, because they measure the GHA
layer cache — `cache-from: type=gha` — which exists only inside Actions. A
local `docker build` run twice measures Docker's own cache: a different
mechanism with a different hit rate.

The 3.4× is the whole argument for the cache. Course reference shape, for
comparison rather than a target: cold ≈ 5 min 40 s, warm ≈ 1 min 02 s — this
project's image is smaller, so both are lower while the ratio holds.

### bad-pr — what each gate caught

Two deliberate breakages on one branch, each caught by a different job.

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

Changing `>=` to `>` moves the exact block threshold out of the block band. A
one-character edit no reviewer reliably catches by eye, letting through the
precise case the risk-approved threshold exists to stop.

`image-smoke` needs `[lint, test]`, so it never started. `publish` needs
`[image-smoke]`, so it never started either. One cheap failure stopped the
pipeline before a single image layer was built.

**Fixed at the source**: the import removed, `>=` restored. Neither the test
nor the contract was touched.

## Day 3 — Lab 6 (Config, Secrets & Logs)

_Fill in after Lab 6 Step 3:_

| Metric | Value |
|---|---|
| p50 latency computed from JSON logs via `jq` | |
| Fail-fast startup error (bad `FRAUD_MODEL_PATH`) confirmed? | yes / no |
| `gitleaks` clean on final commit? | yes / no |
