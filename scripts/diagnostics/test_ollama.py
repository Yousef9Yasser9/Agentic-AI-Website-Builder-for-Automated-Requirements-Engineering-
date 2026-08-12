import requests
import json

URL = "http://localhost:11434/api/chat"
model = "llama3.1"

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello"},
    ],
    "options": {
        "temperature": 0.2,
        "num_predict": 10,
        "num_ctx": 2048,
        "num_gpu": 999
    },
    "format": "json",
    "stream": False,
}

print(f"Calling Ollama at {URL} with model {model}...")
try:
    r = requests.post(URL, json=payload, timeout=30)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
