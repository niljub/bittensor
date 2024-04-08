import secrets
from typing import Optional


def no_operation() -> None:
    """A no-operation function intended as a placeholder."""
    pass


NOOP = no_operation


def generate_request_token(
    prefix: Optional[str] = None, random_value_length: int = 6
) -> str:
    """
    Generates a token consisting of an optional prefix followed by a hyphen and a random alphanumeric string.
    If no prefix is provided, the hyphen is omitted.

    Parameters:
    - prefix: An optional string to prefix the token with. Default is None.
    - random_value_length: An integer specifying the length of the random part of the token. Default is 4.

    Returns:
    - A string token in the format "prefix-random_value" if a prefix is provided, otherwise "random_value" only.
    """
    characters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    random_value = "".join(
        secrets.choice(characters) for _ in range(random_value_length)
    )
    return f"{prefix}-{random_value}" if prefix else random_value
