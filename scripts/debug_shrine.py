#!/usr/bin/env python3
"""
Debug shrine scraper — run this to see exactly what the API returns.

    docker compose run --rm -v $(pwd)/scripts:/scripts backend python /scripts/debug_shrine.py
"""
import asyncio
import sys
import json

async def main():
    try:
        import httpx
    except ImportError:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "--quiet"])
        import httpx

    urls = [
        "https://dbd.tricky.lol/api/shrine",
        "https://dbd.tricky.lol/api/shrine/current",
        "https://dbd.tricky.lol/api/v1/shrine",
        "https://dbd.tricky.lol/shrine",
    ]

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        for url in urls:
            print(f"\n{'='*50}")
            print(f"GET {url}")
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                print(f"Status: {resp.status_code}")
                print(f"Content-Type: {resp.headers.get('content-type','')}")
                body = resp.text[:2000]
                print(f"Body:\n{body}")
            except Exception as e:
                print(f"Error: {e}")

asyncio.run(main())