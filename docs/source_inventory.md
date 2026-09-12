# Job Source Inventory & Status

Authoritative list of discovery providers for the multi-source job agent.
This inventory is honest: every entry reports whether it is wired into the
pipeline, blocked, or unsupported, and why.

Legend

- `ACTIVE`   - wired into `source_runner` and producing jobs
- `BLOCKED`  - wired/hooked but failing (no results); reason listed
- `UNSUPPORTED` - evaluated and deliberately not implemented; reason listed
- `CI-ONLY`  - works only where `python-jobspy` is available (GitHub Actions)

## ATS / company boards (ATS-first)

| Provider | Type | Status | Notes |
|----------|------|--------|-------|
| Greenhouse | ATS | ACTIVE | public board API, 24 companies |
| Ashby | ATS | ACTIVE | public posting API, 14 companies |
| Workable | ATS | ACTIVE | public search API + widget accounts |
| Lever | ATS | BLOCKED | board API returns 404 for probed companies |
| SmartRecruiters | ATS | UNSUPPORTED | legacy public postings API returns empty payloads for all probed company tokens |
| Recruitee | ATS | UNSUPPORTED | requires auth (401/404 on public endpoints) |
| Teamtailor | ATS | UNSUPPORTED | public feed endpoint has TLS hostname mismatch |
| iCIMS / Jobvite / BambooHR | ATS | UNSUPPORTED | auth-gated / paywalled public endpoints |

## Remote / worldwide boards

| Provider | Status | Notes |
|----------|--------|-------|
| WeWorkRemotely | ACTIVE | RSS/HTML board |
| Remote OK | ACTIVE | JSON + RSS |
| Remotive | ACTIVE | public JSON API |
| Jobicy | ACTIVE | public JSON API |
| Working Nomads | ACTIVE | JSON feed |
| Himalayas | ACTIVE | public JSON API |
| Remote.co | BLOCKED | no public API |
| FlexJobs | BLOCKED | paywalled listings |
| Remotive (EU) | ACTIVE | via RS page above |

## Job boards & aggregators

| Provider | Status | Notes |
|----------|--------|-------|
| 4 Day Week | UNSUPPORTED | no public feed |
| Authentic Jobs | UNSUPPORTED | 404 on feed endpoints |
| Compass Rebels | UNSUPPORTED | no public machine-readable API |
| EuroRemote (RSS) | ACTIVE | public RSS feed |
| FreeHire | ACTIVE | public JSON API |
| Jobgether | UNSUPPORTED | 404 on public endpoints |
| Jobs (python.org) | ACTIVE | public RSS feed |
| Jobspresso | UNSUPPORTED | 404 on feed endpoints |
| Jet I | UNSUPPORTED | 404 on public endpoints |
| NoDesk | UNSUPPORTED | 404 on feed endpoints |
| Remote4me | UNSUPPORTED | 404 / DNS failures |
| RemoteLeaf | UNSUPPORTED | 404 on feed endpoints |
| Remoteco | BLOCKED | no public API |
| Startup.jobs | UNSUPPORTED | 404 on public endpoints |
| Working Nomads | ACTIVE | JSON feed |
| Unstop | BLOCKED | no public API |

## JobSearch aggregators (search engine style)

| Provider | Status | Notes |
|----------|--------|-------|
| Jora | UNSUPPORTED | plain HTML, anti-bot and ToS risk; not scraped |
| LinkedIn | CI-ONLY | via python-jobspy in GitHub Actions |
| Indeed | CI-ONLY | via python-jobspy in GitHub Actions |
| Glassdoor | CI-ONLY | via python-jobspy in GitHub Actions |
| Google | CI-ONLY | via python-jobspy in GitHub Actions |
| ZipRecruiter | CI-ONLY | via python-jobspy in GitHub Actions |
| Bayt | CI-ONLY | via python-jobspy in GitHub Actions |

## India boards

| Provider | Status | Notes |
|----------|--------|-------|
| Naukri | BLOCKED | no public API; affiliate endpoint unresolved |
| Foundit | BLOCKED | no public API |
| TimesJobs | BLOCKED | no public API |
| Shine | BLOCKED | no public API |
| Freshersworld | BLOCKED | no public API |
| Instahyre | BLOCKED | no public API |
| Cutshort | BLOCKED | no public API |
| Unstop | BLOCKED | no public API |

## Startup / direct-hire

| Provider | Status | Notes |
|----------|--------|-------|
| YC (Work at a Startup) | BLOCKED | no stable public API |
| Wellfound | BLOCKED | login-gated; scraping against ToS |

## Counts

- Active providers: 13 (12 REST/RSS sources + jobspy sites in CI)
- Registered provider entries in the pipeline: 26+ (India boards and known
  blocked boards stay registered so their health is visible)
- Evaluated & unsupported: ~20
- Total tracked sources: 50+