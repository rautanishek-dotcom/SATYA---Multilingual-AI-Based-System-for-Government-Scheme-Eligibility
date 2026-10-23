"""
BHASHINI Single Test Request
Tests ONE phrase → Hindi only.
Does NOT write to i18n.js or MongoDB.
Credentials read from backend/.env only.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv('backend/.env')

UDYAT_KEY = os.getenv('BHASHINI_UDYAT_KEY')
INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')

if not UDYAT_KEY or not INFERENCE_KEY:
    print("STOP: BHASHINI credentials missing. Cannot proceed.")
    exit(1)

print("BHASHINI credentials detected: YES")
print()

# ─── STEP 1: Fetch pipeline config via ULCA model search ─────────────────────
def get_pipeline_config(src_lang, tgt_lang):
    url = "https://meity-auth.ulcacore.in/ulca/apis/v0/model/getModelsPipeline"
    headers = {
        "userID": UDYAT_KEY,
        "ulcaApiKey": INFERENCE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": src_lang,
                        "targetLanguage": tgt_lang
                    }
                }
            }
        ],
        "pipelineRequestConfig": {
            "pipelineId": "64392f96daac500b55c543cd"
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        print(f"Pipeline config status: {resp.status_code}")
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"Pipeline config failed: {resp.text[:300]}")
            return None
    except Exception as e:
        print(f"Pipeline config error: {e}")
        return None

# ─── STEP 2: Use Dhruva inference endpoint ───────────────────────────────────
def test_dhruva_inference(service_id, src_lang, tgt_lang, test_text):
    url = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"
    headers = {
        "Authorization": INFERENCE_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "pipelineTasks": [
            {
                "taskType": "translation",
                "config": {
                    "language": {
                        "sourceLanguage": src_lang,
                        "targetLanguage": tgt_lang
                    },
                    "serviceId": service_id
                }
            }
        ],
        "inputData": {
            "input": [
                {"source": test_text},
                {"source": "Government Scheme"},
                {"source": "Document Vault"}
            ]
        }
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=20)
        print(f"Inference status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            outputs = data.get("pipelineResponse", [{}])[0].get("output", [])
            return outputs
        else:
            print(f"Inference failed: {resp.text[:400]}")
            return None
    except Exception as e:
        print(f"Inference error: {e}")
        return None

# ─── MAIN TEST ────────────────────────────────────────────────────────────────
print("=== PHASE 1: Fetching pipeline config (en → hi) ===")
config = get_pipeline_config("en", "hi")

if config is None:
    print("\nSTOP: Pipeline config fetch failed. Cannot proceed with translation.")
    exit(1)

# Extract service ID from config
service_id = None
try:
    tasks = config.get("pipelineResponseConfig", [])
    for task in tasks:
        if task.get("taskType") == "translation":
            service_id = task["config"][0]["serviceId"]
            break
except Exception as e:
    print(f"Could not extract serviceId: {e}")

if not service_id:
    # Try Dhruva known IDs as fallback probe
    service_id = "ai4bharat/indictrans-v2-all-gpu--t4"
    print(f"Using fallback serviceId: {service_id}")
else:
    print(f"Found serviceId: {service_id}")

print()
print("=== PHASE 2: Single batch inference test (3 strings, en → hi) ===")
outputs = test_dhruva_inference(service_id, "en", "hi", "Check Eligibility")

if outputs:
    print("\nTest PASSED. Translated texts:")
    for o in outputs:
        raw_src = o.get('source', '')
        raw_tgt = o.get('target', '')
        print(f"  '{raw_src}' → '{raw_tgt}'")
    print()
    print("Key observations:")
    print(f"  - Batch size tested: {len(outputs)} text segments in 1 API call")
    print("  - Authentication: SUCCESS")
    print("  - Response format: pipelineResponse[0].output[].target")
else:
    print("\nSTOP: Inference test failed. Cannot proceed with translation workload.")
    exit(1)

# ─── WORKLOAD ESTIMATE ────────────────────────────────────────────────────────
print()
print("=== WORKLOAD ESTIMATE ===")

TARGET_LANGS = 20  # excluding en, hi, bn which are already complete
PLACEHOLDER_STRINGS = 585  # per language (from audit)
TOTAL_UI_TRANSLATIONS = TARGET_LANGS * PLACEHOLDER_STRINGS
print(f"UI strings needing translation: {PLACEHOLDER_STRINGS} × {TARGET_LANGS} langs = {TOTAL_UI_TRANSLATIONS}")

SCHEMES = 342
SCHEME_LANGS = 20  # excluding en, hi, bn
TOTAL_SCHEME_TRANSLATIONS = SCHEMES * SCHEME_LANGS
print(f"Scheme name translations needed: {SCHEMES} × {SCHEME_LANGS} langs = {TOTAL_SCHEME_TRANSLATIONS}")

TOTAL = TOTAL_UI_TRANSLATIONS + TOTAL_SCHEME_TRANSLATIONS
print(f"Total individual translations needed: {TOTAL}")
print()

# BHASHINI Dhruva allows up to 10 segments per call based on docs
# We'll use batch_size=5 to stay safe and well within limits
BATCH_SIZE = 5
# We process per-language (all strings for 1 lang in 1 set of batches)
# = (585/5) batches per lang × 20 langs = 117 × 20 = 2340 for UI
# + (342/5) batches per lang × 20 langs = 69 × 20 = 1380 for schemes
# Total = 3720 requests — EXCEEDS 1000!

ui_calls_per_lang = -(-PLACEHOLDER_STRINGS // BATCH_SIZE)  # ceiling division
scheme_calls_per_lang = -(-SCHEMES // BATCH_SIZE)

ui_total_calls = ui_calls_per_lang * TARGET_LANGS
scheme_total_calls = scheme_calls_per_lang * SCHEME_LANGS
total_calls = ui_total_calls + scheme_total_calls

print(f"Batch size: {BATCH_SIZE} strings/call")
print(f"UI API calls needed: {ui_calls_per_lang}/lang × {TARGET_LANGS} langs = {ui_total_calls}")
print(f"Scheme API calls needed: {scheme_calls_per_lang}/lang × {SCHEME_LANGS} langs = {scheme_total_calls}")
print(f"TOTAL estimated API calls: {total_calls}")
print()

if total_calls > 1000:
    print(f"⚠️  WARNING: Estimated {total_calls} calls EXCEEDS 1000 approved calls.")
    print()
    print("PRIORITY RECOMMENDATION:")
    print("  Option A: Increase batch size to 10 strings/call (if BHASHINI supports it)")
    print(f"    → Would reduce to ~{(-(-PLACEHOLDER_STRINGS // 10) * TARGET_LANGS + -(-SCHEMES // 10) * SCHEME_LANGS)} calls")
    print("  Option B: Prioritize UI strings (20 langs × 117 calls = 2340 still too high at batch=5)")
    print("  Option C: Translate UI strings only (most visible), skip scheme name translation")
    print(f"    UI only at batch=10: {-(-PLACEHOLDER_STRINGS // 10) * TARGET_LANGS} calls")
    print()
    print("STOP: Will not start full translation run until you confirm the batch strategy.")
    print("To proceed, re-run with a confirmed --batch-size and --scope (ui-only / schemes-only / all)")
else:
    print(f"✅ Estimated {total_calls} calls is within the 1000 approved limit. Safe to proceed.")
