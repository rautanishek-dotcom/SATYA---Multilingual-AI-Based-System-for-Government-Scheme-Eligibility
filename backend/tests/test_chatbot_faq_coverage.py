import os
import sys
import unittest
from unittest.mock import patch

from flask import Flask

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from language_config import SUPPORTED_LANGUAGE_CODES
from routes.chatbot import (
    build_scheme_faqs,
    chatbot_bp,
    get_localized_greeting,
    get_localized_suggestions,
    load_chatbot_faqs,
    normalize_chat_language,
)
from faq_data import get_faqs
from routes import translator_utils


class MockCollection:
    def __init__(self, documents):
        self.documents = documents

    def find(self, *args, **kwargs):
        return self.documents


class MockDatabase:
    def __init__(self, faqs=None, schemes=None):
        self.faqs = MockCollection(faqs or [])
        self.schemes = MockCollection(schemes or [])


class TestChatbotFaqCoverage(unittest.TestCase):
    def test_scheme_questions_are_derived_from_available_facts(self):
        scheme_faqs = build_scheme_faqs([{
            "name": "Sample Scheme",
            "description": "A stored description.",
            "benefits": "A stored benefit.",
            "target_beneficiaries": "Eligible residents.",
            "application_process": "Apply through the official portal.",
        }])

        self.assertEqual(len(scheme_faqs), 4)
        self.assertEqual(scheme_faqs[0]["answer"], "A stored description.")
        self.assertEqual(scheme_faqs[-1]["answer"], "Apply through the official portal.")

    def test_loader_includes_curated_faqs_when_database_faqs_are_empty(self):
        faqs = load_chatbot_faqs(MockDatabase(schemes=[{
            "name": "Sample Scheme",
            "description": "A stored description.",
        }]))
        questions = {faq["question"] for faq in faqs}

        self.assertIn("What is the Document Vault?", questions)
        self.assertIn("Which profile details affect my scheme matches?", questions)
        self.assertIn("What is Sample Scheme?", questions)

    def test_all_supported_languages_are_kept_and_locale_codes_are_normalized(self):
        for language in SUPPORTED_LANGUAGE_CODES:
            with self.subTest(language=language):
                self.assertEqual(normalize_chat_language(language), language)

        self.assertEqual(normalize_chat_language("ta-IN"), "ta")
        self.assertEqual(normalize_chat_language("brx", "hi"), "brx")
        self.assertEqual(normalize_chat_language("unsupported", "hi"), "hi")

    def test_initial_suggestions_include_vault_and_eligibility_questions(self):
        suggestions = get_localized_suggestions("en", get_faqs())

        self.assertTrue(any("Vault" in question for question in suggestions))
        self.assertTrue(any("eligibility" in question.lower() for question in suggestions))

    def test_localized_suggestions_translate_in_one_batch(self):
        with patch("routes.translator_utils.translate_batch_from_english", side_effect=lambda texts, lang: texts) as batch:
            get_localized_suggestions("ta", get_faqs())

        batch.assert_called_once()
        self.assertEqual(batch.call_args.args[0][:2], ["Main Menu", "List All Schemes"])

    def test_uncached_supported_language_uses_translation_fallback(self):
        with patch("routes.chatbot.translate_from_english", return_value="localized greeting") as translate:
            greeting = get_localized_greeting("or")

        self.assertEqual(greeting, "localized greeting")
        translate.assert_called_once()

    def test_incoming_question_uses_source_language_fallback(self):
        with patch.dict(translator_utils.PERSISTENT_CACHE, {}, clear=True), \
             patch.object(translator_utils, "GoogleTranslator", side_effect=RuntimeError), \
             patch.object(translator_utils, "_translate_with_mymemory", return_value="translated query") as fallback, \
             patch.object(translator_utils, "cache_put"), \
             patch.object(translator_utils, "save_cache_to_disk"):
            translated = translator_utils.translate_to_english("localized query", source_lang="ta")

        self.assertEqual(translated, "translated query")
        fallback.assert_called_once_with("localized query", "en", source_lang="ta-IN")

    def test_outgoing_translation_falls_back_when_primary_returns_source_text(self):
        with patch.dict(translator_utils.PERSISTENT_CACHE, {}, clear=True), \
             patch.object(translator_utils, "GoogleTranslator") as primary, \
             patch.object(translator_utils, "_translate_with_mymemory", side_effect=lambda text, lang: text), \
               patch.object(translator_utils, "_translate_with_bhashini", side_effect=lambda text, source, target: text), \
             patch.object(translator_utils, "_translate_with_google_gtx", return_value="localized response") as fallback, \
             patch.object(translator_utils, "cache_put"), \
             patch.object(translator_utils, "save_cache_to_disk"):
            primary.return_value.translate.return_value = "source response"
            translated = translator_utils.translate_from_english("source response", "kok")

        self.assertEqual(translated, "localized response")
        fallback.assert_called_once_with("source response", "kok")

    def test_bhashini_fallback_uses_selected_language_code(self):
        response = unittest.mock.Mock(
            status_code=200,
            json=lambda: {"pipelineResponse": [{"output": [{"target": "స్థానిక సమాధానం"}]}]},
        )
        with patch.dict(os.environ, {"BHASHINI_INFERENCE_KEY": "test-key"}), \
             patch.object(translator_utils.requests, "post", return_value=response) as post:
            translated = translator_utils._translate_with_bhashini("English answer", "en", "te")

        self.assertEqual(translated, "స్థానిక సమాధానం")
        payload = post.call_args.kwargs["json"]
        language = payload["pipelineTasks"][0]["config"]["language"]
        self.assertEqual(language, {"sourceLanguage": "en", "targetLanguage": "te"})

    def test_chat_endpoint_answers_generated_scheme_question(self):
        database = MockDatabase(schemes=[{
            "name": "Sample Scheme",
            "description": "A stored description.",
            "benefits": "A stored benefit.",
        }])
        app = Flask(__name__)
        app.register_blueprint(chatbot_bp, url_prefix="/api/chatbot")

        with patch("routes.chatbot.get_db", return_value=database), \
             patch("routes.chatbot.detect_language", return_value="en"), \
             patch("routes.chatbot.translate_to_english", side_effect=lambda text, source_lang=None: text), \
             patch("routes.chatbot.translate_from_english", side_effect=lambda text, lang: text):
            response = app.test_client().post(
                "/api/chatbot",
                json={"query": "What benefits does Sample Scheme provide?", "lang": "en"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["response"], "A stored benefit.")

    def test_localized_faq_answer_and_suggestions_share_one_batch(self):
        app = Flask(__name__)
        app.register_blueprint(chatbot_bp, url_prefix="/api/chatbot")

        with patch("routes.chatbot.get_db", return_value=MockDatabase()), \
             patch("routes.chatbot.detect_language", return_value="en"), \
             patch("routes.chatbot.translate_to_english", return_value="What is SATYA?"), \
             patch("routes.translator_utils.translate_batch_from_english", side_effect=lambda texts, lang: texts) as batch:
            response = app.test_client().post(
                "/api/chatbot",
                json={"query": "SATYA என்ன?", "lang": "ta"},
            )

        self.assertEqual(response.status_code, 200)
        batch.assert_called_once()
        self.assertEqual(batch.call_args.args[0][1:3], ["Main Menu", "List All Schemes"])

    def test_chat_does_not_translate_each_scheme_before_matching(self):
        database = MockDatabase(schemes=[
            {"name": f"Scheme {index}", "description": "A scheme."}
            for index in range(80)
        ])
        app = Flask(__name__)
        app.register_blueprint(chatbot_bp, url_prefix="/api/chatbot")

        with patch("routes.chatbot.get_db", return_value=database), \
             patch("routes.chatbot.detect_language", return_value="en"), \
             patch("routes.chatbot.translate_from_english", wraps=translator_utils.translate_from_english) as translate:
            response = app.test_client().post(
                "/api/chatbot",
                json={"query": "What is SATYA?", "lang": "en"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(translate.call_count, 0)


if __name__ == "__main__":
    unittest.main()