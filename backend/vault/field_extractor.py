import re
import logging
from typing import Dict, Any, List, Tuple, Optional
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
    def _extract_name_advanced(full_text: str, doc_type: str = "") -> Tuple[Optional[str], str, float]:
        """
        Multi-strategy Name Extraction without assuming labels.
        Generates candidates, filters invalid ones, ranks them, and returns highest score.
        """
        candidates: List[Dict[str, Any]] = []
        lines = [line.strip() for line in full_text.split('\n') if line.strip()]

        forbidden_exact = {
            "dob", "date of birth", "gender", "male", "female", 
            "aadhaar", "uidai", "government of india", "address", 
            "mobile", "phone", "qr", "vid"
        }
        forbidden_regex = [
            r"\b\d{10}\b",                   # Phone
            r"\b\d{12}\b",                   # Aadhaar
            r"\b[A-Z]{5}\d{4}[A-Z]\b",       # PAN
            r"\b\d{2,4}[/\-]\d{2}[/\-]\d{2,4}\b" # Date (DD/MM/YYYY or YYYY-MM-DD)
        ]

        def clean_field_boundary(cand_str: str) -> str:
            # Look for field boundaries like DOB, Gender on the same line
            split_val = re.split(r'\b(dob|date of birth|gender|male|female)\b', cand_str, flags=re.IGNORECASE)[0]
            # Replace excessive spaces
            split_val = re.sub(r"\s+", " ", split_val)
            return split_val.strip(" ,;:-|")

        def is_valid_name(cand: str) -> bool:
            c = cand.lower().strip()
            if len(c) < 2 or len(c) > 50: return False
            if bool(re.search(r'\d', c)): return False
            if c in forbidden_exact: return False
            for pat in forbidden_regex:
                if re.search(pat, c, re.IGNORECASE): return False
            # Check substrings
            if any(f in c for f in forbidden_exact if len(f) > 3): return False
            
            # Additional boilerplate checks
            tokens = c.split()
            if any(t in {"government", "india", "unique", "identification", "authority", "father's", "pan"} for t in tokens):
                return False
            return True

        # STRATEGY A: Label-Based (Contextual proximity)
        # Handle explicitly labelled names, allowing OCR variations
        for i, line in enumerate(lines):
            # Make sure it's not a father's name
            m = re.search(r'(?<!father\'s\s)(?<!father\s)\b(name|naam|nane|nome|na me|holder name|applicant name)\b\s*[:\-]?\s*(.*)', line, re.IGNORECASE)
            if m:
                val = m.group(2).strip()
                if val:
                    val = clean_field_boundary(val)
                    if is_valid_name(val):
                        candidates.append({"value": val, "strategy": "label_context_same_line", "score": 95})
                else:
                    # Look at next line
                    if i + 1 < len(lines):
                        nxt = clean_field_boundary(lines[i+1])
                        if is_valid_name(nxt):
                            candidates.append({"value": nxt, "strategy": "label_context_next_line", "score": 90})

        # STRATEGY B: Position / Layout-Based (Before DOB / Gender)
        # Name often appears right before Identity/DOB block
        for i, line in enumerate(lines):
            # 1. Inline Extraction: Check if Name is completely flattened adjacent to DOB/Gender
            match = re.search(r'(.*?)(?:\b(dob|date of birth|gender|male|female)\b|\b\d{2,4}[/\-]\d{2}[/\-]\d{2,4}\b)', line, re.IGNORECASE)
            if match:
                preceding = match.group(1).strip()
                if preceding:
                    inline_words = preceding.split()
                    cand_found = False
                    for w_count in range(min(5, len(inline_words)), 0, -1):
                        cand = " ".join(inline_words[-w_count:])
                        cand_cln = clean_field_boundary(cand)
                        if is_valid_name(cand_cln):
                            candidates.append({"value": cand_cln, "strategy": "layout_inline_before_dob", "score": 85 + w_count})
                            cand_found = True
                            break
                    if cand_found:
                        break # We already found the best inline candidate

            # 2. Previous Line Extraction: Original logic for correctly tokenized newlines
            if re.search(r'\b(dob|date of birth|gender)\b', line, re.IGNORECASE) or re.search(r'\b\d{2,4}[/\-]\d{2}[/\-]\d{2,4}\b', line):
                for j in range(1, 4):
                    if i - j >= 0:
                        prev = clean_field_boundary(lines[i-j])
                        if is_valid_name(prev):
                            # Bonus for immediately preceding
                            score = 85 - (j - 1) * 5
                            candidates.append({"value": prev, "strategy": "layout_before_dob", "score": score})
                            break
                break

        # STRATEGY C: Document Specific (Aadhaar/PAN uppercase names)
        if doc_type in {"aadhaar_ocr", "pan"}:
            for j in range(min(10, len(lines))):
                cand = clean_field_boundary(lines[j])
                if is_valid_name(cand):
                    if re.match(r'^([A-Z\.]+\s+){0,4}[A-Z\.]+$', cand):
                        candidates.append({"value": cand, "strategy": "doc_header_uppercase", "score": 75})

        # STRATEGY D: General Fallback
        for line in lines:
            line_cln = clean_field_boundary(line)
            if is_valid_name(line_cln):
                if re.match(r'^([A-Za-z\.]+\s+){0,4}[A-Za-z\.]+$', line_cln):
                    candidates.append({"value": line_cln, "strategy": "fallback_words", "score": 60})

        if not candidates:
            return None, "", 0.0

        # Rank: Highest score first, then prefer longer names (e.g. ABHISHEK KUMAR RAUT over RAM KUMAR)
        candidates.sort(key=lambda x: (x["score"], len(x["value"].split()), len(x["value"])), reverse=True)
        
        best = candidates[0]
        if best["score"] >= 60:
            return best["value"], best["strategy"], float(best["score"])

        return None, "", 0.0

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

        # DOB Extraction (PRESERVED)
        dob_match = re.search(r'\b(\d{2}(?:[/-]\d{2}[/-]\d{4}))\b', full_text)
        if dob_match:
            fields["dob"] = {"value": dob_match.group(1), "confidence": 98.0, "strategy": "regex"}
        else:
            yob_anchor = LayoutParser.find_keyword_anchor(graph, ["yob", "year of birth"], search_direction="right")
            if yob_anchor:
                year_match = re.search(r'\b(19|20)\d{2}\b', yob_anchor["value"])
                if year_match:
                    fields["dob"] = {"value": year_match.group(0), "confidence": 85.0, "strategy": "keyword_anchor_year"}

        # Gender Extraction (PRESERVED)
        gender_match = re.search(r'\b(male|female|transgender|m|f|t)\b', full_text, re.IGNORECASE)
        if gender_match:
            val = gender_match.group(1).title()
            if val == "M": val = "Male"
            elif val == "F": val = "Female"
            fields["gender"] = {"value": val, "confidence": 99.0, "strategy": "regex_pattern"}

        # Unified Name Extraction
        name_val, name_strategy, name_conf = FieldExtractor._extract_name_advanced(full_text, doc_type)
        if name_val:
            fields["name"] = {"value": name_val, "confidence": name_conf, "strategy": name_strategy}

        # Document specific identifiers
        if doc_type == "aadhaar_ocr":
            uid_match = re.search(r'\b([2-9]{1}[0-9]{3}[\s]?[0-9]{4}[\s]?[0-9]{4})\b', full_text)
            if uid_match:
                fields["document_number"] = {"value": uid_match.group(1).replace(" ", ""), "confidence": 99.0, "strategy": "regex_aadhaar"}

        elif doc_type == "pan":
            pan_match = re.search(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', full_text)
            if pan_match:
                fields["document_number"] = {"value": pan_match.group(1), "confidence": 99.0, "strategy": "regex_pan"}

        elif doc_type == "passport":
            passport_match = re.search(r'\b(?:([A-Z][0-9]{7})|([0-9]{8}))\b', full_text)
            if passport_match:
                fields["document_number"] = {"value": (passport_match.group(1) or passport_match.group(2)).upper(), "confidence": 99.0, "strategy": "regex_passport"}

            # Passport-specific label fallback for name
            if "name" not in fields:
                surname = FieldExtractor._extract_label_value(full_text, ["surname"])
                given = FieldExtractor._extract_label_value(full_text, ["given names", "given name"])
                if surname or given:
                    full_name = " ".join([part for part in [given, surname] if part]).strip()
                    fields["name"] = {"value": full_name, "confidence": 90.0, "strategy": "label_value_passport"}

        elif doc_type in ["income_certificate", "caste_certificate", "domicile_certificate", "disability_certificate", "ration_card", "birth_certificate"]:
            cert_no = re.search(r'(?:certificate no|no\.|udid|number)[:\-\s]*([A-Z0-9/.\-]+)', full_text, re.IGNORECASE)
            if cert_no:
                fields["document_number"] = {"value": cert_no.group(1), "confidence": 90.0, "strategy": "regex"}
            
            # Certificate specific label fallback
            if "name" not in fields:
                cert_name = FieldExtractor._extract_label_value(full_text, ["certified that", "shri/smt/kum", "shri ", "smt "])
                if cert_name:
                    fields["name"] = {"value": cert_name, "confidence": 80.0, "strategy": "label_value_cert"}
            
            if doc_type == "income_certificate":
                income = re.search(r'(?:income|rupees|rs\.?)\s*([\d,]+)', full_text, re.IGNORECASE)
                if income: fields["income_amount"] = {"value": income.group(1), "confidence": 85.0, "strategy": "regex"}
            elif doc_type == "caste_certificate":
                caste = re.search(r'(?:caste|community|belongs to)\s+([\w\s]+?)\s+(?:categor|class|caste)', full_text, re.IGNORECASE)
                if caste: fields["caste"] = {"value": caste.group(1).strip()[:30], "confidence": 85.0, "strategy": "regex"}
                category_match = re.search(r'\b(obc|sc|st|ebc|open|general)\b', full_text, re.IGNORECASE)
                if category_match: fields["category"] = {"value": category_match.group(1).upper(), "confidence": 95.0, "strategy": "regex"}
            elif doc_type == "domicile_certificate":
                state = re.search(r'(?:state of|government of)\s+([a-zA-Z\s]+)', full_text, re.IGNORECASE)
                if state: fields["state"] = {"value": state.group(1).strip()[:30], "confidence": 85.0, "strategy": "regex"}
            elif doc_type == "disability_certificate":
                pct = re.search(r'(\d{1,3})\s*%', full_text)
                if pct: fields["disability_percentage"] = {"value": pct.group(1), "confidence": 90.0, "strategy": "regex"}

        total_conf = sum([f.get("confidence", 0) for f in fields.values()])
        overall = round(total_conf / len(fields), 2) if fields else 0.0

        return {
            "document_type": doc_type,
            "fields": fields,
            "overall_confidence": overall,
            "layout_graph": graph,
        }
