from flask import Blueprint, jsonify, request

from .translator_utils import SUPPORTED_LANGUAGES, translate_batch_from_english, translate_scheme_steps


localization_bp = Blueprint("localization", __name__)


@localization_bp.route("/translate", methods=["POST"])
def translate_ui_strings():
    """Translate a bounded list of English UI strings for the active locale."""
    payload = request.get_json(silent=True) or {}
    language = payload.get("lang", "en")
    texts = payload.get("texts", [])

    if language not in SUPPORTED_LANGUAGES:
        return jsonify({"error": "Unsupported language"}), 400
    if not isinstance(texts, list) or len(texts) > 600:
        return jsonify({"error": "texts must be a list containing at most 600 items"}), 400

    unique_texts = []
    seen = set()
    for text in texts:
        if not isinstance(text, str):
            continue
        normalized = text.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique_texts.append(normalized)

    if payload.get("mode") == "scheme_steps":
        translated = translate_scheme_steps(unique_texts, language)
    else:
        translated = translate_batch_from_english(unique_texts, language)
    return jsonify({"translations": dict(zip(unique_texts, translated))})
