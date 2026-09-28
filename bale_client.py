#!/usr/bin/env python3
"""Bale channel-data fetcher (POC).

Docs: https://docs.bale.ai/
API is Telegram-compatible: https://tapi.bale.ai/bot<token>/<METHOD>

Usage:
    export BALE_TOKEN="123456:ABC..."
    python bale_client.py @mychannel
    python bale_client.py -1001234567890 --out channel.json
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://tapi.bale.ai"


class BaleAPIError(Exception):
    def __init__(self, method, payload):
        self.method = method
        self.payload = payload
        super().__init__(
            f"{method} failed: {payload.get('error_code')} {payload.get('description')}"
        )


class BaleClient:
    def __init__(self, token, timeout=30):
        if not token:
            raise ValueError("token is required")
        self.token = token
        self.timeout = timeout

    def call(self, method, http="POST", **params):
        url = f"{BASE_URL}/bot{self.token}/{method}"
        # drop None params so the API applies its defaults
        params = {k: v for k, v in params.items() if v is not None}

        if http == "GET":
            url = f"{url}?{urllib.parse.urlencode(params)}"
            data = None
            req = urllib.request.Request(url, data=data, method="GET")
        else:
            data = json.dumps(params).encode()
            req = urllib.request.Request(
                url,
                data=data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = json.loads(e.read().decode())
        except urllib.error.URLError as e:
            raise BaleAPIError(method, {"description": str(e.reason)}) from e

        if not body.get("ok"):
            raise BaleAPIError(method, body)
        return body["result"]

    def get_me(self):
        return self.call("getMe")

    def get_chat(self, chat_id):
        return self.call("getChat", chat_id=chat_id)

    def get_chat_members_count(self, chat_id):
        return self.call("getChatMembersCount", chat_id=chat_id)

    def get_chat_administrators(self, chat_id):
        return self.call("getChatAdministrators", chat_id=chat_id)

    def get_chat_member(self, chat_id, user_id):
        return self.call("getChatMember", chat_id=chat_id, user_id=user_id)

    def export_chat_invite_link(self, chat_id):
        return self.call("exportChatInviteLink", chat_id=chat_id)

    def fetch_channel(self, channel, include_invite_link=False):
        """Collect everything the API exposes about a channel."""
        chat_id = self._resolve_chat_id(channel)
        data = {"chat": self.get_chat(chat_id)}

        try:
            data["members_count"] = self.get_chat_members_count(chat_id)
        except BaleAPIError as e:
            data["members_count"] = {"error": str(e)}

        try:
            data["administrators"] = self.get_chat_administrators(chat_id)
        except BaleAPIError as e:
            data["administrators"] = {"error": str(e)}

        if include_invite_link:
            try:
                data["invite_link"] = self.export_chat_invite_link(chat_id)
            except BaleAPIError as e:
                data["invite_link"] = {"error": str(e)}

        return data

    @staticmethod
    def _resolve_chat_id(channel):
        # "@name" or numeric id pass through; bare "name" gets an "@"
        if isinstance(channel, int):
            return channel
        channel = channel.strip()
        if channel.lstrip("-").isdigit():
            return int(channel)
        return channel if channel.startswith("@") else f"@{channel}"


def main():
    parser = argparse.ArgumentParser(description="Fetch Bale channel data (POC)")
    parser.add_argument("channel", help="@username, bare username, or numeric chat id")
    parser.add_argument("--token", default=os.environ.get("BALE_TOKEN"),
                        help="bot token (or set BALE_TOKEN)")
    parser.add_argument("--invite-link", action="store_true",
                        help="also export the channel invite link")
    parser.add_argument("--bot", action="store_true",
                        help="print bot identity (getMe) first")
    parser.add_argument("--out", help="write raw JSON to this file")
    args = parser.parse_args()

    if not args.token:
        sys.exit("error: no token, use --token or set BALE_TOKEN")

    client = BaleClient(args.token)

    if args.bot:
        print(json.dumps(client.get_me(), ensure_ascii=False, indent=2))

    try:
        data = client.fetch_channel(args.channel, include_invite_link=args.invite_link)
    except BaleAPIError as e:
        sys.exit(f"error: {e}")

    text = json.dumps(data, ensure_ascii=False, indent=2)
    print(text)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"\nsaved -> {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
