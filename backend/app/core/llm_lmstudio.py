from __future__ import annotations
"""LM Studio client wrapper (Phase 1 foundation).

Provides chat + embedding + health check methods against a local LM Studio
OpenAI-compatible server.
"""
from typing import List, Dict, Any, Optional
import httpx
from app.core.config import settings

DEFAULT_TIMEOUT = 400

class LMStudioClient:
    def __init__(self):
        self.base = settings.LMSTUDIO_BASE_URL.rstrip('/')
        self.chat_model = settings.LMSTUDIO_CHAT_MODEL
        self.embed_model = settings.LMSTUDIO_EMBED_MODEL
        self.timeout = settings.LMSTUDIO_TIMEOUT or DEFAULT_TIMEOUT

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Basic single POST helper (no fallback)."""
        url = f"{self.base}{path}" if not path.startswith('http') else path
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, json=payload)
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            data.setdefault('_endpoint', url)
            return data

    async def _post_with_fallback(self, candidate_paths: List[str], payload: Dict[str, Any]) -> Dict[str, Any]:
        last: Dict[str, Any] = {}
        for p in candidate_paths:
            try:
                data = await self._post(p, payload)
                text_blob = (str(data) + str(data.get('raw',''))).lower()
                if 'unexpected endpoint' in text_blob:
                    last = data
                    continue  # try next path
                return data
            except Exception as e:
                last = {"error": str(e), "_endpoint": p}
                continue
        return last

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.0, max_tokens: int = 512, **kwargs) -> Dict[str, Any]:
        payload = {
            "model": self.chat_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        payload.update(kwargs)
        # Build deterministic ordered list of candidate endpoints.
        base_with_v1 = self.base if self.base.endswith('/v1') else (self.base + '/v1')
        base_no_v1 = base_with_v1[:-3]
        ordered = [
            base_with_v1 + '/chat/completions',
            base_with_v1 + '/completions',
            base_no_v1 + '/v1/chat/completions',  # duplicate of first if already had /v1
            base_no_v1 + '/v1/completions',
            base_no_v1 + '/chat/completions',
            base_no_v1 + '/completions'
        ]
        # Normalize & dedupe preserving order
        seen = set(); norm = []
        for c in ordered:
            c2 = c.replace('///','//').replace(':///', '://') 
            if c2 not in seen:
                seen.add(c2); norm.append(c2)
        return await self._post_with_fallback(norm, payload)

    async def get_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        data = await self.chat(messages, **kwargs)
        # Attempt standard parse, fallback to variants
        try:
            message = data["choices"][0]["message"]
            content = message.get("content", "").strip()
            # Some models (like o1) use reasoning_content instead of content
            if not content and "reasoning_content" in message:
                content = message.get("reasoning_content", "").strip()
            return content
        except Exception:
            pass
        try:
            # Some responses might embed text differently
            return data.get("raw", "").strip()
        except Exception:
            return ""

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        payload = {"model": self.embed_model, "input": texts}
        base_with_v1 = self.base if self.base.endswith('/v1') else (self.base + '/v1')
        base_no_v1 = base_with_v1[:-3]
        ordered = [
            base_with_v1 + '/embeddings',
            base_no_v1 + '/v1/embeddings',
            base_no_v1 + '/embeddings'
        ]
        seen = set(); norm = []
        for c in ordered:
            c2 = c.replace('///','//').replace(':///', '://')
            if c2 not in seen:
                seen.add(c2); norm.append(c2)
        data = await self._post_with_fallback(norm, payload)
        return [d.get("embedding", []) for d in data.get("data", [])]

    async def health_check(self) -> Dict[str, Any]:
        status: Dict[str, Any] = {"chat": False, "embed": False}
        try:
            r = await self.chat([{"role": "user", "content": "ping"}], max_tokens=1)
            status["chat"] = bool(r.get("choices"))
        except Exception as e:
            status["chat_error"] = str(e)
        try:
            e = await self.embed(["ping"])
            status["embed"] = bool(e and isinstance(e[0], list))
        except Exception as e:
            status["embed_error"] = str(e)
        return status

lmstudio_client = LMStudioClient()
