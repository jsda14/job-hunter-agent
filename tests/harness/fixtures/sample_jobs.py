from datetime import datetime, timezone

SAMPLE_JOB_DICT = {
    "platform": "lever",
    "external_id": "abc-123-xyz",
    "title": "Senior Python Backend Engineer",
    "company": "Fintech Solutions",
    "url": "https://jobs.lever.co/fintech/abc-123-xyz",
    "location": "Remote - Colombia",
    "raw_description": "We are seeking a Senior Python Engineer with FastAPI and clean architecture experience.",
    "posted_at": datetime.now(timezone.utc),
}