from typing import Any, List, Optional, Literal
from pydantic import BaseModel

class Utterance(BaseModel):
    role: Literal["agent", "user", "system"]
    content: str

class CustomLlmRequest(BaseModel):
    interaction_type: Literal["update_only", "response_required", "reminder_required", "pingpong", "call_details"]
    response_id: Optional[int] = 0
    transcript: Optional[List[Any]] = []
    content: Any = None

class CustomLlmResponse(BaseModel):
    response_type: Literal["response", "config", "pingpong"] = "response"
    response_id: Optional[int] = None
    content: Any = None
    content_complete: Optional[bool] = False
    end_call: Optional[bool] = False
