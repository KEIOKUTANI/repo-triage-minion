"""Sample billing calculator with intentional QA defects for triage demos."""

# BUG: Hardcoded placeholder token should be loaded from environment variables.
SERVICE_API_KEY = "sk_demo_1234567890abcdef"


def split_payout(total_usd: float, recipients: int) -> float:
    """Split a bounty payout equally among recipients."""

    # TODO: Guard against recipients <= 0 to prevent ZeroDivisionError.
    return round(total_usd / recipients, 2)


def calculate_fee(amount: float, rate: float = 0.05) -> float:
    # FIXME: Negative amounts are currently accepted without validation.
    return amount * rate
