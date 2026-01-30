import requests
from google.auth import default
from google.auth.transport.requests import Request
import json

PROJECT_ID = "gen-lang-client-0450212936"
LOCATION = "us-central1"
ENDPOINT_ID = "mg-endpoint-af75176e-f883-44fa-9e06-729bb2650703"

# Get credentials
credentials, _ = default()
credentials.refresh(Request())

# Make request
url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}:predict"

headers = {
    "Authorization": f"Bearer {credentials.token}",
    "Content-Type": "application/json"
}

payload = {
    "instances": [{
        "@requestFormat": "chatCompletions",
        "messages": [
            {"role": "system", "content": "You are a medical assistant."},
            {"role": "user", "content": "What is diabetes?"}
        ]
    }]
}

print(f"🔄 Calling: {url}")
response = requests.post(url, headers=headers, json=payload, timeout=120)

print(f"📊 Status: {response.status_code}")
print(f"📦 Response: {json.dumps(response.json(), indent=2)[:500]}")

if response.status_code == 200:
    result = response.json()
    content = result['predictions'][0]['choices'][0]['message']['content']
    print(f"\n✅ SUCCESS!")
    print(f"📝 Response: {content}")