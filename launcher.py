#!/usr/bin/env python3
"""
Sweet Bonanza 1000 - Standalone Game Launcher
Launches the game with virtual wallet balance integration.

Usage:
    python launcher.py --balance 500
    python launcher.py --balance 1000 --port 8080
"""

import argparse
import asyncio
import json
import html
import http.server
import socketserver
import threading
import os
import sys
import time
from urllib.parse import urlencode, urlparse, parse_qs
from urllib.request import build_opener, HTTPCookieProcessor, Request
import http.cookiejar

try:
    from playwright.async_api import async_playwright
    _HAS_PLAYWRIGHT = True
except ImportError:
    async_playwright = None
    _HAS_PLAYWRIGHT = False

# Game configuration
GAME_ID = 95426
GAME_NAME = "Sweet Bonanza 1000"
BASE_URL = "https://melbet-tn.com"
LANG = "en"


def _build_api_url(base_url: str, path: str, params: dict) -> str:
    base_url = base_url.rstrip("/")
    qs = urlencode({k: v for k, v in params.items() if v is not None}, doseq=True)
    return f"{base_url}{path}?{qs}" if qs else f"{base_url}{path}"


def _make_http_opener(base_url: str, lang: str):
    jar = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"),
        ("Accept", "application/json, text/plain, */*"),
        ("Accept-Language", f"{lang},{lang};q=0.9,en;q=0.8"),
        ("Referer", f"{base_url.rstrip('/')}/{lang}/slots"),
        ("X-Requested-With", "XMLHttpRequest"),
    ]
    # Warm up cookies
    try:
        with opener.open(f"{base_url.rstrip('/')}/{lang}/slots", timeout=30) as r:
            r.read(1)
    except Exception:
        pass
    return opener


def _get_demo_link(game_id: int, retries: int = 5, backoff_s: float = 0.75) -> str:
    """Fetch the demo game URL from MelBet API."""
    opener = _make_http_opener(BASE_URL, LANG)
    
    # Warm up with game page
    try:
        with opener.open(f"{BASE_URL}/{LANG}/slots?game={game_id}", timeout=30) as r:
            r.read(1)
    except Exception:
        pass
    
    api_url = _build_api_url(
        BASE_URL,
        "/web-api/tpgamesopening/getgameurl",
        {
            "demo": "true",
            "id": game_id,
            "withGameInfo": "true",
            "sectionId": 1,
            "launchDomain": "melbet-tn.com/",
        },
    )
    
    last_err = None
    for attempt in range(retries + 1):
        try:
            req = Request(api_url, method="GET")
            with opener.open(req, timeout=30) as r:
                data = r.read().decode("utf-8")
            j = json.loads(data)
            if isinstance(j, dict) and isinstance(j.get("link"), str) and j.get("link"):
                return str(j["link"])
            last_err = "Demo link not found in response"
        except Exception as e:
            last_err = str(e)
        
        if attempt < retries:
            time.sleep(backoff_s * (2 ** attempt))
    
    raise RuntimeError(f"Failed to get demo link: {last_err}")


class Wallet:
    def __init__(self, initial_balance: float = 1000.0):
        self.balance = initial_balance
    
    def update(self, amount: float):
        self.balance = amount


def create_server(host: str, port: int, initial_balance: float):
    """Create the HTTP server that serves the game launcher."""
    wallet = Wallet(initial_balance)
    demo_url_cache = {}
    
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress logging
        
        def _send_html(self, status: int, content: str):
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        
        def _send_json(self, status: int, payload):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        
        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            
            if path == "/api/wallet/balance":
                self._send_json(200, {"balance": wallet.balance, "currency": "FUN"})
                return
            
            if path == "/" or path.startswith("/game"):
                # Get demo URL
                if GAME_ID not in demo_url_cache:
                    try:
                        demo_url_cache[GAME_ID] = _get_demo_link(GAME_ID)
                    except Exception as e:
                        self._send_html(500, f"<h1>Failed to get game URL</h1><pre>{e}</pre>")
                        return
                
                demo_url = demo_url_cache[GAME_ID]
                self._send_html(200, self._render_game_page(demo_url))
                return
            
            self._send_html(404, "<h1>Not Found</h1>")
        
        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            
            if path == "/api/wallet/sync":
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)
                try:
                    data = json.loads(body)
                    new_balance = float(data.get("balance", wallet.balance))
                    wallet.update(new_balance)
                    self._send_json(200, {"success": True, "balance": wallet.balance})
                except Exception as e:
                    self._send_json(400, {"success": False, "error": str(e)})
                return
            
            self._send_json(404, {"error": "Not found"})
        
        def _render_game_page(self, demo_url: str) -> str:
            return f"""<!doctype html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{GAME_NAME}</title>
    <style>
        body {{ margin: 0; font-family: system-ui, sans-serif; }}
        header {{ display: flex; gap: 12px; align-items: center; padding: 10px 12px; background: #111; color: #fff; }}
        iframe {{ width: 100vw; height: calc(100vh - 44px); border: 0; }}
    </style>
</head>
<body>
    <header>
        <strong>{GAME_NAME}</strong>
        <span style="opacity:.7">Game ID: {GAME_ID}</span>
    </header>
    <iframe src="{demo_url}" allowfullscreen></iframe>
    <script>
        let walletBalance = {wallet.balance};
        let lastGameBalance = null;

        async function syncWallet(newBalance) {{
            try {{
                await fetch('/api/wallet/sync', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ balance: newBalance }})
                }});
            }} catch (e) {{ console.error("Failed to sync wallet", e); }}
        }}

        window.addEventListener('message', (e) => {{
            let data = e.data;
            try {{ if (typeof data === 'string') data = JSON.parse(data); }} catch(err){{}}
            if (!data) return;

            if (data.name === 'post_updateBalance' || (data.event === 'updateBalance' && data.params?.total)) {{
                const rawAmount = data.params?.total?.amount;
                if (typeof rawAmount === 'number') {{
                    const gameVal = rawAmount / 100.0;
                    if (lastGameBalance === null) {{
                        lastGameBalance = gameVal;
                        console.log("Initialized baseline game balance:", gameVal);
                    }} else {{
                        const delta = gameVal - lastGameBalance;
                        lastGameBalance = gameVal;
                        if (delta !== 0) {{
                            walletBalance += delta;
                            syncWallet(walletBalance);
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>"""
    
    return socketserver.ThreadingTCPServer((host, port), Handler)


async def launch_browser(host: str, port: int, initial_balance: float):
    """Launch browser with extension."""
    if not _HAS_PLAYWRIGHT:
        print("Error: Playwright not installed. Run: pip install playwright && playwright install chromium")
        return 1
    
    # Start server in background
    server = create_server(host, port, initial_balance)
    server.allow_reuse_address = True
    
    def run_server():
        print(f"Server running on http://{host}:{port}/")
        server.serve_forever()
    
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    await asyncio.sleep(1)
    
    # Launch browser with extension
    extension_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "extension"))
    if not os.path.exists(extension_path):
        print(f"Error: Extension not found at {extension_path}")
        return 1
    
    async with async_playwright() as p:
        print(f"Launching browser with extension...")
        user_data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".browser_profile"))
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=False,
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
            ]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(f"http://{host}:{port}/", timeout=60000)
        
        print(f"\n✅ {GAME_NAME} launched with balance: ${initial_balance:.2f}")
        print("Close the browser window to exit.\n")
        
        try:
            while context.pages:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, Exception):
            pass
        
        await context.close()
    
    return 0


def main():
    parser = argparse.ArgumentParser(description=f"Launch {GAME_NAME} with virtual wallet")
    parser.add_argument("--balance", type=float, default=1000.0, help="Initial balance (default: 1000)")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    args = parser.parse_args()
    
    return asyncio.run(launch_browser(args.host, args.port, args.balance))


if __name__ == "__main__":
    sys.exit(main())
