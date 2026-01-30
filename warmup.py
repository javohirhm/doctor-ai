from google.cloud import aiplatform
import time

PROJECT_ID = "gen-lang-client-0450212936"
LOCATION = "us-central1"
ENDPOINT_ID = "mg-endpoint-af75176e-f883-44fa-9e06-729bb2650703"

print("🔥 Initializing Vertex AI...")
aiplatform.init(project=PROJECT_ID, location=LOCATION)

endpoint = aiplatform.Endpoint(
    endpoint_name=f"projects/{PROJECT_ID}/locations/{LOCATION}/endpoints/{ENDPOINT_ID}"
)

print("=" * 60)
print("🔥 WARMING UP MEDGEMMA ENDPOINT")
print("=" * 60)
print("⏱️  This may take 5-10 minutes on the FIRST request...")
print("☕ Grab a coffee and wait...")
print("=" * 60)

instance = {
    "@requestFormat": "chatCompletions",
    "messages": [
        {
            "role": "system",
            "content": "You are a medical AI assistant."
        },
        {
            "role": "user",
            "content": "What is diabetes?"
        }
    ]
}

start_time = time.time()

try:
    print(f"\n🚀 Sending warmup request at {time.strftime('%H:%M:%S')}...")
    response = endpoint.predict(instances=[instance], timeout=900)  # 15 min timeout
    
    elapsed = time.time() - start_time
    
    print(f"\n✅ SUCCESS! Endpoint is now WARM! ({elapsed:.1f} seconds)")
    print("=" * 60)
    print("Response preview:")
    print(str(response.predictions[0])[:200])
    print("=" * 60)
    print("\n🎉 Your Telegram bot will now respond in 2-5 seconds!")
    print("💡 Go ahead and test it!")
    
except Exception as e:
    elapsed = time.time() - start_time
    print(f"\n❌ Failed after {elapsed:.1f} seconds")
    print(f"Error: {str(e)}")
    print("\n💡 Try running this script again.")

