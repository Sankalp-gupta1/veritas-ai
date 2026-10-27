"""Set a new encryption key in a local ignored .env without printing it.

Never replaces an existing nonempty key. Back up .env privately before storing
important content; neither Git nor the database can recover a lost vault key.
"""

import base64
import os
import secrets
from pathlib import Path

from dotenv import dotenv_values, set_key

path = Path(__file__).resolve().parents[1] / ".env"
if not path.exists():
    path.write_text((path.parent / ".env.example").read_text())
if dotenv_values(path).get("VERITAS_VAULT_KEY"):
    print("A vault key already exists. It was not changed.")
else:
    set_key(path, "VERITAS_VAULT_KEY", base64.b64encode(secrets.token_bytes(32)).decode())
    if os.name != "nt":
        path.chmod(0o600)
    print("Vault key saved privately in .env. Keep a secure backup; never commit or share it.")
