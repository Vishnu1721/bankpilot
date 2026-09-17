import json
import re
from datetime import datetime, timezone
from pathlib import Path


class EventLogger:

    SAFE_STRUCTURED_KEYS = {
        "human_action_type",
    }

    SENSITIVE_KEYS = {
        "password",
        "secret",
        "token",
        "api_key",
        "member_id",
        "account_number",
        "ssn",
        "outputs",
        "value",
        "human_action",
        "observed",
    }

    def __init__(
        self,
        path
    ):
        self.path = Path(path)

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.path.write_text(
            "",
            encoding="utf-8"
        )

    def log(
        self,
        event,
        **data
    ):
        record = {
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
            "event": event,
            **self._redact(data)
        }

        with self.path.open(
            "a",
            encoding="utf-8"
        ) as file:
            file.write(
                json.dumps(record)
            )
            file.write("\n")

    def _redact(
        self,
        value
    ):
        if isinstance(value, dict):
            result = {}

            for key, item in value.items():
                normalized_key = (
                    key.lower()
                )

                if normalized_key in self.SAFE_STRUCTURED_KEYS:
                    result[key] = self._redact(item)
                elif any(
                    sensitive
                    in normalized_key
                    for sensitive
                    in self.SENSITIVE_KEYS
                ):
                    result[key] = "[REDACTED]"

                else:
                    result[key] = (
                        self._redact(item)
                    )

            return result

        if isinstance(value, list):
            return [
                self._redact(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [self._redact(item) for item in value]

        if isinstance(value, str):
            patterns = (
                (r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]"),
                (r"\$\s?\d[\d,]*(?:\.\d{2})?", "[REDACTED_AMOUNT]"),
                (r"\b\d{5,19}\b", "[REDACTED_NUMBER]"),
                (r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b", "[REDACTED_NAME]"),
            )
            for pattern, replacement in patterns:
                value = re.sub(pattern, replacement, value)
            return value

        return value
