"""Hybrid Local + Cloud LLM Provider Abstraction

Unifies local Ollama model routing (qwen2.5:7b, llama3.1, deepseek-r1) and hosted
OpenAI-compatible cloud models with automatic fallback to deterministic grounded
heuristic evaluation when offline.
Uses standard library urllib.request for zero external dependencies.
"""
import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("quantedge.ai")


def clean_json_response(content: str) -> Optional[Dict[str, Any]]:
    """Clean markdown code fences and parse JSON string."""
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()

    try:
        return json.loads(content)
    except Exception:
        # Fallback: regex search for outer {...}
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


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
        self.ollama_base_url = (ollama_base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.ollama_model = ollama_model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.cloud_api_key = cloud_api_key or os.getenv("CLOUD_LLM_API_KEY", "")
        self.cloud_base_url = (cloud_base_url or os.getenv("CLOUD_LLM_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.cloud_model = cloud_model or os.getenv("CLOUD_LLM_MODEL", "gpt-4o-mini")

    def get_supported_models(self) -> List[str]:
        """List of default supported models across local and cloud environments."""
        return [
            "qwen2.5:7b",
            "qwen3:8b",
            "llama3.1",
            "gpt-4o-mini",
            "gpt-4o",
            "claude-3-5-sonnet",
        ]

    def generate_json(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Attempt generation using primary provider, falling back seamlessly if offline.
        Returns parsed JSON dict or None (enabling deterministic local heuristics).
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
        url = f"{self.ollama_base_url}/api/generate"
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
            with urllib.request.urlopen(req, timeout=4) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    response_text = data.get("response", "{}")
                    return clean_json_response(response_text)
        except Exception as e:
            logger.debug(f"Ollama call offline ({self.ollama_model} @ {url}): {e}")
            return None

    def _call_cloud(self, prompt: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        if not self.cloud_api_key:
            return None
        url = f"{self.cloud_base_url}/chat/completions"
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
            with urllib.request.urlopen(req, timeout=6) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    content = data["choices"][0]["message"]["content"]
                    return clean_json_response(content)
        except Exception as e:
            logger.debug(f"Cloud LLM call offline ({self.cloud_model}): {e}")
            return None
