#!/usr/bin/env python3
"""Generate a symmetric encryption key for session persistence."""

from cryptography.fernet import Fernet

def main() -> None:
    """Generate and print a new Fernet key."""
    key = Fernet.generate_key()
    print("Your new SESSION_ENCRYPTION_KEY is:")
    print("-" * 50)
    print(key.decode("utf-8"))
    print("-" * 50)
    print("Add this to your config/.env file.")

if __name__ == "__main__":
    main()
