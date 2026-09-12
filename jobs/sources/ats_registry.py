"""Curated company -> ATS registry for ATS-first discovery.

Single source of truth for the hosted-ATS boards this agent probes.
Adding a company here immediately extends its ATS jobs into the
pipeline without touching any adapter code.

Providers are reported honestly: boards/slugs that fail are listed
as blocked/error in the provider health report with the reason.
"""


GREENHOUSE_BOARDS = [
    "google",
    "stripe",
    "cloudflare",
    "dropbox",
    "github",
    "gitlab",
    "airbnb",
    "instacart",
    "coinbase",
    "datadog",
    "snowflake",
    "linkedin",
    "atlassian",
    "shopify",
    "reddit",
    "twilio",
    "okta",
    "box",
    "mongodb",
    "databricks",
    "slack",
    "asana",
    "hashicorp",
    "segment",
]

ASHBY_COMPANIES = [
    "Notion",
    "Ramp",
    "Airtable",
    "Deel",
    "Loom",
    "Vercel",
    "Linear",
    "Plaid",
    "Universe",
    "Terminal",
    "OpenSea",
    "Vanta",
    "Synthesia",
    "Aurora",
]


# Workable public widget accounts verified live.
WORKABLE_ACCOUNTS = [
    "zapier",
]


# Company -> hosted ATS mapping for the discovery report.
REGISTRY = {}

for _board in GREENHOUSE_BOARDS:
    REGISTRY[_board] = "greenhouse"

for _company in ASHBY_COMPANIES:
    REGISTRY[_company] = "ashby"

for _account in WORKABLE_ACCOUNTS:
    REGISTRY[_account] = "workable"


def ats_for(company):
    """Return the hosted ATS a company uses, if known."""
    return REGISTRY.get((
        str(company or "").strip().lower()
    ))