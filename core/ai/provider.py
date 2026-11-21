"""Hybrid Local + Cloud LLM Provider Abstraction

Supports Ollama local models (qwen2.5:7b, qwen3:8b, llama3.1) and hosted cloud models
with automatic fallback to deterministic grounded heuristic evaluation when offline.
Uses standard library urllib.request for zero-dependency HTTP calls.
"""
import os
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("quantedge.ai")


class LLMProvider:
    def __init__(
        self,
        provider: Optional[str] = None,
        ollama_base_url: Optional[str] = None,
        ollama_model: Optional[str] = None,
        cloud_api_key: Optional[str] = None,
        cloud_base_url: Optional[str] = None,
        cloud_model: Optional[str] = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "ollama")).lower()
        self.ollama_base_url = ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.cloud_api_key = cloud_api_key or os.getenv("CLOUD_LLM_API_KEY", "")
        self.cloud_base_url = cloud_base_url or os.getenv("CLOUD_LLM_BASE_URL", "https://api.openai.com/v1")
        self.cloud_model = cloud_model or os.getenv("CLOUD_LLM_MODEL", "gpt-4o-mini")

    def generate_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Attempt generation using primary provider, falling back if unavailable.
        Returns parsed JSON dict or None.
        """
        if self.provider == "ollama":
            res = self._call_ollama(prompt, system_prompt)
            if res:
                return res
            if self.cloud_api_key:
                return self._call_cloud(prompt, system_prompt)
        elif self.provider in ("cloud", "openai"):
            res = self._call_cloud(prompt, system_prompt)
            if res:
                return res
            return self._call_ollama(prompt, system_prompt)

        return None

    def _call_ollama(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        url = f"{self.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.ollama_model,
            "system": system_prompt,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    response_text = data.get("response", "{}")
                    return json.loads(response_text)
        except Exception as e:
            logger.debug(f"Ollama call offline ({self.ollama_model} @ {url}): {e}")
            return None

    def _call_cloud(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        if not self.cloud_api_key:
            return None
        url = f"{self.cloud_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.cloud_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Authorization": f"Bearer {self.cloud_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"]
                    return json.loads(content)
        except Exception as e:
            logger.debug(f"Cloud LLM call offline ({self.cloud_model}): {e}")
            return None
