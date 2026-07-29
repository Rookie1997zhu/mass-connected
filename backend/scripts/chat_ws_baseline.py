#!/usr/bin/env python3
"""轻量 WebSocket 并发基线脚本（本地/压测机运行）。

用法示例（需有效一次性 ticket）:
  python scripts/chat_ws_baseline.py --url ws://localhost/ws/chat/ --ticket TICKET --connections 100

容量公式（文档）:
  目标在线 N ≈ 单副本舒适连接数 C × 副本数 R
  建议 C=2000～5000（以压测为准），则 1 万在线约需 R=ceil(10000/C) 个 chat-ws 副本。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time


async def one_connection(url: str, ticket: str, hold_seconds: float, results: list):
    try:
        import websockets
    except ImportError:
        results.append(("error", "websockets package missing"))
        return
    full = f"{url}?ticket={ticket}"
    t0 = time.perf_counter()
    try:
        async with websockets.connect(full, open_timeout=10) as ws:
            # 等待 connected 或超时
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=5)
                data = json.loads(raw)
                if data.get("event") != "connected":
                    results.append(("unexpected", data.get("event")))
                    return
            except asyncio.TimeoutError:
                results.append(("timeout", "no connected event"))
                return
            await asyncio.sleep(hold_seconds)
            results.append(("ok", time.perf_counter() - t0))
    except Exception as exc:  # noqa: BLE001
        results.append(("error", str(exc)))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://localhost/ws/chat/")
    parser.add_argument("--ticket", required=True)
    parser.add_argument("--connections", type=int, default=50)
    parser.add_argument("--hold", type=float, default=3.0)
    args = parser.parse_args()

    results: list = []
    tasks = [
        one_connection(args.url, args.ticket, args.hold, results)
        for _ in range(args.connections)
    ]
    t0 = time.perf_counter()
    await asyncio.gather(*tasks)
    elapsed = time.perf_counter() - t0
    ok = sum(1 for r in results if r[0] == "ok")
    print(f"connections={args.connections} ok={ok} elapsed_s={elapsed:.2f}")
    errors = [r for r in results if r[0] != "ok"]
    if errors[:5]:
        print("sample_errors:", errors[:5])
    # 副本估算提示
    print("scale_hint: replicas ≈ ceil(target_online / measured_per_replica_ok)")
    return 0 if ok == args.connections else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
