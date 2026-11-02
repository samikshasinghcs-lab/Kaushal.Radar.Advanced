# Kaushal Radar

**A district-level labour-market decision-support prototype for Karnataka. It tells an officer where to look first, how sure the evidence is, and blocks any capacity decision until independent evidence agrees.**

*KSISU Skillathon 2026 finale · Bengaluru Skill Summit · Built by Samiksha Singh, Mysuru*
Live dashboard: <https://kaushal-radar.lovable.app> · Repo: `github.com/samikshasinghcs-lab/Kaushal.Radar.Advanced`

> **Read this first.** This is a research and decision-support prototype. It is **not** a government deployment, **no department link is live**, and nothing here is a funding decision. Every capability below is labelled **Built**, **Proposed** or **Not run**, and the labels are the truth.

---

## Why this exists

Karnataka's per-capita income gap between Bengaluru Urban (₹8.56 lakh) and Kalaburagi (₹1.44 lakh) is about **5.9x**, and one district produces **40.4%** of state output. Kalyana-Karnataka (7 districts) holds 19% of residents and 10% of output, but 28% of Yuvanidhi registrants. NCS, e-Shram, EPFO, PLFS, PMKVY and ITI/NCVT each do their own job. None was designed to combine them into a **district decision**. Kaushal Radar is that coordination layer. It complements those systems and does not replace them.

**Principles:** code calculates, AI advises, humans decide. Registration is not unemployment. A flag starts an investigation, never a funding decision. Raise the bottom, strengthen the top, leave no district or worker behind.

## Quick start

Requires Python 3.12 (used in CI and Docker) and the `openssl` command-line tool (for one TLS test).

```bash
pip install -r requirements.txt
python run_all.py                 # all tests + AI evaluation + demos + regenerates reports/ (about 1 minute)
python run_all.py --tests-only    # tests only
```

Run the local API:

```bash
cd core && python api_server.py   # http://127.0.0.1:8000, stdlib only
# demo mode (KR_JWT_SECRET unset) accepts a header stub:
curl -H "X-User: demo" -H "X-Role: department_officer" http://127.0.0.1:8000/districts/raichur/indicators
# signed tokens, required whenever KR_JWT_SECRET is set:
KR_JWT_SECRET=<16+ byte secret> python auth_tokens.py issue USER ROLE [DISTRICT]
```

Docker: `KR_JWT_SECRET=<16+ byte secret> docker compose up --build` (API on port 8000, runs as a non-root user).

Dashboard: open `dashboard/Kaushal_Radar_Dashboard_v0_5_final.html` in a browser. No server needed.

Make targets: `make demo`, `make test`, `make reports`, `make api`.

## Verified results

Re-run on 2 Nov 2026: `python run_all.py` finished **ALL GREEN (24 of 24 steps)**. Numbers below regenerate into `reports/` each run and can vary slightly between machines.

| Area | Result | Caveat |
|---|---|---|
| Test suites | 278 tests: 159 in `core/` (16 suites), 119 in `ai_layer/` | Unit and integration tests, not field validation |
| Security tests | 54 of 54 pass | No independent penetration test |
| AI evaluation lab | 139 of 141 labelled cases behave as labelled (98.6%) | Synthetic cases, mock provider: tests the guards, not model accuracy |
| Prompt injection | 34 of 36 adversarial and malformed cases handled | Heuristic detector; 2 hard cases slip through (see Known gaps) |
| Brief checker on 31 real LLM drafts | 27 auto-pass, 1 review, 3 false rejects; 69 of 69 injected errors caught | Tuned on the same set. A regression fix, **not** held-out accuracy |
| Denominator robustness | Rank correlation 0.96 across two denominators; 7 of top 8 districts shared | Census 2011 is 15 years old |
| Scalability (synthetic, 1 CPU) | 1M rows about 0.3 s and 34 MB; 5M rows about 1.7 s and 160 MB; identical output hash across repeats | Single process, in memory, not a production load test |
| Failure recovery | Crash during aggregate or write leaves the last good output intact | Tested at 1M rows |
| API concurrency | 200 clients, 4,000 requests, 0 errors, p95 about 150 ms | Local loopback, mock gate evidence |
| Claim traceability | 10 of 10 tracked claims trace to a source and calculation | See `core/claims_register.csv` |

## How it works

```
Public tables / department files
  -> ingest + validate (schema, PII block, small-cell suppression) -> harmonise (LGD district codes)
  -> store (idempotent refresh, job queue, backup/restore)
  -> engines: DGPI indicators, two-sided district matrix, flags, routing
  -> Corroboration Gate (no action without independent, corroborating evidence)
  -> intervention draft -> human decision -> hash-chained ledger
  -> API (RBAC, signed tokens, rate limit) -> dashboard
AI layer (advisory only): authenticate -> screen injection/PII -> authorised evidence -> deterministic engine
  -> AI analysts -> source / number / claim guards -> decision gate -> human review -> audit
```

Full diagram: `docs/ARCHITECTURE.md`. `core/test_architecture.py` fails if a module named there disappears.

**Roles:** `administrator`, `department_officer`, `district_officer` (own district only), `auditor`. Deny by default. See `core/access_control.csv`.

## Repository layout

| Folder | What it holds |
|---|---|
| [`core/`](core/README.md) | DGPI engine, Corroboration Gate, ledger, ingestion, API, tests, dashboard builder |
| [`ai_layer/`](ai_layer/README.md) | Guarded AI decision-support pipeline and the 141-case evaluation lab |
| [`dashboard/`](dashboard/README.md) | Single-file HTML dashboard prototypes |
| [`data/`](data/README.md) | Real public indicator table, AISHE workbook, PLFS benchmarks, synthetic samples |
| [`reports/`](reports/README.md) | Auto-generated evidence: scalability, security, AI, traceability, routing |
| [`docs/`](docs/README.md) | OpenAPI specs, data contract, DPIA, threat model, DPDP control map, model card |
| [`analysis/`](analysis/README.md) | Routing scatter and seat-allocation comparison |
| `tools/` | `make_reports.py` regenerates everything in `reports/` |
| `.github/workflows/` | CI (tests, secret scan, `pip-audit`, dashboard sync) and a ZAP scan workflow |

## What is built, proposed and not run

| Capability | Status |
|---|---|
| DGPI on 31 districts with two denominators and rank-stability bands | **Built**, real public data |
| Two-sided district matrix (Mission A: raise the bottom 8; Mission B: strengthen the top 7) | **Built**, proxy indicators |
| Corroboration Gate, decision ledger, hash-chained audit | **Built**; non-Yuva-Nidhi evidence cards are MOCK and labelled |
| Departmental file upload to validate, harmonise, store, evidence card | **Built**, tested on SYNTHETIC files only |
| AI guard pipeline (grounding, numeric and hallucination guards, human gate) | **Built** on synthetic evidence with a deterministic mock provider |
| Signed tokens, rate limit, lockout, secret scan | **Built with limitations**; State SSO and key management not done |
| AISHE 2023-24 (state level) and PLFS Karnataka benchmarks | **Built with limitations**; some PLFS rows are secondary-sourced or unverified |
| Labour Market Pulse, skill transition, workforce inclusion, forecasts | **Synthetic demonstration** |
| Postgres schema and SQL generator | Written, **not run** |
| NCS, ITI/NCVT, EPFO, e-Shram, MCA, PLFS micro-data adapters | **Proposed**, not ingested, no agreements |
| Live LLM run on 31 districts; blind adversarial set; rules-only vs rules + AI | **Not run** |
| Usability test with real officers (SUS) | **Not run**, protocol in `reports/USABILITY_REPORT.md` |
| Independent security review and penetration test; legal review of DPIA | **Not done** |
| National benchmarking | **Roadmap** |

## Governance and DPDP posture

Designed for DPDP with disclosed gaps. It is **not** claimed to be DPDP compliant. Controls built: aggregates only, no names, Aadhaar, phone or bank data, PII columns refused at upload, cells under 10 suppressed, deny-by-default RBAC with district scoping, signed tokens, rate limit and lockout, encryption at rest, hash-chained audit with an HMAC tail anchor, and a human sign-off on every output. See `docs/DPDP_CONTROL_MAP.md`, `docs/THREAT_MODEL.md`, `docs/DPIA.md`.

AI never allocates funds, decides eligibility, or scores individuals. The system identifies barriers to opportunity, not the worth or employability of any person.

## Known gaps (kept visible on purpose)

- The prompt-injection detector is heuristic. 2 of 10 adversarial cases in the evaluation lab are not caught.
- Truncating the newest audit entries is detected only with an external anchor kept in a separate write-once store.
- Demo mode accepts a header stub for auth. Production needs State SSO and key management.
- Retention and deletion are partly code (`core/retention.py`) and need the data owner's sign-off.
- The brief-checker result is tuned on its own test set.
- `core/analysis_denominators_and_ai_tests.py` and `core/llm_brief_test.py` need the raw source CSVs from the public GitHub repository.
- Registration is take-up of one scheme. It is not unemployment, and 98.5% of Yuva Nidhi registrants in the dataset are degree holders, so that cohort alone should not drive ITI planning.

## Proposed next step

A **90-day pilot** with one department and one data feed, in 15-day blocks: consultation, data validation, labour-market and skill-gap assessment, inclusion analysis, intervention recommendations, evaluation. Process KPIs are measured inside 90 days. Placement, 3- and 6-month retention and wage progression are measured after. Planning estimate: about ₹0.9-1.2 crore in year one and ₹30-40 lakh a year to run, to be validated by the State. No department agreement exists yet.

## Data sources

DES Karnataka (GDDP and per-capita income 2024-25, MSME tables), Economic Survey of Karnataka 2025-26, Yuvanidhi registrant table (2022-23 cohort), Census 2011 (2023 boundaries), AISHE 2023-24, PLFS. Each indicator's source, calculation and limitation is in `core/claims_register.csv`.

## AI assistance disclosure

Claude, Gemini and ChatGPT assisted. The participant selected the data, directed the analysis and is responsible for the content.

## Contact

Samiksha Singh · singhsameeksha393@gmail.com
