"""Shared OpenAI call + cost logging. Prices copied from continuity/backend/app/usage.py (USD per 1M tokens)."""
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from openai import OpenAI

HERE = Path(__file__).parent
PRICING = {
    'gpt-6-luna': {'input': 0.10, 'cached': 0.01, 'output': 0.50},
    'gpt-6-sol': {'input': 2.00, 'cached': 0.20, 'output': 10.00},
}
_client: OpenAI | None = None
_log_lock = threading.Lock()


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()  # reads OPENAI_API_KEY from the environment
    return _client


def cost_usd(model: str, inp: int, cached: int, out: int) -> float:
    r = PRICING[model]
    return ((inp - cached) * r['input'] + cached * r['cached'] + out * r['output']) / 1_000_000


def parse(model: str, system: str, user: str, schema: type, effort: str | None = None,
          max_output_tokens: int = 6000, log: Path | None = None, tag: str = '') -> tuple[Any, dict]:
    """One structured-output call. Returns (parsed object, usage record). Appends the record to `log`."""
    extra = {'reasoning': {'effort': effort}} if effort else {}
    start = time.perf_counter()
    resp = client().responses.parse(
        model=model, max_output_tokens=max_output_tokens, text_format=schema,
        input=[{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], **extra)
    latency = time.perf_counter() - start
    u = resp.usage
    cached = getattr(getattr(u, 'input_tokens_details', None), 'cached_tokens', 0) or 0
    reasoning = getattr(getattr(u, 'output_tokens_details', None), 'reasoning_tokens', 0) or 0
    rec = {
        'at': datetime.now().isoformat(timespec='seconds'), 'tag': tag, 'model': model, 'effort': effort,
        'input_tokens': u.input_tokens, 'cached_tokens': cached, 'output_tokens': u.output_tokens,
        'reasoning_tokens': reasoning, 'cost_usd': round(cost_usd(model, u.input_tokens, cached, u.output_tokens), 6),
        'latency_ms': round(latency * 1000),
    }
    if log:
        with _log_lock, log.open('a', encoding='utf-8') as f:  # calls run in parallel threads
            f.write(json.dumps(rec) + '\n')
    return resp.output_parsed, rec
