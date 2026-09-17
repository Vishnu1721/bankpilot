import re
from urllib.parse import unquote


class ArtifactMetadataViolation(ValueError):
    """Raised when UI-derived metadata is unsafe to persist or replay."""


class ArtifactMetadataGuard:
    """Fail-closed validator for strings copied from an untrusted UI.

    Replacing sensitive text inside a locator would create a capability that
    cannot be replayed safely. Unsafe metadata is therefore rejected and must
    be reviewed or replaced with a stable, non-customer-specific locator.
    """

    SENSITIVE_PATTERNS = (
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)",
        r"\$\s?\d[\d,]*(?:\.\d{2})?",
        r"\b(?:member|customer|account|routing|tax|case)\s*"
        r"(?:number|id|#)?\s*[:=\-]?\s*[A-Z0-9-]*\d[A-Z0-9-]{3,}\b",
        r"(?<![\d.])\d{5,19}(?![\d.])",
    )

    # Common application vocabulary is permitted. Two title-cased words not
    # composed from this vocabulary are treated as a likely person's name.
    SAFE_TITLE_WORDS = {
        "Account", "Address", "Admin", "Amount", "Application", "Authentication",
        "Balance", "Bank", "Cash", "Change", "Checking", "Complete", "Confirmation",
        "Continue", "Create", "Credit", "Current", "Customer", "Deposit",
        "Details", "Email", "Holiday", "Home", "Id", "Information", "Legacy",
        "Lookup", "Manual", "Member", "Memo", "New", "Number", "Open",
        "Operations", "Payment", "Phone", "Prepare", "Profile", "Required",
        "Result", "Return", "Review", "Savings", "Search", "Select", "Status",
        "Sub", "Transaction", "Type", "Union", "Verification", "View",
        "Workflow",
    }

    def __init__(self, parameter_values=None):
        self.parameter_values = tuple(
            str(value).strip()
            for value in (parameter_values or ())
            if value is not None and len(str(value).strip()) >= 3
        )

    def validate(self, value, field_name):
        if value is None:
            return None
        if not isinstance(value, str):
            raise ArtifactMetadataViolation(
                f"Artifact metadata '{field_name}' must be text."
            )

        decoded = unquote(value)
        for parameter_value in self.parameter_values:
            if parameter_value in decoded:
                self._reject(field_name, "contains a runtime parameter value")

        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, decoded, re.IGNORECASE):
                self._reject(field_name, "contains sensitive-looking UI data")

        for match in re.finditer(
            r"(?=\b([A-Z][a-z]{1,})\s+([A-Z][a-z]{1,})\b)", decoded
        ):
            first, second = match.groups()
            if first not in self.SAFE_TITLE_WORDS and second not in self.SAFE_TITLE_WORDS:
                self._reject(field_name, "contains a likely person name")

        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
            self._reject(field_name, "contains control characters")
        return value

    @staticmethod
    def _reject(field_name, reason):
        raise ArtifactMetadataViolation(
            f"Refusing to persist UI-derived artifact metadata: "
            f"'{field_name}' {reason}. Use a stable generic target and request review."
        )
