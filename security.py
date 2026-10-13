import hashlib
import hmac
import os
import re
import secrets


class AuthorizationError(PermissionError):
    """Raised when a caller does not have permission for an operation."""


def hash_password(password):
    salt = os.urandom(16)
    iterations = 310_000
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    parts = stored_hash.split("$")
    if len(parts) == 4 and parts[0] == "pbkdf2_sha256":
        _, iterations, salt, expected = parts
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), expected), False

    legacy_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_hash, stored_hash), True


def validate_roll_number(value):
    roll_number = value.strip()
    pattern = os.getenv("ROLL_NUMBER_REGEX", "")
    if pattern and not re.fullmatch(pattern, roll_number):
        raise ValueError("Roll number does not match the configured college format.")
    return roll_number or None


def roll_number_uniqueness_enabled():
    return os.getenv("ROLL_NUMBER_UNIQUE", "false").strip().lower() == "true"


def create_qr_token():
    return secrets.token_urlsafe(32)


def hash_qr_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
