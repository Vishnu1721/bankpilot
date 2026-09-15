import re

from src.capability.models import SuccessConditionType


def verify_observation_checkpoint(condition, observation):
    if condition.type == SuccessConditionType.TEXT_PRESENT:
        matched = condition.value in observation.text
    elif condition.type == SuccessConditionType.TITLE_EQUALS:
        matched = observation.title == condition.value
    elif condition.type == SuccessConditionType.URL_MATCHES:
        matched = re.fullmatch(condition.value, observation.url) is not None
    else:  # Defensive; model validation already rejects unknown types.
        raise ValueError(f"Unsupported success condition: {condition.type}")
    if not matched:
        raise RuntimeError(
            f"Discovery finish rejected: checkpoint {condition.type.value}="
            f"{condition.value!r} does not match the observed UI."
        )
