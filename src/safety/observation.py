import re

from src.agent.models import Observation, UIElement
from src.safety.policy import SafetyViolation


class UntrustedObservationGuard:
    """Sanitizes UI-derived data and blocks likely prompt injection."""

    INSTRUCTION_PATTERNS = (
        r"ignore (all |any )?(previous|prior|system) instructions",
        r"(system|developer) message",
        r"reveal (the )?(prompt|secret|api key|credentials)",
        r"(run|execute) (this )?(command|code|script)",
        r"you are (now|an? )",
        r"do not trust the user",
    )

    def __init__(self, max_text_chars=8000, max_elements=100, max_field_chars=300):
        self.max_text_chars = max_text_chars
        self.max_elements = max_elements
        self.max_field_chars = max_field_chars

    def sanitize(self, observation: Observation) -> Observation:
        text = self._clean(observation.text, self.max_text_chars)
        elements = [
            UIElement(
                element_id=element.element_id,
                role=self._clean(element.role, 50),
                name=self._clean(element.name, self.max_field_chars),
                selector=element.selector,
                value=self._clean(element.value, self.max_field_chars)
                if element.value is not None else None,
            )
            for element in observation.elements[:self.max_elements]
        ]

        candidate = " ".join(
            [text, observation.title]
            + [element.name for element in elements]
        ).lower()

        for pattern in self.INSTRUCTION_PATTERNS:
            if re.search(pattern, candidate, re.IGNORECASE):
                raise SafetyViolation(
                    "Untrusted UI content resembles instructions to the agent; "
                    "discovery was stopped for human review."
                )

        return Observation(
            url=observation.url,
            title=self._clean(observation.title, 200),
            text=text,
            elements=elements,
            trust="untrusted_ui_data",
        )

    @staticmethod
    def _clean(value, limit):
        value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", " ", value or "")
        value = re.sub(r"\s+", " ", value).strip()
        return value[:limit]
