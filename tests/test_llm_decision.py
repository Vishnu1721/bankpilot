from src.agent.llm import LLMClient
from src.surface.browser import BrowserSurface


GOAL = (
    "Look up member 10023 and return "
    "their current savings balance."
)


surface = BrowserSurface(headless=False)

try:
    surface.start()

    surface.navigate(
        "http://127.0.0.1:5001"
    )

    observation = surface.observe()

    print("\nGOAL")
    print("----")
    print(GOAL)

    print("\nCURRENT UI")
    print("----------")
    print(
        observation.model_dump_json(
            indent=2
        )
    )

    llm = LLMClient()

    decision = llm.decide(
        GOAL,
        observation
    )

    print("\nLLM DECISION")
    print("------------")
    print(
        decision.model_dump_json(
            indent=2
        )
    )

finally:
    surface.close()