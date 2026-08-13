import hashlib
import hmac
import secrets

_ALGORITHM = "sha256"
_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest_hex = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac(_ALGORITHM, password.encode("utf-8"), bytes.fromhex(salt), _ITERATIONS)
    return hmac.compare_digest(check.hex(), digest_hex)
