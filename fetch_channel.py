#!/usr/bin/env python3
"""Fetch a Bale channel's posts/messages with a user session (bale-sdk).

Usage:
    python3 login.py 989123456789          # once, saves .bale_token
    python3 fetch_channel.py @irantimes_com --limit 50
    python3 fetch_channel.py @irantimes_com --limit 200 --out posts.json
"""

import argparse
import asyncio
import dataclasses
import datetime as dt
import json
import pathlib
import sys
import typing

from bale import BaleClient

TOKEN_FILE = pathlib.Path(__file__).with_name(".bale_token")


def to_jsonable(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: to_jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    return str(obj)


def message_dict(msg) -> dict:
    d = to_jsonable(msg)
    ts = msg.date / 1000 if msg.date > 10**11 else msg.date  # Bale uses ms
    d["date_iso"] = dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()
    return d


async def fetch(channel: str, limit: int) -> dict:
    token = TOKEN_FILE.read_text().strip() if TOKEN_FILE.exists() else None
    token = token or __import__("os").environ.get("BALE_USER_TOKEN")
    if not token:
        sys.exit("error: no user token, run `python3 login.py <phone>` first")

    async with BaleClient(token) as client:
        me = await client.get_me()
        chat = await client.get_entity(channel)

        info = {
            "fetched_by": to_jsonable(me),
            "channel": to_jsonable(chat),
            "messages": [],
        }
        async for msg in client.iter_messages(chat, limit=limit):
            info["messages"].append(message_dict(msg))
        return info


def main():
    parser = argparse.ArgumentParser(description="Fetch Bale channel messages (user client)")
    parser.add_argument("channel", help="@username or numeric id")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", help="write JSON here")
    args = parser.parse_args()

    info = asyncio.run(fetch(args.channel, args.limit))

    print(f"channel: {info['channel'].get('title')} (@{info['channel'].get('username')}) "
          f"members={info['channel'].get('members_count')}")
    print(f"fetched {len(info['messages'])} messages\n")

    for m in info["messages"][:10]:
        text = (m["content"].get("text") or "")[:100].replace("\n", " ")
        print(f"  #{m['rid']} {m['date_iso']} [{m['content'].get('kind')}] {text}")

    if args.out:
        pathlib.Path(args.out).write_text(
            json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nsaved -> {args.out}")


if __name__ == "__main__":
    main()
