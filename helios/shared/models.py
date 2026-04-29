"""Shared Pydantic models for Helios Core."""

from typing import Literal, Optional
from pydantic import BaseModel


class CommandRequest(BaseModel):
    """Voice/text command from user."""
    text: str
    session_id: Optional[str] = None


class Action(BaseModel):
    """Single action to execute."""
    type: Literal[
        "sms", "call", "open_app", "set_alarm", "speak",
        "email", "calendar_add", "reminder", "web_search", "weather"
    ]
    params: dict
    confirmation_required: bool = False


class CommandResponse(BaseModel):
    """Processed command with actions."""
    text: str
    actions: list[Action]
    message: str
    confirmation_required: bool = False


class Contact(BaseModel):
    """Phone contact."""
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    aliases: list[str] = []


class Profile(BaseModel):
    """User profile and preferences."""
    name: Optional[str] = None
    location: Optional[str] = None
    timezone: str = "UTC"
    preferences: dict = {}
