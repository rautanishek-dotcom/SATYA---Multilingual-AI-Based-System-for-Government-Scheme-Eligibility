import re
import logging
from typing import Dict, Any, List
from vault.layout_parser import LayoutParser
from vault.document_classifier import DocumentClassifier

logger = logging.getLogger(__name__)

class FieldExtractor:
    """
    Multi-strategy field extractor. Uses Regex, Keyword Anchors, Neighbor Analysis,
    Spatial Position, and Language Patterns.
    """

    @staticmethod
    def _extract_label_value(text: str, labels: List[str]) -> str:
        stop_patterns = [
            r"\bfather\b",
            r"\bdob\b",
            r"\bdate of birth\b",
            r"\bpan\b",
            r"\bpassport no\b",
            r"\bgender\b",
            r"\baddress\b",
            r"\bissue date\b",
            r"\bexpiry date\b",
            r"\bplace of issue\b",
        ]
        for label in labels:
            match = re.search(rf"\b{re.escape(label)}\b\s*[:\-]?\s*(.+)", text, flags=re.IGNORECASE)
            if match:
                value = re.sub(r"\s+", " ", match.group(1)).strip(" ,;:-")
                for pattern in stop_patterns:
                    split_value = re.split(pattern, value, flags=re.IGNORECASE)[0].strip(" ,;:-")
                    if split_value:
                        value = split_value
                        break
                return value
        return ""

    @staticmethod
    def _extract_name_candidates(full_text: str) -> List[str]:
        candidates = []
        for pattern in [
            r"\bname\s*[:\-]?\s*([A-Z][A-Za-z .'-]{2,})",
            r"\bholder name\s*[:\-]?\s*([A-Z][A-Za-z .'-]{2,})",
            r"\bapplicant name\s*[:\-]?\s*([A-Z][A-Za-z .'-]{2,})",
            r"\bname\s*[:\-]?\s*([A-Z][A-Z .'-]{2,})",
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})\s*(?:\d{4}[-/]\d{2}[-/]\d{2}|male|female|gender|dob)",
        ]:
            for match in re.finditer(pattern, full_text, flags=re.IGNORECASE):
                candidate = match.group(1).strip() if match.lastindex else match.group(0).strip()
                if candidate:
                    candidates.append(candidate)
        return candidates

    @staticmethod
    def extract_fields(ocr_result: Dict[str, Any]) -> Dict[str, Any]:
        full_text = ocr_result.get("full_text", "")
        graph = LayoutParser.build_spatial_graph(ocr_result.get("words", []))

        classification = DocumentClassifier.classify_by_text(full_text)
        doc_type = classification["document_type"]

        fields = {}
        fields["document_type"] = {
            "value": classification["document_label"],
            "confidence": classification["probability"],
            "strategy": "ocr_text_classifier",
        }

        dob_match = re.search(r'\b(\d{2}(?:[/-]\d{2}[/-]\d{4}))\b', full_text)
        if dob_match:
            fields["dob"] = {"value": dob_match.group(1), "confidence": 98.0, "strategy": "regex"}
        else:
            yob_anchor = LayoutParser.find_keyword_anchor(graph, ["yob", "year of birth"], search_direction="right")
            if yob_anchor:
                year_match = re.search(r'\b(19|20)\d{2}\b', yob_anchor["value"])
                if year_match:
                    fields["dob"] = {"value": year_match.group(0), "confidence": 85.0, "strategy": "keyword_anchor_year"}

        gender_match = re.search(r'\b(male|female|transgender|m|f|t)\b', full_text, re.IGNORECASE)
        if gender_match:
            val = gender_match.group(1).title()
            if val == "M": val = "Male"
            elif val == "F": val = "Female"
            fields["gender"] = {"value": val, "confidence": 99.0, "strategy": "regex_pattern"}

        if doc_type == "aadhaar":
            uid_match = re.search(r'\b([2-9]{1}[0-9]{3}\s?[0-9]{4}\s?[0-9]{4})\b', full_text)
            if uid_match:
                fields["document_number"] = {"value": uid_match.group(1).replace(" ", ""), "confidence": 99.0, "strategy": "regex_aadhaar"}

            name_value = FieldExtractor._extract_label_value(full_text, ["name", "holder name", "applicant name"])
            if not name_value:
                name_value = FieldExtractor._extract_label_value(full_text, ["name:"])
            if name_value:
                fields["name"] = {"value": name_value, "confidence": 88.0, "strategy": "label_value"}

        elif doc_type == "pan":
            pan_match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', full_text)
            if pan_match:
                fields["document_number"] = {"value": pan_match.group(1), "confidence": 99.0, "strategy": "regex_pan"}

            name_value = FieldExtractor._extract_label_value(full_text, ["name"])
            if not name_value:
                for candidate in FieldExtractor._extract_name_candidates(full_text):
                    if candidate and len(candidate.split()) >= 2:
                        name_value = candidate
                        break
            if name_value:
                fields["name"] = {"value": name_value, "confidence": 90.0, "strategy": "label_value"}

        elif doc_type == "passport":
            passport_match = re.search(r'\b(?:([A-Z][0-9]{7})|([0-9]{8}))\b', full_text)
            if passport_match:
                fields["document_number"] = {"value": (passport_match.group(1) or passport_match.group(2)).upper(), "confidence": 99.0, "strategy": "regex_passport"}

            surname = FieldExtractor._extract_label_value(full_text, ["surname"])
            given = FieldExtractor._extract_label_value(full_text, ["given names", "given name"])
            if surname or given:
                full_name = " ".join([part for part in [given, surname] if part]).strip()
                fields["name"] = {"value": full_name, "confidence": 90.0, "strategy": "label_value"}

        if "name" not in fields:
            name_candidates = FieldExtractor._extract_name_candidates(full_text)
            filtered_candidates = []
            for candidate in name_candidates:
                cleaned = re.sub(r"\s+", " ", candidate).strip()
                if len(cleaned.split()) < 2:
                    continue
                if any(token in cleaned.lower() for token in ["date of birth", "gender", "passport no", "place of issue", "issue date", "expiry date"]):
                    continue
                filtered_candidates.append(cleaned)
            if filtered_candidates:
                fields["name"] = {"value": filtered_candidates[0], "confidence": 75.0, "strategy": "fallback_name"}

        total_conf = sum([f.get("confidence", 0) for f in fields.values()])
        overall = round(total_conf / len(fields), 2) if fields else 0.0

        return {
            "document_type": doc_type,
            "fields": fields,
            "overall_confidence": overall,
            "layout_graph": graph,
        }
