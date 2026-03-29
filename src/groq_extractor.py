from __future__ import annotations

import os
import re
import time

from openai import OpenAI

from src.base import BaseExtractor
from src.prompts import EXTRACTION_PROMPT
from src.schema import GraphData

_INTER_REQUEST_DELAY = 5
_RETRY_WAIT_429_DEFAULT = 60
_MAX_RETRIES = 4
_WAIT_BUFFER = 5  # API'nin söylediği süreye eklenen güvenlik payı (saniye)


def _parse_retry_after(error_str: str) -> float:
    """'Please try again in 10.94s' gibi mesajlardan saniye değerini çeker."""
    match = re.search(r"try again in\s+([\d.]+)s", error_str)
    if match:
        return float(match.group(1)) + _WAIT_BUFFER
    return _RETRY_WAIT_429_DEFAULT


def _flatten_schema(schema: dict) -> dict:
    """$defs içindeki $ref'leri inline expand eder — OpenAI/Groq function calling uyumluluğu için."""
    defs = schema.get("$defs", {})

    def resolve(obj: object) -> object:
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_name = obj["$ref"].split("/")[-1]
                return resolve(defs[ref_name])
            return {k: resolve(v) for k, v in obj.items() if k != "$defs"}
        if isinstance(obj, list):
            return [resolve(item) for item in obj]
        return obj

    return resolve(schema)  # type: ignore[return-value]


_EXTRACT_TOOL: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "extract_graph_data",
            "description": "CV metninden varlıkları ve ilişkileri çıkarır.",
            "parameters": _flatten_schema(GraphData.model_json_schema()),
        },
    }
]


class GroqExtractor(BaseExtractor):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        self.model = model
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
        )
        self._request_count = 0
        print(f"[SİSTEM] Groq Extraction Modu Aktif ({self.model})...")

    def extract(self, text: str, annotations: list = None) -> GraphData:
        if self._request_count > 0:
            time.sleep(_INTER_REQUEST_DELAY)
        self._request_count += 1

        messages = [
            {"role": "system", "content": EXTRACTION_PROMPT},
            {"role": "user", "content": f"CV metni:\n\n{text}"},
        ]

        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=_EXTRACT_TOOL,
                    tool_choice={"type": "function", "function": {"name": "extract_graph_data"}},
                    temperature=0,
                )
                arguments = response.choices[0].message.tool_calls[0].function.arguments
                return GraphData.model_validate_json(arguments)

            except Exception as exc:
                last_error = exc
                if attempt < _MAX_RETRIES:
                    exc_str = str(exc)
                    if "429" in exc_str:
                        wait = _parse_retry_after(exc_str)
                        print(f"  [RETRY {attempt}/{_MAX_RETRIES}] Rate limit — {wait:.1f}s bekleniyor")
                        time.sleep(wait)
                    else:
                        print(f"  [RETRY {attempt}/{_MAX_RETRIES}] {exc}")

        raise RuntimeError(
            f"GroqExtractor {_MAX_RETRIES} denemede başarısız: {last_error}"
        )
