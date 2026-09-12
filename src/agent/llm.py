import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.agent.models import AgentAction, Observation


load_dotenv()


class LLMClient:

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY is missing. Add it to the .env file."
            )

        self.model = os.getenv(
            "OPENAI_MODEL",
            "gpt-5.6-luna"
        )

        self.client = OpenAI(
            api_key=api_key
        )

    def decide(
        self,
        goal: str,
        observation: Observation
    ) -> AgentAction:

        prompt = self._build_prompt(
            goal,
            observation
        )

        response = self.client.responses.create(
            model=self.model,
            input=prompt
        )

        raw_text = response.output_text.strip()

        if raw_text.startswith("```"):
            raw_text = (
                raw_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        data = json.loads(raw_text)

        # Normalize finish results.
        # The model may occasionally return a simple string.
        if (
            data.get("action") == "finish"
            and data.get("result") is not None
            and not isinstance(data.get("result"), dict)
        ):
            data["result"] = {
                "value": data["result"]
            }

        return AgentAction.model_validate(
            data
        )

    def _build_prompt(
        self,
        goal: str,
        observation: Observation
    ) -> str:

        observation_json = (
            observation.model_dump_json(
                indent=2
            )
        )

        return f"""
You are controlling a business application through a restricted
computer-use interface.

Choose exactly ONE next action that moves toward the user's goal.

GOAL:
{goal}

CURRENT UI:
{observation_json}

Allowed actions:

type:
Enter text into a textbox.
Requires element_id and value.

click:
Click an interactive element.
Requires element_id.

read:
Use when visible information is relevant but the goal is not
yet complete.

wait:
Use when the application appears to still be loading.

finish:
Use only when the user's goal has been completed.
The result MUST always be a JSON object.

Example:
{{
  "action": "finish",
  "element_id": null,
  "value": null,
  "reasoning": "The requested savings balance is visible.",
  "result": {{
    "savings_balance": "$4820.35"
  }}
}}

escalate:
Use when you cannot safely determine what action to take.

Rules:

1. Choose exactly one action.
2. Use only element IDs present in CURRENT UI.
3. Never invent an element.
4. Do not output Playwright selectors.
5. Do not output Python or JavaScript.
6. Do not perform actions unrelated to the goal.
7. Consider the current value of each UI element before acting.
8. Do not type a value again if that value is already present.
9. If the information requested by the goal is visible, use finish.
10. For finish, result MUST be a JSON object, never a plain string.
11. Return JSON only.

For a normal interaction, use this structure:

{{
  "action": "type",
  "element_id": "e1",
  "value": "example",
  "reasoning": "Short explanation.",
  "result": null
}}
"""