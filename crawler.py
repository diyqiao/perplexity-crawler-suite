import os
import sys
import json
import csv
import time
import random
import argparse
from pathlib import Path
from typing import List, Dict

# Fix Windows stdout encoding
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DEFAULT_PROFILE_DIR = Path(__file__).parent / "browser_profile"

def find_system_browser() -> str | None:
    """Locate installed system Edge or Chrome executable on Windows."""
    paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None

STEALTH_JS = """
// Mask webdriver fingerprint
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
"""

def fetch_comments_with_persistent_session(
    url: str,
    max_scrolls: int = 5,
    headless: bool = True,
    profile_dir: Path = DEFAULT_PROFILE_DIR,
    interactive_login: bool = False
) -> List[Dict[str, str]]:
    """
    Crawls comments using a persistent browser profile.
    Cookies, LocalStorage & Sessions are saved in `profile_dir`.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[!] Error: Playwright is required. Run 'pip install playwright'.")
        return []

    exe_path = find_system_browser()
    if not exe_path:
        print("[!] Error: Could not find system Edge or Chrome browser.")
        return []

    profile_dir.mkdir(parents=True, exist_ok=True)
    comments = []

    print(f"[*] Profile Dir: {profile_dir.resolve()}")
    print(f"[*] Launching Browser ({exe_path}) | Headless: {headless} | Interactive Login: {interactive_login}")

    with sync_playwright() as p:
        try:
            # Using launch_persistent_context keeps Cookies & Session login state across runs!
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir.resolve()),
                executable_path=exe_path,
                headless=headless,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )

            # Apply anti-detection stealth script to all pages
            context.add_init_script(STEALTH_JS)
            page = context.pages[0] if context.pages else context.new_page()

            if interactive_login:
                print(f"\n[🔑 Login Mode] Opening {url} in visible browser...")
                print("[👉 Action Required] Please scan QR code or login manually in the opened browser window.")
                page.goto(url, timeout=60000)
                input("\n>>> Press ENTER in this console AFTER you have successfully logged in... <<< \n")
                print("[✔] Login state saved to persistent profile directory!")
                context.close()
                return []

            print(f"[*] Navigating to {url} ...")
            page.goto(url, timeout=45000, wait_until="domcontentloaded")
            time.sleep(3)

            # Check if login modal or verification is required
            print(f"[*] Scrolling page to trigger comment loading ({max_scrolls} times)...")
            for i in range(max_scrolls):
                page.evaluate("window.scrollBy(0, 800);")
                time.sleep(random.uniform(1.2, 2.5))  # Random delay anti-crawler

            # Extraction logic with selectors
            raw_texts = []
            selectors = [
                ".comment-item", ".comment-content", ".comment-text",
                ".comment-inner", "div[class*='comment']",
                ".tm-rate-fulltxt", ".rate-grid",
                "p[class*='desc']", "span[class*='content']"
            ]

            extracted_nodes = set()
            for sel in selectors:
                try:
                    elements = page.query_selector_all(sel)
                    for el in elements:
                        txt = el.inner_text().strip()
                        if txt and len(txt) > 5 and txt not in extracted_nodes:
                            extracted_nodes.add(txt)
                            raw_texts.append(txt)
                except Exception:
                    continue

            if not raw_texts:
                print("[*] Fallback:Extracting visible page text blocks...")
                body_text = page.inner_text("body")
                lines = [line.strip() for line in body_text.split("\n") if len(line.strip()) > 8]
                raw_texts = lines[:40]

            for idx, text in enumerate(raw_texts, 1):
                comments.append({
                    "id": idx,
                    "comment": text,
                    "platform_url": url
                })

            context.close()
        except Exception as err:
            print(f"[!] Error during crawling: {err}")

    return comments

def save_comments(comments: List[Dict[str, str]], output_file: str):
    """Save extracted comments to JSON or CSV."""
    out_path = Path(output_file)
    if out_path.suffix.lower() == ".csv":
        with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "comment", "platform_url"])
            writer.writeheader()
            writer.writerows(comments)
    else:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(comments, f, ensure_ascii=False, indent=2)
    print(f"[✔] Successfully saved {len(comments)} comments to {output_file}")

def main():
    parser = argparse.ArgumentParser(description="Persistent Cookie & Anti-Crawler Comment Scraper")
    parser.add_argument("url", nargs="?", help="Target URL (JD, Xiaohongshu, Douyin, Taobao, etc.)")
    parser.add_argument("--login", action="store_true", help="Open browser to perform manual login & save persistent Cookies")
    parser.add_argument("--profile-dir", default=str(DEFAULT_PROFILE_DIR), help="Directory path to store persistent browser Cookies & Profile")
    parser.add_argument("--scrolls", type=int, default=5, help="Number of auto scrolls to trigger dynamic comments")
    parser.add_argument("--output", default="comments.json", help="Output file path (.json or .csv)")
    parser.add_argument("--no-headless", action="store_true", help="Show browser GUI during scraping")

    args = parser.parse_args()

    profile_path = Path(args.profile_dir)

    if args.login:
        target_url = args.url or "https://www.xiaohongshu.com"
        fetch_comments_with_persistent_session(
            url=target_url,
            headless=False,
            profile_dir=profile_path,
            interactive_login=True
        )
        return

    if not args.url:
        parser.print_help()
        return

    comments = fetch_comments_with_persistent_session(
        url=args.url,
        max_scrolls=args.scrolls,
        headless=not args.no_headless,
        profile_dir=profile_path,
        interactive_login=False
    )

    if comments:
        save_comments(comments, args.output)
    else:
        print("[!] No comments extracted. If login or captcha is required, run with `--login` first.")

if __name__ == "__main__":
    main()
