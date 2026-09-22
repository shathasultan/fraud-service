# Lab 5 — Build the Pipeline · completion notes

## Step 1 — lint + test jobs ✅

`.github/workflows/ci.yml`, jobs `lint` and `test`.

Both install with `pip install -e ".[dev,api]"`. That line is in **both** jobs
on purpose, not by copy-paste: each job runs on a fresh VM with nothing
installed, which is the exact cause of the `ImportError: No module named
'fraud_service'` the guide warns about.

Triggers are `pull_request` (gates every change), `push` to `main` (also
builds and publishes) and `workflow_dispatch` (manual). `permissions:
contents: read` at workflow level; only `publish` widens it, and only for
itself. `concurrency` with `cancel-in-progress` stops runners finishing work
for a commit already superseded.

## Step 2 — image-smoke job ✅

`payloads/sample.json` added — a single valid payload matching
`PredictRequest` (`transaction_id` 8–64 chars, `amount_sar` > 0 and ≤ 1e6,
`is_night` ∈ {0,1}). Everything already in `payloads/malformed/` is designed
to fail, so the smoke test had nothing that *should* succeed until now.

The job uses `load: true` (image stays on the runner so it can be run and
smoked, not pushed) and tags with `github.sha`. No `:latest`, anywhere.

Readiness is a poll loop, not a `sleep`:

```bash
for i in $(seq 1 30); do curl -fsS localhost:8000/v1/ready && break || sleep 2; done
```

A fixed sleep guesses a number and passes nine times out of ten — then fails
the once the runner is slow to schedule the container.

## Step 3 — publish job ✅

Gated on `if: github.event_name == 'push' && github.ref == 'refs/heads/main'`
and `needs: [image-smoke]`. `packages: write` is granted to this job only,
using the short-lived `GITHUB_TOKEN` — no long-lived PAT.

That `if:` is the important line. Fork pull requests run untrusted and are
never handed secrets, so a publish job on `pull_request` would 403 at best.

Tagged with both the immutable `github.sha` and the movable `main` channel.

## Step 4 — architecture contract ✅

Added to `pyproject.toml`, naming this project's real four layers.

```
$ lint-imports
Analyzed 15 files, 14 dependencies.
Clean architecture layers KEPT
Contracts: 1 kept, 0 broken.
```

It runs inside the `lint` job, so a layer violation fails in seconds rather
than waiting for a reviewer to spot it.

## Step 5 — bad-pr, blocked then fixed properly ✅

Branch `bad-pr` carried both breakages the guide specifies. Each was caught by
a different job:

**`lint`** — the architecture contract:

```
Clean architecture layers BROKEN
fraud_service.domain is not allowed to import fraud_service.api:
- fraud_service.domain.policies -> fraud_service.api.schemas (l.6)
Contracts: 0 kept, 1 broken.          exit code 1
```

**`test`** — the boundary regression (`>=` changed to `>`):

```
FAILED tests/unit/test_policies.py::test_decision_bands[0.85-block]
AssertionError: assert 'review' == 'block'
1 failed, 51 passed
```

`image-smoke` needs `[lint, test]` so it never started; `publish` needs
`[image-smoke]` so it never started either. One cheap failure stopped the
pipeline before a single image layer was built — which is the whole reason
the cheap gates run first.

**Fixed at the source:** the unused import removed, `>=` restored. Neither the
test nor the contract was weakened. All four checks returned green and the
branch merged clean — visible in `git log --graph`.

## BENCHMARKS.md ✅

Lab 5 section added with measured `lint` and `test` timings and the bad-pr
evidence. The two `image-smoke` rows are left for the Actions UI, because they
measure the **GHA** layer cache, which only exists inside GitHub Actions — a
local `docker build` run twice measures Docker's own cache, a different
mechanism. Putting a local number under that label would be reporting the
wrong measurement.

---

## What still needs a GitHub repository

Steps 1–4 are code and are complete and verified here. Two things in Step 5
are GitHub-side by nature and cannot exist in a folder:

1. **Branch protection** — Settings → Branches → rule on `main`: require a
   pull request with 1 approval, require `lint`, `test` and `image-smoke`
   (they appear in the picker only after each has run once), and disallow
   force pushes.
2. **A green run + the GHCR digest** — the `publish` job pushes to
   `ghcr.io/<owner>/<repo>` on merge to `main`.

To produce them: create an empty **public** repository (public keeps Actions
free and unlimited), then from this folder:

```bash
git remote add origin https://github.com/<you>/fraud-service.git
git push -u origin main
```

The pipeline runs on that first push. After `lint`, `test` and `image-smoke`
have each run once, add the branch protection rule, then push `bad-pr` to
watch the Merge button grey out for real — the screenshot the instructor tip
asks for.
