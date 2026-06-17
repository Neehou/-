"""
东华倪家 — 自动启动脚本
启动 Flask 服务器 + Cloudflare Tunnel
自动尝试更新域名指向，失败则提示手动更新
"""
import subprocess
import sys
import re
import os
import json
import urllib.request

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ZONE_ID = "cfbb5aab326a690562d3058233baea26"
PAGE_RULE_ID = "c696d4cd39ca38022a4a0b18a47e0306"
LOCAL_PORT = 5000

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)
os.environ["FLASK_SKIP_DOTENV"] = "1"

# 读取 Token
token_file = os.path.join(SCRIPT_DIR, ".cftoken")
CF_TOKEN = None
if os.path.exists(token_file):
    with open(token_file) as f:
        CF_TOKEN = f.read().strip()


def update_page_rule(tunnel_url):
    """尝试更新 Cloudflare Page Rule"""
    if not CF_TOKEN:
        return None
    url = f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/pagerules/{PAGE_RULE_ID}"
    data = {
        "targets": [{"target": "url", "constraint": {"operator": "matches", "value": "donghuani.xyz/*"}}],
        "actions": [{"id": "forwarding_url", "value": {"url": f"{tunnel_url}/$1", "status_code": 301}}],
        "status": "active"
    }
    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(),
            headers={"Authorization": f"Bearer {CF_TOKEN}", "Content-Type": "application/json"},
            method="PUT"
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read())
        return result.get("success", False)
    except Exception:
        return None


def main():
    print("=" * 55)
    print("       东华倪家 — 家庭门户网站")
    print("=" * 55)

    # 1. 启动 cloudflared tunnel
    print("\n[1/3] Starting Cloudflare Tunnel...")
    tunnel_proc = subprocess.Popen(
        ["./cloudflared.exe", "tunnel", "--url", f"http://localhost:{LOCAL_PORT}"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1
    )

    # 2. 提取 tunnel URL
    tunnel_url = None
    for line in tunnel_proc.stdout:
        match = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
        if match:
            tunnel_url = match.group(1)
            break

    if not tunnel_url:
        print("[X] Failed to get Tunnel URL!")
        tunnel_proc.terminate()
        sys.exit(1)

    print(f"[OK] Tunnel: {tunnel_url}")

    # 3. 尝试更新域名
    print("[2/3] Updating donghuani.xyz...")
    result = update_page_rule(tunnel_url)

    if result is True:
        print(f"[OK] donghuani.xyz -> {tunnel_url}")
        print("     Domain auto-updated successfully!")
    elif result is False:
        print("[!] Auto-update failed (API permission issue)")
        print(f"     Please manually update Page Rule in Cloudflare:")
        print(f"     https://dash.cloudflare.com/ -> donghuani.xyz -> Rules -> Page Rules")
        print(f"     Change target URL to: {tunnel_url}/$1")
    else:
        print("[!] Cannot connect to Cloudflare API")
        print(f"     If donghuani.xyz doesn't work, update Page Rule manually:")
        print(f"     Target URL: {tunnel_url}/$1")

    # 4. 启动 Flask
    print(f"\n[3/3] Starting server...")
    print(f"  Local:   http://localhost:{LOCAL_PORT}")
    print(f"  Domain:  https://donghuani.xyz")
    print(f"  Tunnel:  {tunnel_url}")
    print("\nPress Ctrl+C to stop")
    print("=" * 55)

    flask_proc = subprocess.Popen(
        [sys.executable, "server.py"],
        env={**os.environ, "FLASK_SKIP_DOTENV": "1"}
    )
    flask_proc.wait()
    tunnel_proc.terminate()


if __name__ == "__main__":
    main()
