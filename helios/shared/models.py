"""Shared Pydantic models for Helios Core."""

from typing import Literal
from pydantic import BaseModel


class CommandRequest(BaseModel):
    """Voice/text command from user."""
    text: str


class Action(BaseModel):
    """Single action to execute."""
    type: Literal["sms", "call", "open_app", "set_alarm", "speak"]
    params: dict


class CommandResponse(BaseModel):
    """Processed command with actions."""
    text: str
    actions: list[Action]
    message: str
