#!/usr/bin/env python3
"""Generate a Fernet encryption key."""

from cryptography.fernet import Fernet

if __name__ == "__main__":
    key = Fernet.generate_key()
    print(f"ENCRYPTION_KEY={key.decode()}")
