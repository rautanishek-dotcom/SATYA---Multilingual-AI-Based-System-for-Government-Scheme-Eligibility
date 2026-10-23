import os
import sys
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from routes.schemes import deadline_alert_metadata, calculate_eligible_schemes_internal
from scheme_updater import (
    LinkCheck,
    LiveSchemeSynchronizer,
    content_relates_to_scheme,
    extract_deadline,
    is_valid_scheme,
    is_unrelated_application_copy,
    non_empty_updates,
    non_scheme_page_reason,
    sanitize_application_steps,
    validate_scheme_link,
)


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = documents or []

    def find_one(self, query, *args, **kwargs):
        if "_id" in query:
            return next((item for item in self.documents if item.get("_id") == query["_id"]), None)
        for item in self.documents:
            for possibility in query.get("$or", []):
                if all(item.get(key) == value for key, value in possibility.items()):
                    return item
        return None

    def find(self, query=None, *args, **kwargs):
        query = query or {}
        if query.get("status") == "active" and query.get("is_active") is True:
            return [item for item in self.documents if item.get("status") == "active" and item.get("is_active") is True]
        if "status" in query and isinstance(query["status"], dict):
            values = query["status"].get("$in", [])
            return [item for item in self.documents if item.get("status") in values]
        return list(self.documents)

    def insert_one(self, document):
        document = dict(document)
        document.setdefault("_id", len(self.documents) + 1)
        self.documents.append(document)

    def update_one(self, query, update):
        document = self.find_one(query)
        if document:
            document.update(update.get("$set", {}))
            for key in update.get("$unset", {}):
                document.pop(key, None)

    def create_index(self, *args, **kwargs):
        return None


class FakeDatabase(dict):
    def __getitem__(self, key):
        if key not in self:
            self[key] = FakeCollection()
        return dict.__getitem__(self, key)


class FakeResponse:
    def __init__(self, status_code=200, url="https://example.gov.in/scheme", text="Example Scheme application details"):
        self.status_code = status_code
        self.url = url
        self.text = text
        self.ok = status_code < 400


class LiveSchemeSyncTests(unittest.TestCase):
    def test_deadline_extraction_and_normalization(self):
        deadline, status, source = extract_deadline("Applications close on 31 August 2026.")
        self.assertEqual((deadline, status, source), ("2026-08-31", "fixed", "31 August 2026"))
        self.assertEqual(extract_deadline("Registration remains open throughout the year.")[:2], (None, "ongoing"))
        self.assertEqual(extract_deadline("Eligibility details are published online.")[:2], (None, "not_specified"))

    def test_deadline_alert_levels(self):
        now = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        self.assertEqual(deadline_alert_metadata(now.isoformat())["level"], "today")
        self.assertEqual(deadline_alert_metadata((now + timedelta(days=30)).isoformat())["level"], "upcoming")
        self.assertEqual(deadline_alert_metadata((now + timedelta(days=15)).isoformat())["level"], "approaching")
        self.assertEqual(deadline_alert_metadata((now + timedelta(days=7)).isoformat())["level"], "apply_soon")
        self.assertEqual(deadline_alert_metadata((now + timedelta(days=1)).isoformat())["level"], "urgent")
        self.assertEqual(deadline_alert_metadata("2000-01-01")["level"], "expired")

    def test_never_replaces_verified_values_with_empty_extraction(self):
        existing = {"application_deadline": "2026-10-15", "benefits": "Verified benefit", "rules": {"min_age": 18}}
        merged = non_empty_updates({"application_deadline": None, "benefits": "", "rules": {}}, existing)
        self.assertEqual(merged["application_deadline"], "2026-10-15")
        self.assertEqual(merged["benefits"], "Verified benefit")
        self.assertEqual(merged["rules"], {"min_age": 18})

    def test_scraped_notices_are_not_used_as_application_steps(self):
        bad_copy = "Integration of CGHS Online System with Bhavishya Portal. Cyber Security Measures for Pensioners."
        valid_steps = "1. Register on the official portal. 2. Submit the application and track its status."
        self.assertTrue(is_unrelated_application_copy(bad_copy))
        self.assertEqual(sanitize_application_steps(bad_copy), "")
        self.assertEqual(sanitize_application_steps(valid_steps), valid_steps)
        merged = non_empty_updates({"steps": ""}, {"steps": bad_copy})
        self.assertEqual(merged["steps"], "")

    def test_link_validation_requires_official_relevant_content(self):
        with patch("scheme_updater.requests.get", return_value=FakeResponse(text="PM Kisan Scheme benefits and application")):
            self.assertTrue(validate_scheme_link("PM Kisan Scheme", "https://pmkisan.gov.in/register").valid)
        with patch("scheme_updater.requests.get", return_value=FakeResponse(status_code=404)):
            self.assertFalse(validate_scheme_link("PM Kisan Scheme", "https://pmkisan.gov.in/old").valid)
        with patch("scheme_updater.requests.get", side_effect=requests.RequestException("network unavailable")):
            self.assertTrue(validate_scheme_link("PM Kisan Scheme", "https://pmkisan.gov.in/old").temporary_failure)
        self.assertFalse(content_relates_to_scheme("PM Kisan", "https://india.gov.in", "Government of India home page"))

    def test_idempotent_new_then_unchanged_sync(self):
        collection, database = FakeCollection(), FakeDatabase()
        synchronizer = LiveSchemeSynchronizer(collection, database, sources=[])
        candidate = {"name": "Example Scheme", "description": "Official scheme information for applicants.", "official_website": "https://example.gov.in/scheme", "source": "official_government_source", "source_url": "https://example.gov.in", "rules": {}}
        synchronizer.save_candidate(candidate)
        synchronizer.save_candidate(candidate)
        self.assertEqual(len(collection.documents), 1)
        self.assertEqual(synchronizer.stats["new"], 1)
        self.assertEqual(synchronizer.stats["unchanged"], 1)

    def test_portal_ministry_and_category_pages_are_not_schemes(self):
        portal_content = {
            "description": "This government platform provides search and discovery for government schemes and services.",
            "eligibility": "You can check your eligibility for government schemes through a number of filters and personal attributes.",
            "steps": "Use the search page to find programmes and apply through the listed links.",
        }
        for name, url in (
            ("About Us", "https://www.myscheme.gov.in/about"),
            ("Ministry of Education", "https://www.myscheme.gov.in/ministry/education"),
            ("Loading... Health & Wellness", "https://www.myscheme.gov.in/search"),
        ):
            valid, reason = is_valid_scheme({"name": name, "official_website": url, **portal_content})
            self.assertFalse(valid, name)
            self.assertTrue(reason)
        self.assertIsNotNone(non_scheme_page_reason("Terms & Conditions", "https://www.myscheme.gov.in/terms"))

    def test_real_scheme_requires_specific_benefit_eligibility_and_application_evidence(self):
        candidate = {
            "name": "Pradhan Mantri Ujjwala Yojana",
            "official_website": "https://www.pmuy.gov.in/ujjwala2.html",
            "description": "Pradhan Mantri Ujjwala Yojana provides a deposit-free LPG connection to eligible adult women from poor households.",
            "target_beneficiaries": "Eligible adult women from poor households who do not already have an LPG connection.",
            "benefits": "A deposit-free LPG connection and financial assistance for the first refill and stove.",
            "eligibility": "Applicants must be adult women from eligible households and meet the documented programme conditions.",
            "steps": "Apply through an authorised distributor with the required documents and application form.",
        }
        self.assertTrue(is_valid_scheme(candidate)[0])

    def test_cleanup_soft_deactivates_only_obvious_non_scheme_active_records(self):
        collection = FakeCollection([
            {"_id": "about", "name": "About Us", "status": "active", "is_active": True},
            {"_id": "scheme", "name": "BHAVISHYA - Pension Sanction and Payment Tracking System", "status": "active", "is_active": True},
            {"_id": "legacy", "name": "Legacy record", "status": None, "is_active": False},
        ])
        synchronizer = LiveSchemeSynchronizer(collection, FakeDatabase(), sources=[])
        synchronizer.clean_bad_existing_records()
        self.assertEqual(collection.find_one({"_id": "about"})["status"], "inactive")
        self.assertTrue(collection.find_one({"_id": "scheme"})["is_active"])
        self.assertIsNone(collection.find_one({"_id": "legacy"})["status"])


class EligibilityIdentityTests(unittest.TestCase):
    def test_verified_caste_overrides_manual_category_and_active_only(self):
        schemes = FakeCollection([
            {"_id": "a", "name": "OBC benefit", "status": "active", "is_active": True, "state": "All India", "rules": {"allowed_categories": ["obc"]}},
            {"_id": "b", "name": "Inactive", "status": "inactive", "is_active": False, "state": "All India", "rules": {"allowed_categories": ["all"]}},
        ])
        user = {"_id": "64b64c6d31ad5a862e468abc", "caste_locked": True, "caste_identity_profile": {"category": "OBC"}}
        db = type("Database", (), {"users": FakeCollection([user]), "schemes": schemes})()
        result = calculate_eligible_schemes_internal({"user_id": user["_id"], "age": 30, "income": 100000, "state": "Karnataka", "category": "General"}, db)
        self.assertEqual([item["name"] for item in result["eligible"]], ["OBC benefit"])

    def test_age_income_state_and_unverified_category_mismatches(self):
        schemes = FakeCollection([
            {"_id": "age", "name": "Age scheme", "status": "active", "is_active": True, "state": "All India", "rules": {"min_age": 25}},
            {"_id": "income", "name": "Income scheme", "status": "active", "is_active": True, "state": "All India", "rules": {"max_income": 100000}},
            {"_id": "state", "name": "State scheme", "status": "active", "is_active": True, "state": "Karnataka", "rules": {}},
            {"_id": "category", "name": "Category scheme", "status": "active", "is_active": True, "state": "All India", "rules": {"allowed_categories": ["sc"]}},
        ])
        user = {"_id": "64b64c6d31ad5a862e468abd", "caste_locked": False}
        db = type("Database", (), {"users": FakeCollection([user]), "schemes": schemes})()
        result = calculate_eligible_schemes_internal({"user_id": user["_id"], "age": 20, "income": 200000, "state": "Kerala", "category": "General"}, db)
        reasons = {item["name"]: item["reasons"] for item in result["eligible"] + result["ineligible"]}
        self.assertTrue(any(reason.startswith("AgeTooLow") for reason in reasons["Age scheme"]))
        self.assertTrue(any(reason.startswith("IncomeTooHigh") for reason in reasons["Income scheme"]))
        self.assertTrue(any(reason.startswith("StateMismatch") for reason in reasons["State scheme"]))
        self.assertTrue(any(reason.startswith("CategoryMismatch") for reason in reasons["Category scheme"]))


if __name__ == "__main__":
    unittest.main()
