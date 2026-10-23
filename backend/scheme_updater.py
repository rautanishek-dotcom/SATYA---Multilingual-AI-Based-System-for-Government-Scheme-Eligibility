"""SATYA live government-scheme synchronizer.

Only official Indian-government domains are authoritative. Source index pages
are intentionally configurable so deployments can add state portals without
changing individual scheme records.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_NAME = "Satya"
REQUEST_TIMEOUT_SECONDS = int(os.getenv("SATYA_SCHEME_REQUEST_TIMEOUT", "15"))
REQUEST_RETRIES = int(os.getenv("SATYA_SCHEME_REQUEST_RETRIES", "2"))
DEACTIVATE_AFTER_FAILURES = int(os.getenv("SATYA_SCHEME_DEACTIVATE_AFTER_FAILURES", "3"))
IST = ZoneInfo("Asia/Kolkata")
HEADERS = {"User-Agent": "SATYA Scheme Directory/1.0 (official-source verifier)", "Accept-Language": "en-IN,en;q=0.9"}

# ---------------------------------------------------------------------------
# Master State / Union Territory Registry (28 States + 8 UTs)
# ---------------------------------------------------------------------------
INDIAN_STATES = (
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
)

UNION_TERRITORIES = (
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
    "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
)

ALL_STATES_AND_UTS = INDIAN_STATES + UNION_TERRITORIES

# Normalization mapping for state aliases & common variations
_STATE_ALIAS_MAP: dict[str, str] = {
    # Central synonyms
    "all india": "Central",
    "india": "Central",
    "central": "Central",
    "central government": "Central",
    "govt of india": "Central",
    "government of india": "Central",
    "union government": "Central",
    # State synonyms
    "ap": "Andhra Pradesh", "andhra": "Andhra Pradesh",
    "arunachal": "Arunachal Pradesh",
    "up": "Uttar Pradesh", "uttar pradesh": "Uttar Pradesh",
    "uk": "Uttarakhand", "uttaranchal": "Uttarakhand",
    "wb": "West Bengal", "bengal": "West Bengal",
    "mp": "Madhya Pradesh",
    "cg": "Chhattisgarh", "chhatisgarh": "Chhattisgarh",
    "tn": "Tamil Nadu", "tamilnadu": "Tamil Nadu",
    "kl": "Kerala",
    "ka": "Karnataka",
    "mh": "Maharashtra",
    "rj": "Rajasthan",
    "gj": "Gujarat",
    "pb": "Punjab",
    "hr": "Haryana",
    "hp": "Himachal Pradesh",
    "jk": "Jammu and Kashmir", "j&k": "Jammu and Kashmir",
    "dnh": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "a&n": "Andaman and Nicobar Islands",
    "andaman": "Andaman and Nicobar Islands",
    "puducherry": "Puducherry", "pondicherry": "Puducherry",
}

# Add normalized versions of all canonical names
for _st in ALL_STATES_AND_UTS:
    _STATE_ALIAS_MAP[_st.lower()] = _st
    _STATE_ALIAS_MAP[f"government of {_st.lower()}"] = _st
    _STATE_ALIAS_MAP[f"govt. of {_st.lower()}"] = _st
    _STATE_ALIAS_MAP[f"govt of {_st.lower()}"] = _st
    _STATE_ALIAS_MAP[f"{_st.lower()} state"] = _st

def normalize_state_name(raw_state: str | None) -> str:
    """Normalize state string into canonical 'Central', State, or UT name."""
    if not raw_state:
        return "Central"
    cleaned = re.sub(r"\s+", " ", str(raw_state).strip().lower())
    cleaned = re.sub(r"^govt\.?\s+of\s+", "", cleaned)
    cleaned = re.sub(r"\s+state$", "", cleaned)
    if cleaned in _STATE_ALIAS_MAP:
        return _STATE_ALIAS_MAP[cleaned]
    for key, val in _STATE_ALIAS_MAP.items():
        if key == cleaned:
            return val
    # Match against canonical names
    for canonical in ALL_STATES_AND_UTS:
        if canonical.lower() in cleaned or cleaned in canonical.lower():
            return canonical
    return "Central"

DEFAULT_OFFICIAL_SOURCES = (
    "https://www.myscheme.gov.in/search",
    "https://www.india.gov.in/my-government/schemes",
)

OFFICIAL_DOMAIN_SUFFIXES = (".gov.in", ".nic.in", ".ac.in", ".edu.in")
NON_SCHEME_LINK_TEXT = {"home", "login", "register", "contact", "about", "read more", "more", "apply now"}
DATE_PATTERNS = (
    "%d %B %Y", "%d %b %Y", "%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d",
)

# ---------------------------------------------------------------------------
# Negative evidence: pages that are NEVER valid scheme records.
# ---------------------------------------------------------------------------
_EXACT_NEGATIVE_NAMES: frozenset[str] = frozenset({
    "about us", "about", "contact us", "contact",
    "faq", "frequently asked questions", "faqs",
    "accessibility", "accessibility statement",
    "screen reader", "screen reader access",
    "disclaimer", "legal disclaimer",
    "terms & conditions", "terms and conditions", "terms of use",
    "privacy policy", "privacy",
    "sitemap", "site map",
    "dashboard", "login", "register", "sign in", "sign up",
    "home", "feedback", "help", "search",
    "calendar", "content sources", "translation disclaimer",
    "cpgrams", "content", "sources",
    "india portal 2.0 brochure",
    # Generic category pages from portals
    "agriculture, rural & environment", "agriculture rural & environment",
    "benefits & social development", "benefits and social development",
    "business & self-employed", "business and self-employed",
    "education & learning", "education and learning",
    "health & wellness", "health and wellness",
    "housing & local services", "housing and local services",
    "jobs", "social welfare & empowerment", "social welfare and empowerment",
})

_NEGATIVE_NAME_PATTERNS = [
    re.compile(r"^loading\.{0,3}\s*"),        # "Loading..."
    re.compile(r"^ministry\s+of\s+"),          # bare "Ministry of ..."
    re.compile(r"^department\s+of\s+"),        # bare "Department of ..."
    re.compile(r"^ministry\s+of\s+\w+(\s+\w+)?(\s+\w+)?$"),
    re.compile(r"^government\s+of\s+\w+$"),   # "Government of India" / "Government of Karnataka" alone
    re.compile(r"^(state|central|union)\s+(government|ministry)\s*$"),
    re.compile(r"\b(?:brochure|newsletter|annual report|press release)\b$"),
]

_NON_SCHEME_URL_SEGMENTS = frozenset({
    "about", "contact", "faq", "faqs", "accessibility", "accessibility-statement",
    "screen-reader", "disclaimer", "terms", "privacy", "dashboard", "calendar",
    "content-sources", "translation-disclaimer", "login", "register", "search",
    "sitemap", "help", "feedback", "category", "categories",
})

_SCHEME_NAME_MARKERS = re.compile(
    r"\b(?:scheme|yojana|mission|programme|program|initiative|service|benefit|"
    r"pension|scholarship|allowance|insurance|subsidy|connection)\b",
    re.I,
)

_SCHEME_EVIDENCE_PATTERNS = {
    "beneficiary": re.compile(r"\b(?:beneficiar|target group|who can apply|intended for)\b", re.I),
    "benefit": re.compile(r"\b(?:benefit|assistance|subsidy|financial support|grant|pension|insurance)\b", re.I),
    "eligibility": re.compile(r"\b(?:eligibility|eligible|eligibility criteria|income limit|age limit)\b", re.I),
    "application": re.compile(r"\b(?:how to apply|application process|apply online|apply through|registration process)\b", re.I),
}

_POSITIVE_CONTENT_FIELDS = ("target_beneficiaries", "benefits", "eligibility", "steps")


@dataclass
class LinkCheck:
    valid: bool
    final_url: str | None = None
    status_code: int | None = None
    reason: str = ""
    temporary_failure: bool = False
    content: str = ""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def scheme_slug(name: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return value[:120]


def normalised_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def non_scheme_page_reason(name: str, url: str | None = None) -> str | None:
    """Classify navigation, category and organization pages before extraction."""
    cleaned_name = re.sub(r"\s+", " ", (name or "").strip().lower())
    stripped_name = re.sub(r"^loading\.{0,3}\s*", "", cleaned_name).strip()
    if not cleaned_name or cleaned_name in _EXACT_NEGATIVE_NAMES or stripped_name in _EXACT_NEGATIVE_NAMES:
        return "Navigation/category page"
    if cleaned_name.startswith("loading"):
        return "Loading placeholder or category page"
    if cleaned_name.startswith(("ministry of ", "department of ", "government of ", "office of ")):
        return "Organization landing page"
    if any(pattern.search(cleaned_name) for pattern in _NEGATIVE_NAME_PATTERNS):
        return "Navigation, organization, or informational page"

    parsed = urlparse(url or "")
    segments = {segment.lower() for segment in parsed.path.split("/") if segment}
    if segments & _NON_SCHEME_URL_SEGMENTS:
        return "Navigation or portal route"
    return None


def description_relates_to_name(name: str, description: str) -> bool:
    tokens = [
        token for token in re.findall(r"[a-z0-9]{3,}", (name or "").lower())
        if token not in {"scheme", "yojana", "the", "for", "and", "india", "pradhan", "mantri"}
    ]
    text = (description or "").lower()
    if not tokens:
        return False
    return sum(token in text for token in tokens) >= min(2, len(tokens))


def is_official_url(url: str | None) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"}:
        return False
    # Check official domain suffixes or government subdomains
    if any(host.endswith(suffix) for suffix in OFFICIAL_DOMAIN_SUFFIXES):
        return True
    if "gov" in host or "nic" in host or "official" in host:
        return True
    return False


def configured_sources() -> tuple[str, ...]:
    configured = os.getenv("SATYA_SCHEME_SOURCES", "").strip()
    if not configured:
        return DEFAULT_OFFICIAL_SOURCES
    return tuple(item.strip() for item in configured.split(",") if item.strip())


def request_url(url: str) -> LinkCheck:
    last_error = ""
    for attempt in range(REQUEST_RETRIES):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
            final_url = response.url
            if response.status_code >= 500:
                last_error = f"server error {response.status_code}"
                if attempt + 1 < REQUEST_RETRIES:
                    time.sleep(attempt + 1)
                    continue
                return LinkCheck(False, final_url, response.status_code, last_error, temporary_failure=True)
            if response.status_code in {404, 410}:
                return LinkCheck(False, final_url, response.status_code, f"HTTP {response.status_code}")
            if not response.ok:
                return LinkCheck(False, final_url, response.status_code, f"HTTP {response.status_code}")
            return LinkCheck(True, final_url, response.status_code, content=response.text)
        except requests.RequestException as error:
            last_error = type(error).__name__
            if attempt + 1 < REQUEST_RETRIES:
                time.sleep(attempt + 1)
    return LinkCheck(False, reason=last_error or "request failed", temporary_failure=True)


def content_relates_to_scheme(name: str, url: str, html: str) -> bool:
    tokens = [token for token in re.findall(r"[a-z0-9]{3,}", (name or "").lower()) if token not in {"scheme", "yojana", "the", "for", "and"}]
    if not tokens:
        return False
    text = BeautifulSoup(html or "", "html.parser").get_text(" ", strip=True).lower()[:20000]
    haystack = f"{url.lower()} {text}"
    matched = sum(token in haystack for token in tokens)
    return matched >= min(2, len(tokens))


def validate_scheme_link(name: str, url: str | None) -> LinkCheck:
    if not is_official_url(url):
        return LinkCheck(False, reason="not an official Indian government URL")
    result = request_url(url)
    if not result.valid:
        return result
    if not is_official_url(result.final_url):
        return LinkCheck(False, result.final_url, result.status_code, "redirected outside an official domain")
    if not content_relates_to_scheme(name, result.final_url or url or "", result.content):
        return LinkCheck(False, result.final_url, result.status_code, "page is not demonstrably related to the scheme")
    return result


def find_section_text(soup: BeautifulSoup, labels: Iterable[str]) -> str:
    labels = tuple(label.lower() for label in labels)
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b"]):
        title = heading.get_text(" ", strip=True).lower()
        if any(label in title for label in labels):
            parts: list[str] = []
            for sibling in heading.find_all_next(["p", "li"], limit=5):
                text = sibling.get_text(" ", strip=True)
                if text:
                    parts.append(text)
            if parts:
                return " ".join(parts)[:2000]
    return ""


_UNRELATED_APPLICATION_COPY = re.compile(
    r"\b(?:beware of misleading communication|it has been reported to us|"
    r"cyber security measures|comprehensive guidelines for the nation-wide|"
    r"clarification on limitation on amount of gratuity|"
    r"integration of cghs online system with)\b",
    re.I,
)


def is_unrelated_application_copy(text: str | None) -> bool:
    return bool(text and _UNRELATED_APPLICATION_COPY.search(text))


def sanitize_application_steps(text: str | None) -> str:
    normalized = re.sub(r"\s+", " ", text or "").strip()
    if is_unrelated_application_copy(normalized):
        return ""
    return normalized[:2000]


def extract_deadline(text: str, now: datetime | None = None) -> tuple[str | None, str, str | None]:
    now = now or utcnow()
    clean = re.sub(r"\s+", " ", text or " ")
    date_value = r"(?:\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s*,?\s+\d{4}|(?:january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4}|\d{4}-\d{2}-\d{2})"
    trigger_pattern = r"(?i)(?:last date|deadline|apply(?:\s+before|\s+by)?|applications?\s+close(?:\s+on)?)"
    for trigger in re.finditer(trigger_pattern, clean):
        date_match = re.search(date_value, clean[trigger.end():trigger.end() + 80], flags=re.I)
        if not date_match:
            continue
        original = date_match.group(0)
        normalized = re.sub(r"(?<=\d)(?:st|nd|rd|th)\b", "", original, flags=re.I)
        for pattern in DATE_PATTERNS:
            try:
                return datetime.strptime(normalized, pattern).date().isoformat(), "fixed", original
            except ValueError:
                continue
    if re.search(r"(?i)(throughout the year|no last date|open all year|ongoing)", clean):
        return None, "ongoing", None
    return None, "not_specified", None


def is_valid_scheme(candidate: dict[str, Any]) -> tuple[bool, str]:
    """Return whether an official page has enough scheme-specific evidence."""
    name: str = (candidate.get("name") or "").strip()
    page_reason = non_scheme_page_reason(name, candidate.get("official_website") or candidate.get("source_url"))
    if page_reason:
        return False, f"{page_reason}: '{name}'"

    description = (candidate.get("description") or "").strip()
    content_values = " ".join(str(candidate.get(field) or "") for field in _POSITIVE_CONTENT_FIELDS)
    evidence_text = f"{description} {content_values}"
    structured_signals = sum(
        1 for field in _POSITIVE_CONTENT_FIELDS
        if len(str(candidate.get(field) or "").strip()) >= 50
    )
    semantic_signals = sum(bool(pattern.search(evidence_text)) for pattern in _SCHEME_EVIDENCE_PATTERNS.values())
    name_is_scheme_like = bool(_SCHEME_NAME_MARKERS.search(name))
    is_specific = description_relates_to_name(name, evidence_text)

    if structured_signals >= 2 and semantic_signals >= 2:
        return True, f"Valid: {structured_signals} structured and {semantic_signals} semantic signals"
    if structured_signals >= 1 and (name_is_scheme_like or is_specific) and semantic_signals >= 2:
        return True, "Valid: scheme-specific content plus application/benefit evidence"
    if name_is_scheme_like and is_specific and semantic_signals >= 3 and len(description) >= 120:
        return True, "Valid: detailed scheme-specific description"
    return False, (
        f"Insufficient scheme-specific evidence (structured={structured_signals}, "
        f"semantic={semantic_signals}, description={len(description)} chars): '{name}'"
    )


def extract_candidate(name: str, page_url: str, html: str, source_url: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text(" ", strip=True)
    description = ""
    for paragraph in soup.find_all("p"):
        candidate_text = paragraph.get_text(" ", strip=True)
        if len(candidate_text) >= 60:
            description = candidate_text[:1200]
            break
    if not description:
        return None
    application_url = None
    for link in soup.find_all("a", href=True):
        label = link.get_text(" ", strip=True).lower()
        href = urljoin(page_url, link["href"])
        if any(word in label for word in ("apply", "application", "register")) and is_official_url(href):
            application_url = href
            break
    if application_url:
        application_check = validate_scheme_link(name, application_url)
        application_url = application_check.final_url if application_check.valid else None
    deadline, deadline_status, deadline_source_text = extract_deadline(page_text)
    
    # Infer state scope from name, URL, or text
    raw_state = None
    for st in ALL_STATES_AND_UTS:
        if st.lower() in name.lower() or st.lower() in page_url.lower():
            raw_state = st
            break
    canonical_state = normalize_state_name(raw_state)

    return {
        "name": name,
        "description": description,
        "official_website": page_url,
        "official_application_url": application_url,
        "target_beneficiaries": find_section_text(soup, ("beneficiar", "who can apply", "target group")),
        "benefits": find_section_text(soup, ("benefit", "assistance", "financial support")),
        "eligibility": find_section_text(soup, ("eligibility", "eligible")),
        "steps": sanitize_application_steps(find_section_text(soup, ("how to apply", "application process", "apply"))),
        "application_deadline": deadline,
        "deadline_status": deadline_status,
        "deadline_source_text": deadline_source_text,
        "source": "official_government_source",
        "source_url": source_url,
        "state": canonical_state,
        "rules": {},
    }


def discover_from_source(source_url: str) -> list[tuple[dict[str, Any], str]]:
    """Returns list of (candidate_dict, rejection_reason) tuples."""
    source = request_url(source_url)
    if not source.valid or not is_official_url(source.final_url):
        return []
    soup = BeautifulSoup(source.content, "html.parser")
    results: list[tuple[dict[str, Any], str]] = []
    seen: set[str] = set()
    for link in soup.find_all("a", href=True):
        name = link.get_text(" ", strip=True)
        url = urljoin(source.final_url or source_url, link["href"])
        slug = scheme_slug(name)
        if len(name) < 6 or slug in seen or name.lower() in NON_SCHEME_LINK_TEXT or not is_official_url(url):
            continue
        quick_rejection = non_scheme_page_reason(name, url)
        if quick_rejection:
            seen.add(slug)
            results.append((
                {"name": name, "official_website": url, "source_url": source.final_url or source_url},
                quick_rejection,
            ))
            continue
        page = validate_scheme_link(name, url)
        if not page.valid:
            continue
        candidate = extract_candidate(name, page.final_url or url, page.content, source.final_url or source_url)
        if candidate:
            valid, reason = is_valid_scheme(candidate)
            if valid:
                seen.add(slug)
                results.append((candidate, ""))
            else:
                seen.add(slug)
                results.append((candidate, reason))
    return results


def content_hash(document: dict[str, Any]) -> str:
    keys = ("name", "description", "official_website", "official_application_url", "target_beneficiaries", "benefits", "eligibility", "steps", "state", "rules", "application_deadline", "deadline_status")
    payload = {key: document.get(key) for key in keys}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def non_empty_updates(candidate: dict[str, Any], existing: dict[str, Any] | None) -> dict[str, Any]:
    existing = existing or {}
    protected = {"official_website", "official_application_url", "target_beneficiaries", "benefits", "eligibility", "steps", "state", "rules", "application_deadline", "deadline_status"}
    result = dict(existing)
    for key, value in candidate.items():
        if key in {"_id", "first_seen", "verification_failure_count"}:
            continue
        if key in protected and value in (None, "", {}, []):
            if key == "steps" and is_unrelated_application_copy(existing.get("steps")):
                result[key] = ""
            continue
        if key == "state" and value == "Central" and existing.get("state") not in (None, "", "Central", "All India"):
            continue
        result[key] = value
    result["state"] = normalize_state_name(result.get("state"))
    return result


class LiveSchemeSynchronizer:
    def __init__(self, collection, database, sources: Iterable[str] | None = None, dry_run: bool = False):
        self.collection = collection
        self.database = database
        self.sources = tuple(sources or configured_sources())
        self.dry_run = dry_run
        self.stats: dict[str, int] = {
            "sources_checked": 0,
            "candidates_discovered": 0,
            "central_discovered": 0,
            "state_discovered": 0,
            "ut_discovered": 0,
            "valid_schemes": 0,
            "rejected_navigation": 0,
            "rejected_category": 0,
            "rejected_organization": 0,
            "rejected_insufficient": 0,
            "new": 0,
            "updated": 0,
            "unchanged": 0,
            "deactivated": 0,
            "cleanup_deactivated": 0,
            "cleanup_retained": 0,
            "invalid_links_removed": 0,
            "deadlines_updated": 0,
            "duplicates_skipped": 0,
        }
        self._would_deactivate: list[str] = []
        self._would_reject: list[tuple[str, str]] = []

    def ensure_indexes(self) -> None:
        self.collection.create_index("scheme_slug", unique=True, sparse=True)
        self.collection.create_index([("status", 1), ("last_verified", -1)])
        self.collection.create_index("state")

    def _find_existing(self, candidate: dict[str, Any]) -> dict[str, Any] | None:
        slug = scheme_slug(candidate["name"])
        query = {"$or": [{"scheme_slug": slug}, {"official_website": candidate.get("official_website")}, {"official_application_url": candidate.get("official_application_url")} ]}
        query["$or"] = [item for item in query["$or"] if list(item.values())[0]] or [{"scheme_slug": slug}]
        found = self.collection.find_one(query)
        if found:
            return found
        normalized = normalised_name(candidate["name"])
        for document in list(self.collection.find({"name": {"$regex": re.escape(candidate["name"]), "$options": "i"}}))[:5]:
            if normalised_name(document.get("name", "")) == normalized:
                return document
        return None

    def _classify_rejection(self, reason: str) -> None:
        r = reason.lower()
        if "organization" in r or "ministry" in r or "department" in r:
            self.stats["rejected_organization"] += 1
        elif "navigation" in r or "category" in r or "loading" in r or "portal" in r:
            self.stats["rejected_navigation"] += 1
        elif "insufficient" in r or "no descriptive" in r:
            self.stats["rejected_insufficient"] += 1
        else:
            self.stats["rejected_category"] += 1

    def save_candidate(self, candidate: dict[str, Any]) -> None:
        existing = self._find_existing(candidate)
        merged = non_empty_updates(candidate, existing)
        merged["scheme_slug"] = (existing or {}).get("scheme_slug") or scheme_slug(candidate["name"])
        merged["state"] = normalize_state_name(merged.get("state"))
        merged["status"] = "active"
        merged["is_active"] = True
        merged["official_website_verified"] = True
        merged["official_application_url_verified"] = bool(merged.get("official_application_url"))
        merged["last_verified"] = utcnow()
        merged["last_updated"] = utcnow()
        merged["verification_failure_count"] = 0
        merged["content_hash"] = content_hash(merged)

        if existing and existing.get("content_hash") == merged["content_hash"] and existing.get("status") == "active":
            if not self.dry_run:
                self.collection.update_one({"_id": existing["_id"]}, {"$set": {"last_verified": merged["last_verified"], "state": merged["state"], "verification_failure_count": 0}})
            self.stats["unchanged"] += 1
            return

        if not existing:
            if not self.dry_run:
                merged["first_seen"] = utcnow()
                self.collection.insert_one(merged)
            self.stats["new"] += 1
        else:
            previous_deadline = existing.get("application_deadline")
            if not self.dry_run:
                self.collection.update_one({"_id": existing["_id"]}, {"$set": merged})
            self.stats["updated"] += 1
            if merged.get("application_deadline") and merged.get("application_deadline") != previous_deadline:
                self.stats["deadlines_updated"] += 1

    def clean_bad_existing_records(self) -> None:
        """Soft-deactivate existing ACTIVE records that are clearly NOT schemes."""
        print("\n-- Cleaning invalid records from existing active dataset --")
        for existing in self.collection.find({"status": {"$in": ["active", None]}}):
            name = existing.get("name", "")
            reason = non_scheme_page_reason(
                name,
                existing.get("official_website") or existing.get("source_url"),
            )
            if reason:
                self._would_deactivate.append(f"  - {name!r:50}  Reason: {reason}")
                if not self.dry_run:
                    self.collection.update_one(
                        {"_id": existing["_id"]},
                        {"$set": {
                            "status": "inactive",
                            "is_active": False,
                            "deactivated_at": utcnow(),
                            "deactivation_reason": reason,
                        }},
                    )
                self.stats["cleanup_deactivated"] += 1
            else:
                # Also normalize state field for existing valid records
                current_state = existing.get("state")
                norm_state = normalize_state_name(current_state)
                if current_state != norm_state and not self.dry_run:
                    self.collection.update_one({"_id": existing["_id"]}, {"$set": {"state": norm_state}})
                self.stats["cleanup_retained"] += 1

    def reconcile_existing(self, discovered_urls: set[str]) -> None:
        for existing in self.collection.find({"status": "active", "is_active": True}):
            url = existing.get("official_website") or existing.get("official_application_url")
            application_url = existing.get("official_application_url")
            if application_url:
                application_check = validate_scheme_link(existing.get("name", ""), application_url)
                if application_check.valid:
                    if not self.dry_run:
                        self.collection.update_one(
                            {"_id": existing["_id"]},
                            {"$set": {"official_application_url": application_check.final_url or application_url, "official_application_url_verified": True}},
                        )
                elif not application_check.temporary_failure:
                    if not self.dry_run:
                        self.collection.update_one(
                            {"_id": existing["_id"]},
                            {"$unset": {"official_application_url": ""}, "$set": {"official_application_url_verified": False, "last_verification_error": application_check.reason}},
                        )
                    self.stats["invalid_links_removed"] += 1
            if not url or url in discovered_urls:
                continue
            check = validate_scheme_link(existing.get("name", ""), url)
            if check.valid:
                update = {"last_verified": utcnow(), "verification_failure_count": 0, "status": "active", "is_active": True, "official_website_verified": True}
                if check.final_url and check.final_url != url:
                    update["official_website"] = check.final_url
                if not self.dry_run:
                    self.collection.update_one({"_id": existing["_id"]}, {"$set": update})
                continue
            if check.temporary_failure:
                continue
            failures = int(existing.get("verification_failure_count", 0) or 0) + 1
            update = {"verification_failure_count": failures, "last_verification_error": check.reason, "last_verified": utcnow()}
            if failures >= DEACTIVATE_AFTER_FAILURES:
                update.update({"status": "unavailable", "is_active": False, "deactivated_at": utcnow()})
                self.stats["deactivated"] += 1
            if not self.dry_run:
                self.collection.update_one({"_id": existing["_id"]}, {"$set": update})

    def run(self) -> dict[str, int]:
        self.ensure_indexes()
        self.clean_bad_existing_records()
        discovered_urls: set[str] = set()
        seen_slugs: set[str] = set()

        # Ingest curated official seed dataset (> 200 authentic Central + State schemes)
        try:
            from backend.seed_schemes import get_all_seed_schemes
            seed_candidates = get_all_seed_schemes()
        except ImportError:
            try:
                from seed_schemes import get_all_seed_schemes
                seed_candidates = get_all_seed_schemes()
            except ImportError:
                seed_candidates = []

        for candidate in seed_candidates:
            self.stats["candidates_discovered"] += 1
            slug = scheme_slug(candidate["name"])
            st = normalize_state_name(candidate.get("state"))
            if st == "Central":
                self.stats["central_discovered"] += 1
            elif st in UNION_TERRITORIES:
                self.stats["ut_discovered"] += 1
            else:
                self.stats["state_discovered"] += 1

            if slug in seen_slugs:
                self.stats["duplicates_skipped"] += 1
                continue
            seen_slugs.add(slug)
            self.stats["valid_schemes"] += 1
            if candidate.get("official_website"):
                discovered_urls.add(candidate["official_website"])
            self.save_candidate(candidate)

        for source_url in self.sources:
            self.stats["sources_checked"] += 1
            try:
                results = discover_from_source(source_url)
            except Exception:
                results = []
            for candidate, rejection_reason in results:
                self.stats["candidates_discovered"] += 1
                slug = scheme_slug(candidate["name"])
                
                # Classify Central vs State vs UT
                st = normalize_state_name(candidate.get("state"))
                if st == "Central":
                    self.stats["central_discovered"] += 1
                elif st in UNION_TERRITORIES:
                    self.stats["ut_discovered"] += 1
                else:
                    self.stats["state_discovered"] += 1

                if rejection_reason:
                    self._classify_rejection(rejection_reason)
                    self._would_reject.append((candidate["name"], rejection_reason))
                    continue
                if slug in seen_slugs:
                    self.stats["duplicates_skipped"] += 1
                    continue
                seen_slugs.add(slug)
                self.stats["valid_schemes"] += 1
                discovered_urls.add(candidate["official_website"])
                self.save_candidate(candidate)

        self.reconcile_existing(discovered_urls)
        if not self.dry_run:
            self.database["scrape_logs"].insert_one({
                "run_at": utcnow(),
                "sources": list(self.sources),
                "stats": self.stats,
                "mode": "sync-live",
            })
        return self.stats


def print_summary(stats: dict[str, int], collection, synchronizer: LiveSchemeSynchronizer, dry_run: bool = False) -> None:
    mode = "DRY RUN" if dry_run else "LIVE SYNC"
    print(f"\nSATYA SCHEME UPDATER - {mode}\n" + "=" * 45)
    print(f"Started: {datetime.now(IST).strftime('%Y-%m-%d %H:%M IST')}")
    print("")
    labels = [
        ("Sources checked",              "sources_checked"),
        ("Candidates discovered",         "candidates_discovered"),
        ("  - Central candidates",        "central_discovered"),
        ("  - State candidates",          "state_discovered"),
        ("  - UT candidates",             "ut_discovered"),
        ("Valid schemes/services",        "valid_schemes"),
        ("Rejected: navigation/portal",   "rejected_navigation"),
        ("Rejected: category pages",      "rejected_category"),
        ("Rejected: organization pages",  "rejected_organization"),
        ("Rejected: insufficient content","rejected_insufficient"),
        ("New schemes",                   "new"),
        ("Updated schemes",               "updated"),
        ("Unchanged schemes",             "unchanged"),
        ("Deactivated (link failure)",    "deactivated"),
        ("Cleaned up (invalid records)",  "cleanup_deactivated"),
        ("Retained (legitimate)",         "cleanup_retained"),
        ("Invalid links removed",         "invalid_links_removed"),
        ("Deadlines updated",             "deadlines_updated"),
        ("Duplicates skipped",            "duplicates_skipped"),
    ]
    for label, key in labels:
        print(f"  {label:<38} {stats.get(key, 0)}")

    if dry_run:
        print("\n-- Records that would be deactivated (cleanup): --")
        if synchronizer._would_deactivate:
            for line in synchronizer._would_deactivate:
                print(line)
        else:
            print("  (none - existing records all passed validation)")
        print("\n-- Candidates that would be rejected (new discovery): --")
        if synchronizer._would_reject:
            for name, reason in synchronizer._would_reject[:30]:
                print(f"  - {name!r:50}  {reason}")
            if len(synchronizer._would_reject) > 30:
                print(f"  ... and {len(synchronizer._would_reject) - 30} more")
        else:
            print("  (none)")
        active = collection.count_documents({"status": "active", "is_active": True})
        central_cnt = collection.count_documents({"status": "active", "is_active": True, "state": {"$in": ["Central", "All India"]}})
        state_cnt = collection.count_documents({"status": "active", "is_active": True, "state": {"$in": list(INDIAN_STATES)}})
        ut_cnt = collection.count_documents({"status": "active", "is_active": True, "state": {"$in": list(UNION_TERRITORIES)}})
        print(f"\n  Central active schemes: {central_cnt}")
        print(f"  State active schemes:   {state_cnt}")
        print(f"  UT active schemes:      {ut_cnt}")
        print(f"  Total active schemes:   {active}")
        print("  NOTE: This was a dry run. No changes were made to MongoDB.")
    else:
        active = collection.count_documents({"status": "active", "is_active": True})
        central_cnt = collection.count_documents({"status": "active", "is_active": True, "state": {"$in": ["Central", "All India"]}})
        state_cnt = collection.count_documents({"status": "active", "is_active": True, "state": {"$in": list(INDIAN_STATES)}})
        ut_cnt = collection.count_documents({"status": "active", "is_active": True, "state": {"$in": list(UNION_TERRITORIES)}})
        print(f"\n  Central active schemes: {central_cnt}")
        print(f"  State active schemes:   {state_cnt}")
        print(f"  UT active schemes:      {ut_cnt}")
        print(f"  Total active schemes:   {active}")
        print("\n  Completed successfully.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Synchronize SATYA schemes from official government sources.")
    parser.add_argument("--sync-live", action="store_true", help="run the official live synchronization")
    parser.add_argument("--dry-run", action="store_true", help="report what would change without modifying MongoDB")
    args = parser.parse_args()
    if not args.sync_live:
        parser.error("use --sync-live (optionally with --dry-run)")
    dry_run = args.dry_run
    try:
        client = MongoClient(os.getenv("MONGO_URI", "mongodb://localhost:27017/"), serverSelectionTimeoutMS=8000)
        client.admin.command("ping")
        database = client[DB_NAME]
        synchronizer = LiveSchemeSynchronizer(database["schemes"], database, dry_run=dry_run)
        stats = synchronizer.run()
        print_summary(stats, database["schemes"], synchronizer, dry_run=dry_run)
        client.close()
        return 0
    except PyMongoError as error:
        print(f"Sync failed: MongoDB unavailable ({error})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
