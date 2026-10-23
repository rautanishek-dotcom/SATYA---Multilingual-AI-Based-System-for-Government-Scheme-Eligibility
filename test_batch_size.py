"""
BHASHINI test with larger batch to confirm max safe batch size.
Does NOT write to any production file.
"""
import os
import json
import requests
from dotenv import load_dotenv

load_dotenv('backend/.env')
INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')

url = 'https://dhruva-api.bhashini.gov.in/services/inference/pipeline'
headers = {'Authorization': INFERENCE_KEY, 'Content-Type': 'application/json'}

# Test with 10 strings in one call
test_strings = [
    "Check Eligibility", "Document Vault", "Government Scheme",
    "Upload Document", "Verification Status", "Submit Application",
    "Annual Income", "Date of Birth", "Marital Status", "Get Started"
]

payload = {
    'pipelineTasks': [{'taskType': 'translation', 'config': {
        'language': {'sourceLanguage': 'en', 'targetLanguage': 'hi'},
        'serviceId': 'ai4bharat/indictrans-v2-all-gpu--t4'
    }}],
    'inputData': {'input': [{'source': s} for s in test_strings]}
}

try:
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print('Status:', r.status_code)
    data = r.json()
    outputs = data.get('pipelineResponse', [{}])[0].get('output', [])
    print(f'Sent {len(test_strings)} strings, received {len(outputs)} translations:')
    for o in outputs:
        print(f"  '{o.get('source','')}' → '{o.get('target','')}'")
except Exception as e:
    print('Error:', type(e).__name__, str(e)[:300])
