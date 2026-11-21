"""AI providers behind one interface. The core app never depends on any of them.

- "disabled": AI features explain how to enable them.
- "openai_compatible": any service speaking the OpenAI chat-completions API — Ollama, LM Studio,
  Azure OpenAI / organisation gateways, Google Gemini (OpenAI endpoint), Groq, OpenRouter, OpenAI.
- "manual": the app builds the full prompt; you paste it into any chat tool (e.g. a free ChatGPT
  or Copilot account) and paste the answer back. No API or key needed.
"""

import time
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.system import AIInteraction, SystemSetting

SETTINGS_KEY = "ai"

PRESETS = {
    "ollama": {
        "label": "Ollama on this computer (free, private)",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1:8b",
        "needs_key": False,
    },
    "lmstudio": {
        "label": "LM Studio on this computer (free, private)",
        "base_url": "http://localhost:1234/v1",
        "model": "",
        "needs_key": False,
    },
    "organisation": {
        "label": "Organisation AI gateway / Azure OpenAI",
        "base_url": "",
        "model": "",
        "needs_key": True,
    },
    "gemini": {
        "label": "Google Gemini API (free tier available)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.5-flash",
        "needs_key": True,
    },
    "groq": {
        "label": "Groq (free tier available)",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "needs_key": True,
    },
    "openrouter": {
        "label": "OpenRouter (has free models)",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "",
        "needs_key": True,
    },
    "custom": {
        "label": "Other OpenAI-compatible service",
        "base_url": "",
        "model": "",
        "needs_key": True,
    },
}


class AIError(RuntimeError):
    pass


class ManualRequired(Exception):
    """Raised in manual mode: the caller returns the prompt for the user to run elsewhere."""

    def __init__(self, prompt: str):
        self.prompt = prompt


@dataclass
class AIConfig:
    provider: str = "disabled"  # disabled | openai_compatible | manual
    preset: str = "ollama"
    base_url: str = ""
    model: str = ""
    temperature: float = 0.3
    timeout_seconds: int = 120
    max_context_chars: int = 16000

    @property
    def api_key(self) -> str:
        return get_settings().ai_api_key

    def public(self) -> dict:
        return {
            "provider": self.provider,
            "preset": self.preset,
            "base_url": self.base_url,
            "model": self.model,
            "temperature": self.temperature,
            "timeout_seconds": self.timeout_seconds,
            "max_context_chars": self.max_context_chars,
            "api_key_set": bool(self.api_key),
            "is_local": self.base_url.startswith(("http://localhost", "http://127.0.0.1")),
        }


def load_config(db: Session) -> AIConfig:
    row = db.get(SystemSetting, SETTINGS_KEY)
    s = get_settings()
    base = {"provider": s.ai_provider, "base_url": s.ai_base_url, "model": s.ai_model}
    data = {**base, **(row.value if row else {})}
    return AIConfig(**{k: v for k, v in data.items() if k in AIConfig.__dataclass_fields__})


def save_config(db: Session, values: dict) -> AIConfig:
    row = db.get(SystemSetting, SETTINGS_KEY) or SystemSetting(key=SETTINGS_KEY, value={})
    row.value = {**(row.value or {}), **values}
    db.add(row)
    db.commit()
    return load_config(db)


def _log(
    db: Session,
    feature: str,
    cfg: AIConfig,
    prompt: str,
    text: str,
    started: float,
    error: str | None = None,
) -> None:
    db.add(
        AIInteraction(
            feature=feature,
            provider=cfg.provider,
            model=cfg.model or None,
            prompt_chars=len(prompt),
            response_chars=len(text),
            duration_ms=int((time.monotonic() - started) * 1000),
            ok=error is None,
            error=error[:500] if error else None,
        )
    )
    db.commit()


def complete(
    db: Session,
    feature: str,
    system: str,
    user: str,
    manual_response: str | None = None,
    max_tokens: int = 1500,
) -> str:
    """Run one chat completion with the configured provider."""
    cfg = load_config(db)
    prompt = f"{system}\n\n---\n\n{user}"
    started = time.monotonic()
    if manual_response is not None:
        if not manual_response.strip():
            raise AIError("Paste the AI's answer first.")
        _log(
            db,
            feature,
            AIConfig(**{**cfg.__dict__, "provider": "manual"}),
            prompt,
            manual_response,
            started,
        )
        return manual_response.strip()
    if cfg.provider == "disabled":
        raise AIError(
            "The AI assistant is turned off. Choose a provider in Administration → AI assistant."
        )
    if cfg.provider == "manual":
        raise ManualRequired(prompt)
    if not cfg.base_url or not cfg.model:
        raise AIError("Set the AI service address and model in Administration → AI assistant.")
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
        headers["api-key"] = cfg.api_key  # Azure OpenAI style; ignored by others
    body = {
        "model": cfg.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": cfg.temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    url = cfg.base_url.rstrip("/") + "/chat/completions"
    try:
        with httpx.Client(timeout=cfg.timeout_seconds) as client:
            r = client.post(url, json=body, headers=headers)
    except httpx.ConnectError as e:
        _log(db, feature, cfg, prompt, "", started, "connection refused")
        raise AIError(f"Cannot reach the AI service at {cfg.base_url}. Is it running?") from e
    except httpx.TimeoutException as e:
        _log(db, feature, cfg, prompt, "", started, "timeout")
        raise AIError(
            "The AI service took too long to answer. Try a smaller model or increase the timeout."
        ) from e
    if r.status_code >= 400:
        detail = _error_detail(r)
        _log(db, feature, cfg, prompt, "", started, f"HTTP {r.status_code}: {detail}")
        hint = {
            401: " Check the API key in backend/.env (AI_API_KEY).",
            403: " The key is not allowed to use this model.",
            404: " Check the service address and model name.",
            429: " The free-tier rate limit was reached; wait and try again.",
        }.get(r.status_code, "")
        raise AIError(f"The AI service returned an error ({r.status_code}): {detail}.{hint}")
    try:
        text = r.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError) as e:
        _log(db, feature, cfg, prompt, "", started, "unexpected response")
        raise AIError("The AI service returned a response in an unexpected format.") from e
    text = _strip_thinking(text).strip()
    _log(db, feature, cfg, prompt, text, started)
    if not text:
        raise AIError("The AI service returned an empty answer.")
    return text


def _error_detail(r: httpx.Response) -> str:
    try:
        data = r.json()
        err = data.get("error", data)
        msg = err.get("message") if isinstance(err, dict) else str(err)
        return (msg or r.reason_phrase)[:200]
    except ValueError:
        return r.reason_phrase or "error"


def _strip_thinking(text: str) -> str:
    """Some local reasoning models prefix answers with <think>…</think>."""
    import re

    return re.sub(r"<think>.*?</think>", "", text, flags=re.S)


def list_models(db: Session) -> list[str]:
    cfg = load_config(db)
    if cfg.provider != "openai_compatible" or not cfg.base_url:
        return []
    headers = {"Authorization": f"Bearer {cfg.api_key}"} if cfg.api_key else {}
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(cfg.base_url.rstrip("/") + "/models", headers=headers)
        r.raise_for_status()
        return sorted(m["id"] for m in r.json().get("data", []))
    except (httpx.HTTPError, ValueError, KeyError):
        return []
