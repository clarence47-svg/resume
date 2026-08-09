import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from job_search.models import JobPlatform, JobPosting

TRACKING_QUERY_KEYS = {
    "from",
    "ref",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def canonicalize_url(url: str) -> str:
    value = url.strip()
    if not value:
        return ""
    parts = urlsplit(value)
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parts.query, keep_blank_values=False)
            if key.casefold() not in TRACKING_QUERY_KEYS
        )
    )
    path = re.sub(r"/{2,}", "/", parts.path).rstrip("/") or "/"
    return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, query, ""))


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def content_fingerprint(company: str, title: str, location: str, jd_text: str) -> str:
    material = "\n".join(
        normalize_text(item).casefold() for item in (company, title, location, jd_text)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def detect_platform(url: str) -> JobPlatform:
    host = urlsplit(url).netloc.casefold()
    if "zhipin.com" in host:
        return JobPlatform.BOSS
    if "greenhouse.io" in host:
        return JobPlatform.GREENHOUSE
    if "lever.co" in host:
        return JobPlatform.LEVER
    if "ashbyhq.com" in host:
        return JobPlatform.ASHBY
    if host:
        return JobPlatform.OFFICIAL
    return JobPlatform.MANUAL


def normalize_job(job: JobPosting) -> JobPosting:
    job.company = normalize_text(job.company)
    job.title = normalize_text(job.title)
    job.location = normalize_text(job.location)
    job.salary_text = normalize_text(job.salary_text)
    job.jd_text = normalize_text(job.jd_text)
    job.source_url = job.source_url.strip()
    job.canonical_url = canonicalize_url(job.canonical_url or job.source_url)
    if job.platform == JobPlatform.MANUAL and job.canonical_url:
        job.platform = detect_platform(job.canonical_url)
    job.content_hash = content_fingerprint(
        job.company,
        job.title,
        job.location,
        job.jd_text,
    )
    return job
