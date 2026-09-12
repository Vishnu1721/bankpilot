from src.agent.models import (
    ActionType,
    AgentAction,
    Observation,
    UIElement
)

from src.safety.policy import (
    SafetyPolicy,
    SafetyViolation
)


policy = SafetyPolicy()


print(
    "\nTEST 1: Allowed domain"
)
print("----------------------")

policy.check_url(
    "http://127.0.0.1:5001"
)

print("PASS")


print(
    "\nTEST 2: Blocked domain"
)
print("----------------------")

try:
    policy.check_url(
        "https://example.com"
    )

    print("FAIL")

except SafetyViolation as error:
    print(
        f"PASS - {error}"
    )


print(
    "\nTEST 3: Safe click"
)
print("------------------")

observation = Observation(
    url="http://127.0.0.1:5001",
    title="LegacyBank Admin",
    text="Member Search",
    elements=[
        UIElement(
            element_id="e1",
            role="button",
            name="Search",
            selector=(
                'button[type="submit"]'
            )
        )
    ]
)

safe_action = AgentAction(
    action=ActionType.CLICK,
    element_id="e1",
    reasoning="Search for member."
)

policy.check_action(
    safe_action,
    observation
)

print("PASS")


print(
    "\nTEST 4: Risky click"
)
print("-------------------")

risky_observation = Observation(
    url="http://127.0.0.1:5001",
    title="Account",
    text="Delete Account",
    elements=[
        UIElement(
            element_id="e1",
            role="button",
            name="Delete Account",
            selector="#delete-account"
        )
    ]
)

risky_action = AgentAction(
    action=ActionType.CLICK,
    element_id="e1",
    reasoning="Delete the account."
)

try:
    policy.check_action(
        risky_action,
        risky_observation
    )

    print("FAIL")

except SafetyViolation as error:
    print(
        f"PASS - {error}"
    )