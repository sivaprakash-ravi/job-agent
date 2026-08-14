# Daily Job Hunter

This is a small personal job-search automation project. It helps find relevant
jobs regularly, so the search does not have to start from scratch every day.

## How it works

```text
GitHub Actions (every 3 hours)
        ↓
Python job collector
        ↓
FreeHire job API
        ↓
Profile-based filtering
        ↓
jobs.json report + alert-ready output
```

## Built so far

- A GitHub Actions workflow runs automatically every 3 hours.
- A beginner-friendly Python collector gets recent job listings from the
  FreeHire API.
- `jobs/profile.py` holds general target roles, skills, locations, and job
  preferences derived from the resume—without storing the resume itself or
  private contact details.
- Matching jobs are saved in `reports/jobs.json` and uploaded as a GitHub
  Actions artifact.
- The project also prepares alert output so new matching jobs can be shared
  without repeatedly sending the same listing.

## What's next

The next main step is improving job matching and ranking, so the best-fitting
roles appear first. Later, the project may add more job sources and AI-assisted
matching.

## Privacy

This repository should contain only general job-search preferences. It should
not contain a resume PDF, phone number, personal email, address, passwords,
API keys, or tokens.
