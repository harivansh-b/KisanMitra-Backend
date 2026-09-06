"""Ollama chat client — STDLIB ONLY (urllib, no pip dep). Local-first.

Works against local Ollama or any OpenAI-compatible /api/chat endpoint.
Import-safe when Ollama absent — errors surface only on .chat()
so tests can inject FakeTransport.
"""
import json
import os
import urllib.request


class OllamaClient:
    def __init__(self, model=None, host=None, transport=None):
        self.model = model or os.environ.get("ASSISTANT_MODEL", "qwen3:8b")
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.transport = transport

    def chat(self, messages, tools=None, timeout=120):
        if self.transport is not None:
            return self.transport(messages, tools)
        payload = {"model": self.model, "messages": messages, "stream": False}
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(
            self.host + "/api/chat",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = json.loads(r.read().decode("utf-8"))
        except OSError as e:
            raise ConnectionError(
                f"Ollama unreachable at {self.host} (is `ollama serve` running? model `{self.model}` pulled?)"
            ) from e
        return body.get("message", {})
