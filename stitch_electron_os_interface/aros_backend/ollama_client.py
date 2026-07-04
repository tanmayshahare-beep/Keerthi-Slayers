"""Thin wrapper around a local Ollama server - no cloud LLM, nothing leaves
this machine. Ollama exposes a small REST API (default localhost:11434);
we talk to it with plain `requests`, no extra SDK dependency.

Model choice: "phi3" (Phi-3-mini, ~2.2GB) by default - picked for being a
capable, genuinely lightweight instruction-following model well-suited to
plain-language summarization and chat on modest/CPU hardware, per the ask
for something lightweight for a demo. Override with the AROS_OLLAMA_MODEL
env var if you'd rather point at a different local model.
"""

import os

import requests

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("AROS_OLLAMA_MODEL", "phi3")

STATUS_TIMEOUT = 3
CHAT_TIMEOUT = 180  # local CPU inference on a "lightweight" model is still not instant


class OllamaUnavailableError(RuntimeError):
    pass


def is_available() -> bool:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=STATUS_TIMEOUT)
        return resp.ok
    except requests.RequestException:
        return False


def chat(messages: list[dict], model: str | None = None, num_predict: int = 400) -> str:
    """messages: [{"role": "system"|"user"|"assistant", "content": str}, ...]
    Returns the assistant's reply text. Raises OllamaUnavailableError with a
    message fit to show directly in the UI if Ollama isn't reachable."""
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": model or DEFAULT_MODEL,
                "messages": messages,
                "stream": False,
                # Kept modest on purpose - this is a lightweight local demo,
                # not a long-form writer, and shorter replies mean the CPU
                # inference actually stays fast.
                "options": {"num_predict": num_predict, "temperature": 0.4},
            },
            timeout=CHAT_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.ConnectionError:
        raise OllamaUnavailableError(
            f"Couldn't reach Ollama at {OLLAMA_URL}. Make sure it's installed and running, "
            f"then run: ollama pull {model or DEFAULT_MODEL}"
        )
    except requests.Timeout:
        raise OllamaUnavailableError("Ollama took too long to respond - the model may still be loading. Try again.")
    except requests.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("error", "")
        except Exception:
            pass
        if "not found" in detail.lower():
            raise OllamaUnavailableError(f'Model "{model or DEFAULT_MODEL}" isn\'t pulled yet. Run: ollama pull {model or DEFAULT_MODEL}')
        raise OllamaUnavailableError(f"Ollama returned an error: {detail or e}")

    return resp.json()["message"]["content"]
