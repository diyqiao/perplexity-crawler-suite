import os
import sys
import json
import urllib.request
import urllib.error
import argparse
from pathlib import Path

# Windows console encoding fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"

def load_dotenv():
    """Simple zero-dependency .env file loader."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"\''))

load_dotenv()

CACHE_FILE = Path(__file__).parent / ".pplx_cache.json"

def get_cached_response(cache_key: str) -> str | None:
    """Retrieve response from local disk cache if available."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
            return cache.get(cache_key)
    except Exception:
        return None

def save_to_cache(cache_key: str, response_text: str):
    """Save response to local disk cache to avoid redundant API calls."""
    cache = {}
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
    cache[cache_key] = response_text
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def clear_cache():
    """Clear local disk cache."""
    if CACHE_FILE.exists():
        CACHE_FILE.unlink()
        return "Local cache cleared."
    return "No cache file found."

def perplexity_search(
    query: str, 
    model: str = "sonar", 
    system_prompt: str = "You are a helpful research assistant. Be extremely concise, factual, and direct without fluff.",
    max_tokens: int = 500,
    use_cache: bool = True
) -> str:
    """
    Query Perplexity API with cost-optimization strategies:
    - Default low-cost model (`sonar`)
    - Local cache lookup to eliminate duplicate API requests
    - Token limits (`max_tokens`) to cap output billing
    - Concise system prompt to minimize generated tokens
    """
    cache_key = f"{model}:{query.strip()}"
    if use_cache:
        cached = get_cached_response(cache_key)
        if cached:
            return f"[⚡ Local Cache Hit - $0 Cost]\n{cached}"

    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        return "Error: PERPLEXITY_API_KEY is not configured in environment or .env file."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        "max_tokens": max_tokens
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(PERPLEXITY_API_URL, data=data, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            res_body = response.read().decode("utf-8")
            res_json = json.loads(res_body)
            result = res_json["choices"][0]["message"]["content"]
            if use_cache:
                save_to_cache(cache_key, result)
            return result
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        return f"HTTP Error {e.code}: {err_msg}"
    except Exception as e:
        return f"Request Error: {str(e)}"

def mcp_server_loop():
    """
    Simple stdio JSON-RPC MCP server protocol runner for Perplexity Search tool.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "perplexity-search", "version": "1.1.0"}
                    }
                }
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "perplexity_search",
                                "description": "Perform cost-optimized real-time web search using Perplexity API.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string", "description": "The search query or prompt"},
                                        "model": {"type": "string", "description": "Model to use: sonar (cheapest, default), sonar-pro, sonar-reasoning", "default": "sonar"},
                                        "max_tokens": {"type": "integer", "description": "Max tokens in response to control cost", "default": 500},
                                        "use_cache": {"type": "boolean", "description": "Whether to use local disk cache to save cost", "default": True}
                                    },
                                    "required": ["query"]
                                }
                            }
                        ]
                    }
                }
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                if tool_name == "perplexity_search":
                    query = args.get("query", "")
                    model = args.get("model", "sonar")
                    max_tokens = args.get("max_tokens", 500)
                    use_cache = args.get("use_cache", True)
                    result = perplexity_search(query, model=model, max_tokens=max_tokens, use_cache=use_cache)
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": result}]
                        }
                    }
                else:
                    resp = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Method/Tool {tool_name} not found"}
                    }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {}
                }

            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
        except Exception as err:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(err)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description="Perplexity API Cost-Optimized CLI & MCP Integration Tool")
    parser.add_argument("query", nargs="?", help="Search query to execute via Perplexity API")
    parser.add_argument("--model", default="sonar", choices=["sonar", "sonar-pro", "sonar-reasoning"], help="Perplexity model name (default: sonar for lowest cost)")
    parser.add_argument("--max-tokens", type=int, default=500, help="Max output tokens to control billing (default: 500)")
    parser.add_argument("--no-cache", action="store_true", help="Bypass local cache and force API request")
    parser.add_argument("--clear-cache", action="store_true", help="Clear local search response cache")
    parser.add_argument("--mcp", action="store_true", help="Run as Stdio MCP Server")

    args = parser.parse_args()

    if args.clear_cache:
        print(clear_cache())
        return

    if args.mcp:
        mcp_server_loop()
    elif args.query:
        print(f"[*] Querying Perplexity API (model: {args.model}, max_tokens: {args.max_tokens}, cache: {not args.no_cache})...\n")
        result = perplexity_search(args.query, model=args.model, max_tokens=args.max_tokens, use_cache=not args.no_cache)
        print(result)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

