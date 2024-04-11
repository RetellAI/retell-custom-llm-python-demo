from typing import Any, List, Optional, Literal
from pydantic import BaseModel

class Utterance(BaseModel):
    role: Literal["agent", "user", "system"]
    content: str

class CustomLlmRequest(BaseModel):
    interaction_type: Literal["update_only", "response_required", "reminder_required", "ping_pong", "call_details"]
    response_id: Optional[int] = 0 # Used by response_required and reminder_required
    transcript: Optional[List[Any]] = [] # Used by response_required and reminder_required
    call: Optional[dict] = None # Used by call_details
    timestamp: Optional[int] = None # Used by ping_pong

class CustomLlmResponse(BaseModel):
    response_type: Literal["response", "config", "ping_pong"] = "response"
    response_id: Optional[int] = None # Used by response
    content: Any = None # Used by response
    content_complete: Optional[bool] = False # Used by response
    end_call: Optional[bool] = False # Used by response
    config: Optional[dict] = None # Used by config
    timestamp: Optional[int] = None # Used by ping_pong
