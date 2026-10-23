import requests, os
from dotenv import load_dotenv
load_dotenv('backend/.env')
INFERENCE_KEY = os.getenv('BHASHINI_INFERENCE_KEY')
url = 'https://dhruva-api.bhashini.gov.in/services/inference/pipeline'
headers = {'Authorization': INFERENCE_KEY, 'Content-Type': 'application/json'}

# Check kok, sd, ur with alternate codes
alternates = {
    'kok': ['kok', 'gom', 'gom_Deva', 'kok_Deva'],
    'sd': ['sd', 'snd', 'snd_Arab', 'sd_Arab'],
    'ur': ['ur', 'urd', 'urd_Arab', 'ur_Arab']
}

for target, codes in alternates.items():
    print(f"\nTesting {target}:")
    for code in codes:
        payload = {
            'pipelineTasks': [{'taskType': 'translation', 'config': {
                'language': {'sourceLanguage': 'en', 'targetLanguage': code},
                'serviceId': 'ai4bharat/indictrans-v2-all-gpu--t4'
            }}],
            'inputData': {'input': [{'source': 'Check Eligibility'}]}
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=5)
            print(f"  {code}: status={r.status_code} {r.text[:120] if r.status_code==200 else r.text[:80]}")
        except Exception as e:
            print(f"  {code}: error {e}")
