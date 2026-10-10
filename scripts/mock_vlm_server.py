#!/usr/bin/env python3
"""Tiny loopback-only OpenAI-compatible server for exercising client wiring."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("mock-vlm:", fmt % args)

    def _write(self, status: int, value: dict):
        data = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._write(200, {"status": "ok", "mock": True})
        elif self.path == "/v1/models":
            self._write(200, {"data": [{"id": "nvidia/Qwen3.8-27B-NVFP4", "object": "model"}]})
        else:
            self._write(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self._write(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        message = payload["messages"][-1]
        content = message["content"]
        if isinstance(content, list):
            has_image = any(part.get("type") == "image_url" for part in content)
            text = " ".join(part.get("text", "") for part in content if part.get("type") == "text")
        else:
            has_image = False
            text = content
        if has_image and "Compare" in text:
            answer = json.dumps(
                {
                    "event_type": "move",
                    "object_id": "red_cube",
                    "from_zone_id": "left_zone",
                    "to_zone_id": "right_zone",
                    "confidence": 0.99,
                    "visible_evidence": ["Mock server fixture moved the red cube from left to right."],
                    "uncertainty_reason": None,
                }
            )
        elif has_image:
            answer = "A red cube is visible in the left zone."
        else:
            answer = "LOCALRECALL_OK"
        self._write(
            200,
            {
                "id": "mock-completion",
                "object": "chat.completion",
                "model": "mock/localrecall-fixture",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": answer}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            },
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Mock VLM listening on http://127.0.0.1:{args.port}; no inference is performed.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
