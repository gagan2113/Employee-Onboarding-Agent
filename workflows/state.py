from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain.schema import BaseMessage
from dataclasses import dataclass
from enum import Enum

class OnboardingStep(Enum):
    WELCOME = "welcome"
    COLLECT_INFO = "collect_info"
    SHARE_POLICIES = "share_policies"
    TOOL_ACCESS = "tool_access"
    CULTURE_INTRO = "culture_intro"
    ASSIGN_MENTOR = "assign_mentor"
    TRACK_PROGRESS = "track_progress"
    COLLECT_FEEDBACK = "collect_feedback"
    COMPLETION = "completion"

@dataclass
class OnboardingState:
    user_id: str
    current_step: OnboardingStep
    user_info: Dict[str, Any]
    completed_steps: List[OnboardingStep]
    messages: List[BaseMessage]
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_step": self.current_step.value,
            "user_info": self.user_info,
            "completed_steps": [step.value for step in self.completed_steps],
            "context": self.context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OnboardingState":
        return cls(
            user_id=data["user_id"],
            current_step=OnboardingStep(data["current_step"]),
            user_info=data.get("user_info", {}),
            completed_steps=[OnboardingStep(step) for step in data.get("completed_steps", [])],
            messages=data.get("messages", []),
            context=data.get("context", {})
        )
