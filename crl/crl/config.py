# Username Sanitiziation
USER_ALLOWED_REGEX = "^[A-Za-z0-9]+$$"
USER_MAX_LEN = 32
USER_MIN_LEN = 4
USER_CASE_SENSITIVE = False
MAGIC_PASSWORD_VALUE = (
    "crl{PASSWORD}"  # Pick a password from a curated rockyou.txt list (removed space, : and non ascii)
)
