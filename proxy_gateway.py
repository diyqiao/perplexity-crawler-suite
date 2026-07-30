import os
import sys
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Load .env variables
def load_dotenv():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"\''))

load_dotenv()

TARGET_HOST = "api.perplexity.ai"
PORT = 8000

class ProxyGatewayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[Gateway] {self.address_string()} -> {args[0]}")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_POST(self):
        self.forward_request("POST")

    def do_GET(self):
        self.forward_request("GET")

    def forward_request(self, method):
        real_key = os.environ.get("PERPLEXITY_API_KEY")
        if not real_key:
            self.send_error(500, "Gateway Error: PERPLEXITY_API_KEY is missing in .env file")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build target URL
        path = self.path if self.path != "/" else "/chat/completions"
        target_url = f"https://{TARGET_HOST}{path}"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {real_key}",
            "User-Agent": "Zero-Key-Proxy-Gateway/1.0"
        }

        req = urllib.request.Request(target_url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                resp_body = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(resp_body)
        except urllib.error.HTTPError as e:
            err_body = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(err_body)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

def run_server():
    server_address = ("127.0.0.1", PORT)
    httpd = HTTPServer(server_address, ProxyGatewayHandler)
    print(f"\n========================================================")
    print(f"🚀 Zero-Key API Proxy Gateway Running on http://127.0.0.1:{PORT}")
    print(f"🔑 Auto-Injecting Key from .env -> {TARGET_HOST}")
    print(f"========================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down proxy gateway...")

if __name__ == "__main__":
    run_server()
