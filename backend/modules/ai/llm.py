"""
SysWatch v2.1 — LLM Provider Abstraction with Health Tracking
- Multi-provider fallback chain (DeepSeek, Claude, OpenAI, Gemini)
- Provider health tracking in database (success rate, latency, errors)
- Automatic failover with circuit-breaker pattern
- Per-provider rate limiting awareness
"""
import time
import json
import logging
import requests
from datetime import timedelta
from typing import Optional

from modules.config import Config
from modules.database import db
from modules.logging_manager import log_event, utcnow

logger = logging.getLogger("syswatch.ai.llm")


class ProviderHealth:
    @staticmethod
    def ensure_provider_exists(provider, model, priority):
        db.execute("INSERT IGNORE INTO ai_provider_health (provider, model, api_key_present, priority, enabled) VALUES (%s, %s, FALSE, %s, TRUE)", (provider, model, priority))

    @staticmethod
    def update_api_key_status(provider, has_key):
        db.execute("UPDATE ai_provider_health SET api_key_present=%s, updated_at=NOW() WHERE provider=%s", (has_key, provider))

    @staticmethod
    def record_call(provider, success, latency_ms=0, error=None):
        db.execute("UPDATE ai_provider_health SET total_calls=total_calls+1, successful_calls=successful_calls+%s, failed_calls=failed_calls+%s, last_test_success=%s, last_test_at=NOW(), last_test_latency_ms=%s, last_error=%s, updated_at=NOW() WHERE provider=%s", (1 if success else 0, 0 if success else 1, success, latency_ms, error, provider))

    @staticmethod
    def get_health(provider):
        return db.query_one("SELECT * FROM ai_provider_health WHERE provider=%s", (provider,))

    @staticmethod
    def get_all_health():
        return db.query("SELECT * FROM ai_provider_health ORDER BY priority ASC")

    @staticmethod
    def is_circuit_open(provider, threshold=3):
        try:
            health = ProviderHealth.get_health(provider)
        except Exception:
            return False
        if not health:
            return False
        if health.get("last_test_success") is False and health.get("failed_calls", 0) >= threshold:
            if not health.get("last_test_at"):
                return True
            last_test = health["last_test_at"]
            if hasattr(last_test, "tzinfo") and last_test.tzinfo is None:
                last_test = last_test.replace(tzinfo=utcnow().tzinfo)
            if (utcnow() - last_test).total_seconds() > 300:
                return False
            return True
        return False

    @staticmethod
    def reset_circuit(provider):
        db.execute("UPDATE ai_provider_health SET failed_calls=0 WHERE provider=%s", (provider,))


class LLMProvider:
    def __init__(self, name, api_key, model, base_url):
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")

    def ask(self, prompt, system=None, temperature=0.7, max_tokens=2000):
        raise NotImplementedError

    def _make_request(self, url, headers, payload, timeout=30):
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=timeout)
            latency = int((time.time() - start) * 1000)
            if response.status_code == 200:
                ProviderHealth.record_call(self.name, True, latency)
                ProviderHealth.reset_circuit(self.name)
                return {"success": True, "data": response.json(), "latency_ms": latency}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:500]}"
                ProviderHealth.record_call(self.name, False, latency, error_msg)
                return {"success": False, "error": error_msg, "latency_ms": latency}
        except requests.Timeout:
            ProviderHealth.record_call(self.name, False, 0, "Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            ProviderHealth.record_call(self.name, False, latency, str(e))
            return {"success": False, "error": str(e), "latency_ms": latency}


class DeepSeekProvider(LLMProvider):
    def ask(self, prompt, system=None, temperature=0.7, max_tokens=2000):
        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        result = self._make_request(f"{self.base_url}/chat/completions", headers, payload, timeout=Config.AI_TIMEOUT)
        if result["success"]:
            text = result["data"]["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": self.name, "model": self.model}
        return result


class ClaudeProvider(LLMProvider):
    def ask(self, prompt, system=None, temperature=0.7, max_tokens=2000):
        payload = {"model": self.model, "max_tokens": max_tokens, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]}
        if system: payload["system"] = system
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
        result = self._make_request(f"{self.base_url}/messages", headers, payload, timeout=Config.AI_TIMEOUT)
        if result["success"]:
            text = result["data"]["content"][0]["text"]
            return {"success": True, "text": text, "provider": self.name, "model": self.model}
        return result


class OpenAIProvider(LLMProvider):
    def ask(self, prompt, system=None, temperature=0.7, max_tokens=2000):
        messages = []
        if system: messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        result = self._make_request(f"{self.base_url}/chat/completions", headers, payload, timeout=Config.AI_TIMEOUT)
        if result["success"]:
            text = result["data"]["choices"][0]["message"]["content"]
            return {"success": True, "text": text, "provider": self.name, "model": self.model}
        return result


class GeminiProvider(LLMProvider):
    def ask(self, prompt, system=None, temperature=0.7, max_tokens=2000):
        contents = [{"parts": [{"text": prompt}]}]
        if system: contents.insert(0, {"parts": [{"text": system}], "role": "model"})
        payload = {"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}}
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        result = self._make_request(url, headers, payload, timeout=Config.AI_TIMEOUT)
        if result["success"]:
            text = result["data"]["candidates"][0]["content"]["parts"][0]["text"]
            return {"success": True, "text": text, "provider": self.name, "model": self.model}
        return result


PROVIDER_CLASSES = {"deepseek": DeepSeekProvider, "claude": ClaudeProvider, "openai": OpenAIProvider, "gemini": GeminiProvider}


def _get_provider_instance(provider_name):
    api_key = getattr(Config, f"{provider_name.upper()}_API_KEY", "")
    if not api_key: return None
    model = getattr(Config, f"{provider_name.upper()}_MODEL", "")
    base_url = getattr(Config, f"{provider_name.upper()}_BASE_URL", "")
    provider_class = PROVIDER_CLASSES.get(provider_name)
    if not provider_class: return None
    priority = Config.AI_PROVIDER_ORDER.index(provider_name) if provider_name in Config.AI_PROVIDER_ORDER else 99
    ProviderHealth.ensure_provider_exists(provider_name, model, priority)
    ProviderHealth.update_api_key_status(provider_name, True)
    return provider_class(provider_name, api_key, model, base_url)


def ask_llm(prompt, system=None, provider=None, temperature=0.7, max_tokens=2000):
    if provider:
        instance = _get_provider_instance(provider)
        if not instance: return {"success": False, "error": f"Provider '{provider}' not configured"}
        return instance.ask(prompt, system, temperature, max_tokens)
    for provider_name in Config.AI_PROVIDER_ORDER:
        if ProviderHealth.is_circuit_open(provider_name):
            logger.info(f"Skipping {provider_name} - circuit breaker open")
            continue
        instance = _get_provider_instance(provider_name)
        if not instance: continue
        logger.info(f"Trying AI provider: {provider_name}")
        result = instance.ask(prompt, system, temperature, max_tokens)
        if result["success"]:
            logger.info(f"AI response from {provider_name} ({result.get('latency_ms', 0)}ms)")
            return result
        else:
            logger.warning(f"Provider {provider_name} failed: {result.get('error', 'unknown')}")
    return {"success": False, "error": "All AI providers failed or not configured"}


def get_provider_status():
    ProviderHealth.ensure_provider_exists("deepseek", Config.DEEPSEEK_MODEL, 0)
    ProviderHealth.ensure_provider_exists("claude", Config.CLAUDE_MODEL, 1)
    ProviderHealth.ensure_provider_exists("openai", Config.OPENAI_MODEL, 2)
    ProviderHealth.ensure_provider_exists("gemini", Config.GEMINI_MODEL, 3)
    for name in Config.AI_PROVIDER_ORDER:
        key = getattr(Config, f"{name.upper()}_API_KEY", "")
        ProviderHealth.update_api_key_status(name, bool(key))
    health = ProviderHealth.get_all_health()
    result = []
    for h in health:
        total = h.get("total_calls", 0)
        success = h.get("successful_calls", 0)
        success_rate = round(success / total * 100, 1) if total > 0 else 0
        result.append({"name": h["provider"], "model": h.get("model", ""), "api_key_present": h.get("api_key_present", False), "priority": h.get("priority", 99), "enabled": h.get("enabled", True), "last_test_success": h.get("last_test_success"), "last_test_at": h["last_test_at"].isoformat() if h.get("last_test_at") else None, "last_test_latency_ms": h.get("last_test_latency_ms"), "total_calls": total, "successful_calls": success, "failed_calls": h.get("failed_calls", 0), "success_rate": success_rate, "last_error": h.get("last_error"), "circuit_open": ProviderHealth.is_circuit_open(h["provider"])})
    return result


def test_provider(provider_name):
    result = ask_llm("Say OK", provider=provider_name.lower())
    if result["success"]:
        return {"success": True, "message": f"{provider_name} responded: {result.get('text', '')[:50]}"}
    return {"success": False, "message": result.get("error", "Failed")}
