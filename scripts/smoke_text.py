#!/usr/bin/env python3
"""Verify a short text completion from the local OpenAI-compatible vLLM server."""

from __future__ import annotations

import argparse
import sys
import time

import httpx


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="nvidia/Qwen3.8-27B-NVFP4")
    parser.add_argument("--timeout", type=float, default=180.0)
    args = parser.parse_args()

    if not args.base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        parser.error("The smoke test only permits a loopback model endpoint")

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": "Reply with exactly: LOCALRECALL_OK"}],
        "temperature": 0,
        "max_tokens": 24,
    }
    started = time.perf_counter()
    try:
        response = httpx.post(
            f"{args.base_url.rstrip('/')}/chat/completions",
            json=payload,
            timeout=args.timeout,
        )
    except httpx.HTTPError as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1
    latency_ms = (time.perf_counter() - started) * 1000
    print(f"HTTP {response.status_code}; latency_ms={latency_ms:.1f}")
    if response.status_code != 200:
        print(response.text[:2000], file=sys.stderr)
        return 1
    try:
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        reported_model = body.get("model", "unknown")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"Malformed chat response: {exc}", file=sys.stderr)
        return 1
    if not isinstance(content, str) or not content.strip():
        print("Model returned an empty or malformed answer", file=sys.stderr)
        return 1
    print(f"reported_model={reported_model}\n{content.strip()}")
    if "LOCALRECALL_OK" not in content:
        print("Response did not contain the requested sentinel", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
