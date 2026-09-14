import json
import re
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class CapabilityStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    RETIRED = "retired"


class CapabilityEntry(BaseModel):
    capability_id: str
    version: str = "1.0.0"
    status: CapabilityStatus = CapabilityStatus.DRAFT
    artifact_path: str
    tenant_id: str = "default"
    application: str
    intents: list[str] = Field(default_factory=list)
    approved_by: str | None = None


class CapabilityRegistry:
    """File-backed catalog and approval lifecycle for recorded capabilities."""

    def __init__(self, path="config/capability_registry.json"):
        self.path = Path(path)
        self.entries = self._load()

    def register(self, entry):
        replacement = entry.model_copy(update={"status": CapabilityStatus.DRAFT})
        self.entries = [
            current for current in self.entries
            if not self._same_version(current, replacement)
        ]
        self.entries.append(replacement)
        self._save()
        return replacement

    def approve(self, capability_id, tenant_id="default", approved_by="operator"):
        entry = self._find(capability_id, tenant_id)
        if entry is None:
            raise KeyError(f"Capability not found: {capability_id}")
        updated = entry.model_copy(update={
            "status": CapabilityStatus.APPROVED,
            "approved_by": approved_by,
        })
        self.entries[self.entries.index(entry)] = updated
        self._save()
        return updated

    def match(self, goal, tenant_id="default", application=None):
        candidates = [
            entry for entry in self.entries
            if entry.tenant_id == tenant_id
            and entry.status != CapabilityStatus.RETIRED
            and (application is None or entry.application == application)
        ]
        scored = [(self._score(goal, entry.intents), entry) for entry in candidates]
        scored = [item for item in scored if item[0] >= 0.60]
        if not scored:
            return None
        return max(scored, key=lambda item: item[0])[1]

    def _find(self, capability_id, tenant_id):
        matches = [
            entry for entry in self.entries
            if entry.capability_id == capability_id and entry.tenant_id == tenant_id
        ]
        return matches[-1] if matches else None

    def _load(self):
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [CapabilityEntry.model_validate(item) for item in data]

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [entry.model_dump(mode="json") for entry in self.entries]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _same_version(left, right):
        return (
            left.capability_id,
            left.version,
            left.tenant_id,
        ) == (
            right.capability_id,
            right.version,
            right.tenant_id,
        )

    @classmethod
    def _score(cls, goal, intents):
        goal_tokens = cls._tokens(goal)
        best = 0.0
        for intent in intents:
            intent_tokens = cls._tokens(intent)
            if not intent_tokens:
                continue
            overlap = len(goal_tokens & intent_tokens)
            best = max(best, overlap / len(intent_tokens))
        return best

    @staticmethod
    def _tokens(text):
        ignored = {
            "a", "an", "and", "for", "from", "member", "please", "the",
            "their", "this", "to", "with",
        }
        return {
            token for token in re.findall(r"[a-z]+", text.lower())
            if token not in ignored
        }

