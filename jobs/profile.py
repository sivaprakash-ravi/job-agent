TARGET_ROLES = [
    # Support / Operations
    "Application Support Engineer",
    "Production Support Engineer",
    "Technical Support Engineer",
    "Cloud Support Engineer",
    "Cloud Infrastructure Support Engineer",
    "Infrastructure Support Engineer",
    "Cloud Operations Engineer",
    "Operations Engineer",
    "Production Operations Engineer",
    "Application Operations Engineer",
    "Technical Operations Engineer",
    "Infrastructure Engineer",

    # Cloud / DevOps / SRE
    "Site Reliability Engineer",
    "SRE",
    "DevOps Engineer",
    "Junior DevOps Engineer",
    "Cloud Engineer",

    # QA / Testing
    "QA Engineer",
    "Junior QA Engineer",
    "Quality Assurance Engineer",
    "Software Test Engineer",
    "Junior Test Engineer",
    "Test Engineer",
    "QA Analyst",
    "Junior QA Analyst",
    "Quality Analyst",
    "Quality Assurance Analyst",
    "Manual Tester",
    "Manual Testing Engineer",
    "Software Tester",
    "Application Tester",
    "QA Tester",
    "Software QA Engineer",
    "Functional Tester",
    "Functional Test Engineer",
    "Test Analyst",
    "QA Support Engineer",
    "Production QA Engineer",
    "Application Quality Engineer",
]

SKILLS = [
    # Cloud / Infrastructure
    "GCP",
    "Google Cloud",
    "AWS",
    "Azure",
    "Linux",

    # Programming / Database
    "Python",
    "Java",
    "SQL",

    # API / Tools
    "REST API",
    "API Testing",
    "ServiceNow",
    "New Relic",
    "NRQL",
    "Postman",

    # DevOps
    "Docker",
    "Kubernetes",
    "Git",
    "CI/CD",
    "DevOps",
    "SRE",

    # Operations / Support
    "Production Support",
    "Application Support",
    "Incident Management",
    "Root Cause Analysis",
    "Log Analysis",
    "System Monitoring",
    "Application Monitoring",

    # QA / Testing
    "Manual Testing",
    "Software Testing",
    "Quality Assurance",
    "QA Testing",
    "Test Cases",
    "Test Case Design",
    "Test Execution",
    "Regression Testing",
    "Functional Testing",
    "Defect Tracking",
    "Bug Tracking",
    "Jira",
]

# ============================================================
# CAREER JOB-FAMILY PRIORITIES (single source of truth)
# ============================================================
#
# This is a PRIORITY ORDER, not an exclusion rule. All families stay
# in discovery; the tier only steers ranking, enrichment selection,
# query budget and reporting. Lower numbers are higher priority.
#
#   P1 - Support / Operations (highest application priority)
#   P2 - QA / Testing
#   P3 - Development / DevOps / SRE / Cloud / Infrastructure

JOB_FAMILY_PRIORITY = {
    "technical_support": 1,
    "application_support": 1,
    "production_support": 1,
    "operations_support": 1,
    "cloud_support": 1,
    "qa_testing": 2,
    "software_development": 3,
    "devops": 3,
    "sre": 3,
    "cloud_infrastructure": 3,
}

PRIORITY_TIERS = {1: "P1", 2: "P2", 3: "P3"}

PRIORITY_EMOJIS = {"P1": "🥇", "P2": "🥈", "P3": "🥉"}

JOB_FAMILY_LABELS = {
    "technical_support": "Technical Support",
    "application_support": "Application Support",
    "production_support": "Production Support",
    "operations_support": "Operations Support",
    "cloud_support": "Cloud Support",
    "qa_testing": "QA",
    "software_development": "Software Dev",
    "devops": "DevOps",
    "sre": "SRE",
    "cloud_infrastructure": "Cloud/Infra",
}

# Career-priority boosts.
#
# Ranking boost is applied ONLY to the presentation/rank key, never to
# match_score, so the MINIMUM_SCORE=45 gate and all hard filters keep
# their exact current behavior.
RANK_PRIORITY_BOOST = {"P1": 12, "P2": 8, "P3": 0}

# Enrichment boost is applied to the cheap pre-enrichment priority
# signal so the stratified selector gives P1/P2 a fair share before
# the cap. P1 support gets the largest boost; P2 QA gets a small
# signal that never lets it outrank a genuinely stronger P3 listing.
ENRICHMENT_PRIORITY_BOOST = {1: 12, 2: 2, 3: 0}

# Role-family detection rules.
#
# - ``strong_title`` phrases are self-evident technical roles: the
#   title alone qualifies the family (still vetoed by ``exclude``).
# - ``weak_title`` phrases need real JD evidence before the family is
#   applied, so generic "support" / "quality" titles are not adopted.
# - ``exclude`` phrases veto the family (e.g. call-center customer
#   service without technical duties).
# A job may match several families; the HIGHEST-priority genuinely
# applicable family wins.
JOB_FAMILY_RULES = {
    "technical_support": {
        "strong_title": [
            "technical support engineer",
            "technical support analyst",
            "technical support specialist",
            "technical support",
            "tech support",
            "tech support engineer",
            "software support engineer",
            "systems support engineer",
            "platform support engineer",
        ],
        "weak_title": [
            "support engineer",
            "support analyst",
            "support specialist",
            "support associate",
        ],
        "evidence": [
            "troubleshoot",
            "debug",
            "diagnos",
            "escalat",
            "incident",
            "root cause",
            "ticketing",
            "itil",
            "servicenow",
            "monitor",
            "logs",
            "patching",
            "configuration",
            "deployment",
            "api",
            "sql",
            "linux",
            "server",
            "vpn",
            "slack",
        ],
        "exclude": [
            "call center",
            "customer service representative",
            "customer care",
            "voice support",
            "customer support representative",
            "telecalling",
            "inbound call",
            "outbound call",
        ],
    },
    "application_support": {
        "strong_title": [
            "application support engineer",
            "application support analyst",
            "application support specialist",
            "application support",
            "app support",
            "application operations engineer",
            "application operations",
        ],
        "weak_title": [],
        "evidence": [
            "troubleshoot",
            "application",
            "production environment",
            "deployment",
            "release",
            "bug fix",
            "root cause",
            "escalat",
            "incident",
            "monitor",
            "jira",
            "sql",
            "api",
        ],
        "exclude": [
            "call center",
            "customer service representative",
            "voice process",
        ],
    },
    "production_support": {
        "strong_title": [
            "production support engineer",
            "production support analyst",
            "production support",
            "production operations engineer",
            "production operations",
        ],
        "weak_title": [],
        "evidence": [
            "production",
            "incident",
            "monitor",
            "on-call",
            "mitigat",
            "restore service",
            "deployment",
            "release",
            "database",
            "server",
            "application",
        ],
        "exclude": ["call center"],
    },
    "operations_support": {
        "strong_title": [
            "operations engineer",
            "technical operations engineer",
            "technical operations",
            "it operations engineer",
            "it operations",
            "cloud operations engineer",
            "cloud operations",
            "operations support engineer",
            "operations support",
            "infrastructure support engineer",
            "infrastructure support",
            "devops support engineer",
            "devops support",
            "noc engineer",
            "noc",
            "monitoring engineer",
            "system administrator",
            "systems support engineer",
        ],
        "weak_title": [
            "systems engineer",
        ],
        "evidence": [
            "incident",
            "monitor",
            "on-call",
            "server",
            "automation",
            "deployment",
            "troubleshoot",
            "escalat",
            "runbook",
            "uptime",
            "availability",
            "infrastructure",
            "linux",
            "cloud",
        ],
        "exclude": [],
    },
    "cloud_support": {
        "strong_title": [
            "cloud support engineer",
            "cloud support analyst",
            "cloud support associate",
            "cloud support",
            "cloud infrastructure support engineer",
            "cloud infrastructure support",
            "cloud operations",
        ],
        "weak_title": [
            "cloud engineer",
            "cloud associate",
        ],
        "evidence": [
            "support engineer",
            "support associate",
            "support",
            "troubleshoot",
            "incident",
            "escalat",
            "ticket",
            "help desk",
            "user account",
            "set up",
            "setup",
            "customer support",
        ],
        "exclude": [
            "call center",
            "customer service representative",
            "telecalling",
        ],
    },
    "qa_testing": {
        "strong_title": [
            "quality assurance engineer",
            "quality assurance analyst",
            "software quality assurance",
            "qa engineer",
            "junior qa engineer",
            "qa analyst",
            "qa tester",
            "software qa",
            "software test engineer",
            "software tester",
            "test engineer",
            "test analyst",
            "test automation engineer",
            "qa automation",
            "automation tester",
            "sdet",
            "manual tester",
            "manual testing engineer",
            "functional tester",
            "qa support engineer",
            "software testing engineer",
        ],
        "weak_title": [
            "quality engineer",
            "quality analyst",
            "tester",
            "quality assurance",
            "test lead",
        ],
        "evidence": [
            "test case",
            "test cases",
            "test execution",
            "testing",
            "regression",
            "functional test",
            "integration test",
            "unit test",
            "selenium",
            "automation testing",
            "postman",
            "api testing",
            "manual testing",
            "smoke test",
            "uat",
            "defect tracking",
            "bug tracking",
            "jira",
            "test plan",
            "quality assurance",
            "test script",
        ],
        "exclude": [
            "call center",
            "customer service representative",
            "voice process",
        ],
    },
    "devops": {
        "strong_title": [
            "devops engineer",
            "junior devops engineer",
            "junior devops",
            "devops",
            "devops support engineer",
        ],
        "weak_title": [],
        "evidence": [
            "ci/cd",
            "pipeline",
            "jenkins",
            "github actions",
            "terraform",
            "ansible",
            "docker",
            "kubernetes",
            "infrastructure as code",
            "deployment",
            "aws",
            "gcp",
            "azure",
        ],
        "exclude": [],
    },
    "sre": {
        "strong_title": [
            "site reliability engineer",
            "site reliability",
            "sre",
            "sre engineer",
            "reliability engineer",
        ],
        "weak_title": [],
        "evidence": [
            "reliability",
            "availability",
            "slo",
            "incident",
            "on-call",
            "monitor",
            "observability",
            "prometheus",
            "grafana",
            "kubernetes",
        ],
        "exclude": [],
    },
    "cloud_infrastructure": {
        "strong_title": [
            "cloud infrastructure engineer",
            "cloud infrastructure",
            "cloud engineer",
            "cloud architect",
            "infrastructure engineer",
            "infrastructure reliability engineer",
        ],
        "weak_title": [
            "systems engineer",
            "platform engineer",
            "infrastructure",
        ],
        "evidence": [
            "aws",
            "gcp",
            "azure",
            "terraform",
            "vpc",
            "networking",
            "linux",
            "virtualization",
            "kubernetes",
            "on-prem",
            "server",
            "infrastructure",
            "cloud",
        ],
        "exclude": [],
    },
    "software_development": {
        "strong_title": [
            "software developer",
            "software engineer",
            "backend developer",
            "back end developer",
            "frontend developer",
            "full stack developer",
            "full stack",
            "python developer",
            "java developer",
            "programmer",
        ],
        "weak_title": [
            "developer",
            "engineer",
        ],
        "evidence": [
            "development",
            "code",
            "coding",
            "python",
            "java",
            "javascript",
            "application",
            "programming",
            "software",
            "rest api",
            "database",
        ],
        "exclude": [],
    },
}

# Focused search terms per family so the discovery query budget can be
# spread across P1 support, P2 QA and P3 development/DevOps instead of
# letting one family dominate.
JOB_FAMILY_QUERY_TERMS = {
    "technical_support": [
        "Technical Support",
        "Technical Support Engineer",
        "Tech Support",
        "Support Engineer",
        "Systems Support Engineer",
        "Software Support",
    ],
    "application_support": [
        "Application Support",
        "Application Support Engineer",
        "Application Operations",
        "App Support",
    ],
    "production_support": [
        "Production Support",
        "Production Support Engineer",
        "Production Operations",
    ],
    "operations_support": [
        "IT Operations",
        "IT Operations Engineer",
        "Operations Engineer",
        "Technical Operations",
        "Cloud Operations",
        "NOC",
        "Monitoring Engineer",
        "Infrastructure Support",
        "System Administrator",
    ],
    "cloud_support": [
        "Cloud Support",
        "Cloud Support Engineer",
        "Cloud Infrastructure Support",
    ],
    "qa_testing": [
        "QA Engineer",
        "QA Analyst",
        "QA Tester",
        "Quality Assurance",
        "Software Test Engineer",
        "Software Tester",
        "Test Engineer",
        "Test Analyst",
        "Automation Tester",
        "QA Automation",
        "SDET",
        "Manual Tester",
        "Quality Engineer",
        "Functional Tester",
    ],
    "devops": [
        "DevOps",
        "DevOps Engineer",
        "Junior DevOps Engineer",
    ],
    "sre": [
        "SRE",
        "Site Reliability",
        "Site Reliability Engineer",
    ],
    "cloud_infrastructure": [
        "Cloud Engineer",
        "Cloud Infrastructure Engineer",
        "Cloud Infrastructure",
        "Infrastructure Engineer",
        "Systems Engineer",
        "Platform Engineer",
    ],
    "software_development": [
        "Software Developer",
        "Python Developer",
        "Java Developer",
    ],
}

LOCATIONS = [
    "Chennai",
    "Bangalore",
    "Hyderabad",
    "Remote",
    "Coimbatore",
]

EXPERIENCE_YEARS = 1.5

# Hard maximum experience requirement.
# Jobs clearly requiring more than 2 years must be rejected.
MAX_JOB_EXPERIENCE_YEARS = 2

EMPLOYMENT_TYPE = "full_time"

# Salary preferences.
MINIMUM_CTC_LPA = 7
TARGET_CTC_LPA = "8-9"