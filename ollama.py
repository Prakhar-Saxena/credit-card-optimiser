import json
import subprocess
import time
import urllib.error
import urllib.request
from config import MODEL, OLLAMA_URL, SEED, TEMPERATURE

_HEALTH_URL = "http://localhost:11434/api/tags"
_ollama_proc = None  # subprocess started by this script, if any


def _is_ollama_running():
    try:
        urllib.request.urlopen(_HEALTH_URL, timeout=2)
        return True
    except Exception:
        return False


def ensure_ollama():
    """Start Ollama if it isn't already running. Returns True if we started it."""
    global _ollama_proc
    if _is_ollama_running():
        return False
    print("Ollama not running — starting it...")
    _ollama_proc = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(0.5)
        if _is_ollama_running():
            print("Ollama ready.\n")
            return True
    raise RuntimeError("Ollama failed to start after 10 seconds.")


def shutdown_ollama():
    """Terminate the Ollama process if this script started it."""
    global _ollama_proc
    if _ollama_proc is not None:
        _ollama_proc.terminate()
        _ollama_proc.wait()
        _ollama_proc = None


def _payload(prompt):
    return json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": TEMPERATURE, "seed": SEED},
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
