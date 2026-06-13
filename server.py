#!/usr/bin/env python3
"""Simple HTTP server for Gab n' Go web interface."""

import json
import http.server
import socketserver
from pathlib import Path

PORT = 8080
HOST = "0.0.0.0"
CONCEPTS_PATH = Path("concepts.json")

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/concepts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if CONCEPTS_PATH.exists():
                self.wfile.write(CONCEPTS_PATH.read_bytes())
            else:
                self.wfile.write(b"[]")
            return
        super().do_GET()

    def do_PUT(self):
        if self.path == "/api/concepts":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                CONCEPTS_PATH.write_text(json.dumps(data, indent=2) + "\n")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, PUT, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


if __name__ == "__main__":
    print(f"Gab n' Go server running at http://{HOST}:{PORT}")
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()
