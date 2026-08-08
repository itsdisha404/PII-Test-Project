from __future__ import annotations

from typing import TypedDict, List


class EligibilityResult(TypedDict):
    eligible: bool
    reasons: List[str]


def check_eligibility(age: int, email: str) -> EligibilityResult:
    """Ground-truth eligibility check. Runs on de-anonymized real values.

    Eligible if age > 18 AND email ends with '@gmail.com'.
    """
    is_adult = age > 18
    is_gmail = email.strip().lower().endswith("@gmail.com")
    eligible = is_adult and is_gmail

    reasons: List[str] = []
    if not is_adult:
        reasons.append("age must be greater than 18")
    if not is_gmail:
        reasons.append("email must end with @gmail.com")
    if not reasons:
        reasons.append("meets all eligibility criteria")

    return {"eligible": eligible, "reasons": reasons}


ELIGIBILITY_TOOL = {
    "type": "function",
    "function": {
        "name": "check_eligibility",
        "description": (
            "Determine if a user is eligible. A user is eligible only if "
            "age is greater than 18 AND their email address ends with "
            "'@gmail.com'. Call this whenever you have both pieces of "
            "information, even if the email is a partially masked value "
            "such as 'p****@g*****.com' instead of a real email address "
            "-- pass it through exactly as given."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "age": {
                    "type": "integer",
                    "description": "The user's age in years.",
                },
                "email": {
                    "type": "string",
                    "description": (
                        "The user's email address, or a masked placeholder "
                        "like <EMAIL_ADDRESS_1> if it was anonymized in the "
                        "conversation."
                    ),
                },
            },
            "required": ["age", "email"],
        },
    },
}