from enum import Enum
from typing import Optional

from pydantic import BaseModel


class ActionType(str, Enum):
    CLICK = "click"
    TYPE = "type"
    READ = "read"
    WAIT = "wait"
    FINISH = "finish"
    ESCALATE = "escalate"


class UIElement(BaseModel):
    element_id: str
    role: str
    name: str
    selector: str
    value: Optional[str] = None


class Observation(BaseModel):
    url: str
    title: str
    text: str
    elements: list[UIElement]


class AgentAction(BaseModel):
    action: ActionType
    element_id: Optional[str] = None
    value: Optional[str] = None
    reasoning: str
    result: Optional[dict] = None