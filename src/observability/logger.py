import json
from datetime import datetime, timezone
from pathlib import Path


class EventLogger:

    SENSITIVE_KEYS = {
        "password",
        "secret",
        "token",
        "api_key",
        "member_id",
        "account_number",
        "ssn"
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

                if any(
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

        return value