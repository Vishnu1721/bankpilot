from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

from src.capability.registry import CapabilityEntry, CapabilityStatus


class RouteMode(str, Enum):
    REPLAYED = "replayed"
    DISCOVERY_REQUIRED = "discovery_required"
    DRAFT_CREATED = "draft_created"
    APPROVAL_REQUIRED = "approval_required"


class RouteResult(BaseModel):
    mode: RouteMode
    capability_id: str | None = None
    artifact_path: str | None = None
    message: str
    outputs: dict = Field(default_factory=dict)
    replay_status: str | None = None
    code: str | None = None


class CapabilityRouter:
    """Replay approved matches; send unknown goals through bounded discovery."""

    def __init__(self, registry, replay_engine):
        self.registry = registry
        self.replay_engine = replay_engine

    def execute(
        self,
        goal,
        inputs,
        tenant_id="default",
        application="LegacyBank Credit Union",
        discovery_agent=None,
        artifact_path=None,
    ):
        entry = self.registry.match(goal, tenant_id, application)
        if entry and entry.status == CapabilityStatus.APPROVED:
            capability = self.replay_engine.load_capability(entry.artifact_path)
            replay = self.replay_engine.run(capability, inputs)
            return RouteResult(
                mode=RouteMode.REPLAYED,
                capability_id=entry.capability_id,
                artifact_path=entry.artifact_path,
                message=replay.message,
                outputs=replay.outputs,
                replay_status=replay.status.value,
                code=replay.code,
            )

        if entry:
            return RouteResult(
                mode=RouteMode.APPROVAL_REQUIRED,
                capability_id=entry.capability_id,
                artifact_path=entry.artifact_path,
                message="A matching capability exists but is not approved for replay.",
            )

        if discovery_agent is None:
            return RouteResult(
                mode=RouteMode.DISCOVERY_REQUIRED,
                message="No matching capability exists; bounded LLM discovery is required.",
            )

        if not artifact_path:
            raise ValueError("artifact_path is required when discovery is enabled.")

        discovery_agent.run(
            goal=goal,
            artifact_path=artifact_path,
            parameters=inputs,
        )
        capability = self.replay_engine.load_capability(artifact_path)
        entry = self.registry.register(CapabilityEntry(
            capability_id=capability.capability_id,
            artifact_path=str(Path(artifact_path)),
            tenant_id=tenant_id,
            application=application,
            intents=[goal],
        ))
        return RouteResult(
            mode=RouteMode.DRAFT_CREATED,
            capability_id=entry.capability_id,
            artifact_path=entry.artifact_path,
            message="Discovery completed and created a draft capability for human review.",
        )
