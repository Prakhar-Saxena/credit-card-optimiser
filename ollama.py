import json
import urllib.request
from config import MODEL, OLLAMA_URL, TEMPERATURE


def _payload(prompt):
    return json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": TEMPERATURE},
    }).encode()


def ask_ollama_raw(prompt):
    """Call Ollama and return the full response as a string."""
    req = urllib.request.Request(OLLAMA_URL, data=_payload(prompt), headers={"Content-Type": "application/json"})
    parts = []
    with urllib.request.urlopen(req) as r:
        for line in r:
            chunk = json.loads(line)
            parts.append(chunk.get("response", ""))
            if chunk.get("done"):
                break
    return "".join(parts)


def ask_ollama_stream(prompt):
    """Call Ollama and stream the response to stdout."""
    req = urllib.request.Request(OLLAMA_URL, data=_payload(prompt), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        for line in r:
            chunk = json.loads(line)
            print(chunk.get("response", ""), end="", flush=True)
            if chunk.get("done"):
                break
    print()
