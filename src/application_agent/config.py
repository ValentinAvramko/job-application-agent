"""Static project configuration used by the public agent."""

ROLE_RESUMES = ("CIO", "CTO", "HoE", "HoD", "EM")
CONTACT_REGIONS = ("RU", "KZ", "EU")
WORKFLOW_CATALOG = (
    "ingest-vacancy",
    "analyze-vacancy",
    "prepare-screening",
    "intake-adoptions",
    "rebuild-master",
    "rebuild-role-resume",
    "build-linkedin",
    "export-resume-pdf",
)
