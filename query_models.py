import requests, os
from dotenv import load_dotenv

load_dotenv('backend/.env')
UDYAT_KEY = os.getenv('BHASHINI_UDYAT_KEY')
INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')

url = "https://meity-auth.ulcacore.in/ulca/apis/v0/model/getModelsPipeline"
headers = {
    "userID": UDYAT_KEY,
    "ulcaApiKey": INFERENCE_KEY,
    "Content-Type": "application/json"
}

for lang in ['kok', 'sd', 'ur', 'gom']:
    payload = {
        "pipelineTasks": [{"taskType": "translation", "config": {"language": {"sourceLanguage": "en", "targetLanguage": lang}}}],
        "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"}
    }
    r = requests.post(url, headers=headers, json=payload, timeout=10)
    print(lang, r.status_code)
    if r.status_code == 200:
        data = r.json()
        try:
            tasks = data.get('pipelineResponseConfig', [])
            for t in tasks:
                if t.get('taskType') == 'translation':
                    configs = t.get('config', [])
                    for cfg in configs:
                        print(f"  ServiceId: {cfg.get('serviceId')}")
        except Exception as e:
            print("  err", e)
