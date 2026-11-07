"""Thin LLM wrapper using only the Python standard library (urllib), so there is nothing to install.

Supported providers (set LLM_PROVIDER in .env):
  groq       - Groq, free tier, very fast               (GROQ_API_KEY)   <- default
  gemini     - Google AI Studio, free tier available    (GEMINI_API_KEY)
  openai     - OpenAI                                   (OPENAI_API_KEY)
  anthropic  - Claude                                   (ANTHROPIC_API_KEY)

The evaluator can use a DIFFERENT provider/model from the generator (EVAL_PROVIDER / EVAL_MODEL).
That reduces "a model grading its own homework" bias, and it also gives each model its own rate-limit quota.

Speed and reliability settings (all optional, set in .env):
  REASONING_EFFORT=low           reasoning level for the WRITER   (gpt-oss models only: low | medium | high)
  EVAL_REASONING_EFFORT=medium   reasoning level for the JUDGE    (gpt-oss models only)
  LLM_MIN_INTERVAL=0             seconds to wait between calls to the same model (e.g. 3 to avoid 429s)
  LLM_TIMEOUT=240                seconds to wait for one reply before retrying
  LLM_MAX_RETRIES=6              how many times to retry a rate limit / timeout / server error
  LLM_MAX_WAIT=120               if the server asks for a longer wait than this (e.g. a daily limit), stop and explain
  LLM_MAX_WAIT=120               if the server asks for a longer wait than this (seconds), stop and explain instead

Model names change often. If you get a 404 "model not found" error, check your provider's model list
and set LLM_MODEL / EVAL_MODEL in .env.
"""
from __future__ import annotations

import json
import os
import re
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROVIDER = "groq"

# provider -> (base url, api-key env var, default model)
PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "openai/gpt-oss-120b"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "GEMINI_API_KEY", "gemini-3.8-flash"),
    "openai": ("https://api.openai.com/v1", "OPENAI_API_KEY", "gpt-4o-mini"),
    "anthropic": ("https://api.anthropic.com/v1", "ANTHROPIC_API_KEY", "claude-sonnet-5-5"),
}

_last_call: dict[tuple, float] = {}  # (provider, model) -> time of the last request, shared by writer and judge


class LLMError(RuntimeError):
    pass


def load_env(path: Path | None = None) -> None:
    """Minimal .env loader (KEY=value per line). Handles quotes and trailing '# comments'.
    Existing environment variables win."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip()
        if value[:1] in ('"', "'"):  # quoted value: keep everything inside the quotes
            quote = value[0]
            end = value.find(quote, 1)
            value = value[1:end] if end != -1 else value[1:]
        else:  # unquoted: cut off an inline " # comment"
            value = value.split(" #", 1)[0].split("\t#", 1)[0].strip()
        os.environ.setdefault(key.strip(), value)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


class Usage:
    """Tracks calls and tokens so we can talk about cost (the job post cares about cost)."""

    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def add(self, prompt: int, completion: int) -> None:
        self.calls += 1
        self.prompt_tokens += prompt or 0
        self.completion_tokens += completion or 0

    def as_dict(self) -> dict:
        return {
            "calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
        }


def _server_wait(headers, body: str) -> float | None:
    """Seconds the server asked us to wait (uncapped), or None if it did not say."""
    try:
        ra = headers.get("Retry-After") if headers else None
        if ra:
            return float(ra)
    except (TypeError, ValueError):
        pass
    m = re.search(r"try again in\s*(?:(\d+)h)?\s*(?:(\d+)m(?!s))?\s*([\d.]+)\s*(ms|s)", body or "", re.IGNORECASE)
    if m:
        unit = 1000 if m.group(4).lower() == "ms" else 1
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + float(m.group(3)) / unit
    return None


def _human(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return (f"{h}h " if h else "") + (f"{m}m " if m else "") + f"{s}s"


def _retry_delay(headers, body: str, attempt: int) -> float:
    """How long to wait after a 429/5xx. Prefer what the server tells us; otherwise back off exponentially."""
    try:  # 1. Retry-After header (seconds)
        ra = headers.get("Retry-After") if headers else None
        if ra:
            return float(ra) + 0.5
    except (TypeError, ValueError):
        pass
    m = re.search(r"try again in\s*(?:(\d+)m)?\s*([\d.]+)\s*(ms|s)", body or "", re.IGNORECASE)  # 2. "try again in 4.2s"
    if m:
        secs = int(m.group(1) or 0) * 60 + float(m.group(2)) / (1000 if m.group(3).lower() == "ms" else 1)
        return secs + 0.5
    return min(2.0 ** (attempt + 1), 30.0)  # 3. 2s, 4s, 8s, 16s, 30s


class LLM:
    def __init__(self, provider: str, model: str | None = None, temperature: float = 0.7, usage: Usage | None = None):
        provider = provider.lower()
        if provider not in PROVIDERS:
            raise LLMError(f"Unknown provider '{provider}'. Choose one of: {', '.join(PROVIDERS)}")
        self.provider = provider
        self.base_url, self.key_env, default_model = PROVIDERS[provider]
        self.model = model or default_model
        self.temperature = temperature
        self.usage = usage or Usage()
        self.reasoning_effort: str | None = None
        self.api_key = os.getenv(self.key_env, "")
        if not self.api_key:
            raise LLMError(
                f"{self.key_env} is not set. Copy .env.example to .env and add your key, "
                f"or run with --mock to test without any API."
            )

    @classmethod
    def from_env(cls, role: str, usage: Usage | None = None) -> "LLM":
        """role = 'generator' or 'evaluator'. The evaluator falls back to the generator settings."""
        base_provider = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER)
        provider = base_provider
        model = os.getenv("LLM_MODEL") or None
        if role == "evaluator":
            provider = os.getenv("EVAL_PROVIDER", base_provider)
            model = os.getenv("EVAL_MODEL") or (model if provider == base_provider else None)
            temperature = 0.0  # judging should be as repeatable as possible
            effort = os.getenv("EVAL_REASONING_EFFORT")
        else:
            temperature = float(os.getenv("GEN_TEMPERATURE", "0.7"))
            effort = os.getenv("REASONING_EFFORT")
        llm = cls(provider, model, temperature, usage)
        llm.reasoning_effort = (effort or "").strip().lower() or None
        return llm

    # ------------------------------------------------------------------------------------------
    def chat(self, system: str, user: str, temperature: float | None = None, task: str = "") -> str:
        t = self.temperature if temperature is None else temperature
        if self.provider == "anthropic":
            return self._anthropic(system, user, t)
        return self._openai_compatible(system, user, t)

    def _openai_compatible(self, system: str, user: str, temperature: float) -> str:
        payload = {
            "model": self.model,
            "temperature": temperature,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        }
        # Fewer hidden "thinking" tokens means faster replies and fewer rate-limit hits (gpt-oss models only).
        if self.reasoning_effort and "gpt-oss" in self.model:
            payload["reasoning_effort"] = self.reasoning_effort
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/chat/completions"
        try:
            data = self._post(url, headers, payload)
        except LLMError as e:
            # If the server does not accept the reasoning setting, drop it and try once more instead of crashing.
            if "reasoning_effort" in payload and "reasoning" in str(e).lower() and "HTTP 400" in str(e):
                print("[llm] reasoning_effort not accepted by this model; retrying without it", flush=True)
                self.reasoning_effort = None
                payload.pop("reasoning_effort", None)
                data = self._post(url, headers, payload)
            else:
                raise
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise LLMError(f"Unexpected response shape from {self.provider}: {str(data)[:300]}")
        u = data.get("usage") or {}
        self.usage.add(u.get("prompt_tokens", 0), u.get("completion_tokens", 0))
        return text or ""

    def _anthropic(self, system: str, user: str, temperature: float) -> str:
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": temperature,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        data = self._post(f"{self.base_url}/messages", headers, payload)
        try:
            text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError):
            raise LLMError(f"Unexpected response shape from anthropic: {str(data)[:300]}")
        u = data.get("usage") or {}
        self.usage.add(u.get("input_tokens", 0), u.get("output_tokens", 0))
        return text

    # ------------------------------------------------------------------------------------------
    def _pace(self) -> None:
        """Optional minimum gap between calls to the same model (set LLM_MIN_INTERVAL to avoid 429s)."""
        gap = _env_float("LLM_MIN_INTERVAL", 0.0)
        if gap <= 0:
            return
        key = (self.provider, self.model)
        wait = gap - (time.time() - _last_call.get(key, 0.0))
        if wait > 0:
            time.sleep(wait)

    def _post(self, url: str, headers: dict, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        # Some providers' firewalls block the default Python-urllib User-Agent (HTTP 403, error 1010).
        headers = {**headers, "User-Agent": "genai-lesson-agent/1.0", "Accept": "application/json"}
        timeout = _env_float("LLM_TIMEOUT", 90.0)
        max_retries = int(_env_float("LLM_MAX_RETRIES", 2))
        max_wait = _env_float("LLM_MAX_WAIT", 120.0)  # never sit through a single wait longer than this
        last_error = ""
        for attempt in range(max_retries + 1):
            self._pace()
            _last_call[(self.provider, self.model)] = time.time()
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                _last_call[(self.provider, self.model)] = time.time()
                return data
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:600]
                last_error = f"HTTP {e.code}: {detail[:300]}"
                if e.code == 429:
                    wait = _server_wait(e.headers, detail)
                    max_wait = _env_float("LLM_MAX_WAIT", 120.0)
                    if wait is not None and wait > max_wait:
                        raise LLMError(
                            f"{self.provider} rate limit: the server asks you to wait about {wait / 60:.0f} minute(s), "
                            f"longer than LLM_MAX_WAIT={max_wait:.0f}s, so retrying now would not help. "
                            f"This usually means a daily token limit for model '{self.model}'. "
                            f"Server message: {detail[:300]}"
                        )
                    if attempt == 0:
                        print(f"[llm] server says: {detail[:200]}", flush=True)
                if e.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                    delay = _retry_delay(e.headers, detail, attempt)
                    if e.code == 429 and delay > max_wait:
                        raise LLMError(
                            f"{self.provider} rate limit: the server asks to wait {_human(delay)} "
                            f"(more than LLM_MAX_WAIT={int(max_wait)}s). This usually means a DAILY token limit is "
                            f"used up for model '{self.model}'. Switch to another model/provider in .env, or wait. "
                            f"Server said: {detail[:250]}"
                        )
                    print(f"[llm] HTTP {e.code}; retrying in {delay:.0f}s ({attempt + 1}/{max_retries})", flush=True)
                    time.sleep(delay)
                    continue
                raise LLMError(f"{self.provider} request failed. {last_error}")
            except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError) as e:
                last_error = f"network error: {getattr(e, 'reason', e)}"
                if attempt < max_retries:
                    delay = min(2.0 ** (attempt + 1), 30.0)
                    print(f"[llm] {last_error}; retrying in {delay:.0f}s ({attempt + 1}/{max_retries})", flush=True)
                    time.sleep(delay)
                    continue
        raise LLMError(f"{self.provider} request failed after {max_retries} retries. {last_error}")