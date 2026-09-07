"""Ollama chat client â€” STDLIB ONLY (urllib, no pip dep). Local-first + Groq/Gemini fallback.

Flow: auto -> Ollama (qwen3:1.7b local) -> Groq (fast cloud) -> Gemini if needed.
Groq is fastest (~900 tok/s) with best tool-calling for SQL agent.
"""
import json
import os
import urllib.request
import urllib.error


class OllamaClient:
    def __init__(self, model=None, host=None, transport=None):
        try:
            from app.core.config import settings as _s
            _cfg_model = _s.ASSISTANT_MODEL
            _cfg_host = _s.OLLAMA_HOST
            _cfg_provider = getattr(_s, "LLM_PROVIDER", "auto")
            _cfg_gemini_key = getattr(_s, "GOOGLE_API_KEY", "")
            _cfg_gemini_model = getattr(_s, "GEMINI_MODEL", "gemini-pro-latest")
            _cfg_groq_key = getattr(_s, "GROQ_API_KEY", "")
            _cfg_groq_model = getattr(_s, "GROQ_MODEL", "llama-3.1-8b-instant")
        except Exception:
            _cfg_model = "qwen2.5:1.5b"
            _cfg_host = "http://localhost:11434"
            _cfg_provider = "auto"
            _cfg_gemini_key = os.environ.get("GOOGLE_API_KEY", "")
            _cfg_gemini_model = "gemini-pro-latest"
            _cfg_groq_key = os.environ.get("GROQ_API_KEY", "")
            _cfg_groq_model = "llama-3.1-8b-instant"
        self.model = model or os.environ.get("ASSISTANT_MODEL") or _cfg_model
        self.host = (host or os.environ.get("OLLAMA_HOST") or _cfg_host).rstrip("/")
        self.provider = (os.environ.get("LLM_PROVIDER") or _cfg_provider).lower()
        self.gemini_key = (os.environ.get("GOOGLE_API_KEY") or _cfg_gemini_key or "").strip()
        self.gemini_model = os.environ.get("GEMINI_MODEL") or _cfg_gemini_model
        self.groq_key = (os.environ.get("GROQ_API_KEY") or _cfg_groq_key or "").strip()
        self.groq_model = os.environ.get("GROQ_MODEL") or _cfg_groq_model
        self.transport = transport

    def chat(self, messages, tools=None, timeout=180):
        if self.transport is not None:
            return self.transport(messages, tools)
        # forced providers
        if self.provider == "groq" and self.groq_key:
            return self._groq_chat(messages, tools, timeout=min(timeout, 30))
        if self.provider == "gemini" and self.gemini_key:
            return self._gemini_chat(messages, tools, timeout)
        # auto: Ollama -> Groq -> Gemini
        if self.provider in ("auto", "ollama", ""):
            try:
                return self._ollama_chat(messages, tools, timeout)
            except (OSError, ConnectionError, TimeoutError, urllib.error.URLError) as e:
                # try Groq first (fastest, high limits)
                if self.groq_key:
                    try:
                        return self._groq_chat(messages, tools, timeout=min(timeout, 30))
                    except Exception as ge:
                        # try Gemini next
                        if self.gemini_key:
                            try:
                                return self._gemini_chat(messages, tools, timeout=min(timeout, 30))
                            except Exception as gem_e:
                                raise ConnectionError(f"Ollama failed ({e}); Groq also failed ({ge}); Gemini also failed ({gem_e})") from gem_e
                        raise ConnectionError(f"Ollama failed ({e}) and Groq fallback also failed ({ge})") from ge
                if self.gemini_key:
                    try:
                        return self._gemini_chat(messages, tools, timeout=min(timeout, 30))
                    except Exception as ge:
                        raise ConnectionError(f"Ollama failed ({e}) and Gemini fallback also failed ({ge})") from ge
                raise ConnectionError(f"Ollama unreachable at {self.host} (is `ollama serve` running? model `{self.model}` pulled?)") from e
        if self.groq_key:
            return self._groq_chat(messages, tools, timeout)
        if self.gemini_key:
            return self._gemini_chat(messages, tools, timeout)
        return self._ollama_chat(messages, tools, timeout)

    def _groq_normalize(self, messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for i, m in enumerate(messages):
            role = m.get("role", "user")
            if role == "tool":
                # OpenAI expects tool messages with tool_call_id
                tc_id = m.get("tool_call_id") or f"call_{i}"
                out.append({"role": "tool", "tool_call_id": tc_id, "content": m.get("content", "")})
            elif role == "assistant" and m.get("tool_calls"):
                norm_tcs = []
                for j, tc in enumerate(m["tool_calls"]):
                    fn = tc.get("function", tc)
                    norm_tcs.append({"id": tc.get("id") or f"call_{i}_{j}", "type": "function", "function": {"name": fn.get("name"), "arguments": fn.get("arguments", "{}") if not isinstance(fn.get("arguments"), dict) else json.dumps(fn.get("arguments"))}})
                out.append({"role": "assistant", "content": m.get("content") or "", "tool_calls": norm_tcs})
            else:
                out.append({"role": role, "content": m.get("content", "") or ""})
        return out

    def _groq_chat(self, messages, tools, timeout=30):
        import time as _t
        url = "https://api.groq.com/openai/v1/chat/completions"
        gmsgs = self._groq_normalize(messages)
        payload = {"model": self.groq_model, "messages": gmsgs, "temperature": 0.2, "max_tokens": 600}
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.groq_key}", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"}
        for attempt in range(2):
            req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = json.loads(r.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:600] if hasattr(e, "read") else str(e)
                if e.code == 429 and attempt == 0:
                    import re as _re429
                    m = _re429.search(r"try again in ([0-9.]+)s", detail)
                    wait = float(m.group(1)) + 0.5 if m else 4
                    if wait > 12: wait = 12
                    _t.sleep(wait)
                    continue
                raise ConnectionError(f"Groq API error {e.code}: {detail[:300]}") from e
        choice = (body.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        out = {"role": msg.get("role", "assistant"), "content": msg.get("content") or ""}
        if msg.get("tool_calls"):
            norm = []
            for tc in msg["tool_calls"]:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if isinstance(args, dict):
                    args = json.dumps(args)
                # keep id so next turn we can echo it back for Groq
                norm.append({"id": tc.get("id") or "call_0", "function": {"name": fn.get("name"), "arguments": args}})
            out["tool_calls"] = norm
        return out

    def _ollama_chat(self, messages, tools, timeout):
        payload = {"model": self.model, "messages": messages, "stream": False, "think": False, "keep_alive": "30m", "options": {"num_ctx": 2048, "temperature": 0.2}}
        if tools:
            payload["tools"] = tools
        req = urllib.request.Request(self.host + "/api/chat", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
        return body.get("message", {})

    def _gemini_chat(self, messages, tools, timeout=30):
        # Try OpenAI-compat first, then native generateContent fallback with model rotation
        candidates = [self.gemini_model, "gemini-pro-latest", "gemini-2.5-pro-preview-tts", "gemini-flash-latest"]
        # dedupe preserve order
        seen = set()
        models = [m for m in candidates if not (m in seen or seen.add(m))]
        last_err = None
        for mdl in models:
            # 1) OpenAI compat
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
                payload = {"model": mdl, "messages": messages, "temperature": 0.2}
                if tools:
                    payload["tools"] = tools
                    payload["tool_choice"] = "auto"
                headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.gemini_key}", "x-goog-api-key": self.gemini_key}
                req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    body = json.loads(r.read().decode("utf-8"))
                choice = (body.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                out = {"role": msg.get("role", "assistant"), "content": msg.get("content") or ""}
                if msg.get("tool_calls"):
                    norm = []
                    for tc in msg["tool_calls"]:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", "{}")
                        if isinstance(args, dict):
                            args = json.dumps(args)
                        norm.append({"function": {"name": fn.get("name"), "arguments": args}})
                    out["tool_calls"] = norm
                return out
            except urllib.error.HTTPError as e:
                detail = e.read().decode()[:500] if hasattr(e, "read") else str(e)
                last_err = f"OpenAI {mdl} {e.code}: {detail[:200]}"
                # 403 permission denied -> try next model; 429 quota -> also try next
                # try native endpoint as second chance for same model
                try:
                    native = self._gemini_native(messages, tools, mdl, timeout)
                    return native
                except Exception as ne:
                    last_err = f"{last_err} | native {ne}"
                    continue
            except Exception as e:
                last_err = str(e)[:300]
                continue
        raise ConnectionError(f"Gemini all models failed: {last_err}")

    def _gemini_native(self, messages, tools, model, timeout):
        # native generateContent â€” handles tools via functionDeclarations
        # Build contents from Ollama messages
        system_text = ""
        contents = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "") or ""
            if role == "system":
                system_text += content + "\n"
                continue
            if role == "tool":
                # tool result -> functionResponse
                # last tool call name unknown here, use generic
                contents.append({"role": "user", "parts": [{"text": f"Tool result: {content}"}]})
                continue
            if role == "assistant" and m.get("tool_calls"):
                # assistant function call -> keep as text hint
                tc = m["tool_calls"][0]
                fn = tc.get("function", tc)
                contents.append({"role": "model", "parts": [{"text": f"Call {fn.get('name')} with {fn.get('arguments')}"}]})
                continue
            g_role = "model" if role == "assistant" else "user"
            contents.append({"role": g_role, "parts": [{"text": content}]})
        if not contents:
            contents = [{"role": "user", "parts": [{"text": system_text or "hi"}]}]
        payload = {"contents": contents}
        if system_text.strip():
            payload["systemInstruction"] = {"parts": [{"text": system_text[:4000]}]}
        if tools:
            decls = []
            for t in tools:
                fn = t.get("function", {})
                decls.append({"name": fn.get("name"), "description": fn.get("description", ""), "parameters": fn.get("parameters", {"type": "object", "properties": {}})})
            payload["tools"] = [{"functionDeclarations": decls}]
            payload["toolConfig"] = {"functionCallingConfig": {"mode": "AUTO"}}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_key}"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = json.loads(r.read().decode("utf-8"))
        cand = (body.get("candidates") or [{}])[0]
        content = cand.get("content", {})
        parts = content.get("parts") or []
        text = ""
        tool_calls = []
        for p in parts:
            if "text" in p:
                text += p["text"]
            if "functionCall" in p:
                fc = p["functionCall"]
                args = fc.get("args", {})
                if isinstance(args, dict):
                    args = json.dumps(args)
                tool_calls.append({"function": {"name": fc.get("name"), "arguments": args}})
        out = {"role": "assistant", "content": text}
        if tool_calls:
            out["tool_calls"] = tool_calls
        return out
