#!/usr/bin/env python3
"""One-time Bale user login (phone OTP) -> saves JWT to .bale_token.

This is a *user* session (like Telethon), NOT the bot token.
The bot API cannot read channel history; a user client can.

Usage:
    python3 login.py 989123456789
"""

import pathlib
import sys

from bale import auth

TOKEN_FILE = pathlib.Path(__file__).with_name(".bale_token")


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python3 login.py <phone in international format, e.g. 989123456789>")
    phone = int(sys.argv[1])

    session = auth.start_phone_auth(phone)
    print(f"SMS code sent (registered={session.is_registered})")
    code = input("enter the code: ").strip()

    result = auth.validate_code(session.transaction_hash, code)
    TOKEN_FILE.write_text(result.access_token + "\n")
    TOKEN_FILE.chmod(0o600)
    print(f"logged in as user_id={result.user_id} name={result.user_name!r}")
    print(f"token saved -> {TOKEN_FILE}")


if __name__ == "__main__":
    main()
