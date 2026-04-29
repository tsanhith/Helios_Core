"""NVIDIA NIM LLM client for intent parsing."""

import json
import os
from openai import OpenAI

from shared.config import Config


SYSTEM_PROMPT = """You are Helios, a voice assistant that parses user commands into structured JSON actions.

Available action types:
- sms: Send SMS. params: {"contact": str, "message": str}
- call: Make phone call. params: {"contact": str}
- open_app: Open an app. params: {"app": str}
- speak: Speak text to user. params: {"text": str}
- email: Send email. params: {"recipient": str, "subject": str, "body": str}
- calendar_add: Add calendar event. params: {"title": str, "datetime": str (ISO format), "duration_minutes": int}
- reminder: Set reminder. params: {"text": str, "datetime": str (ISO format)}
- web_search: Search the web. params: {"query": str, "source": str (optional, e.g. "google", "ddg")}

{context}

Respond ONLY with a JSON object in this format:
{
    "actions": [{"type": "action_name", "params": {...}}],
    "message": "What to say to user",
    "confirmation_required": false
}

Set confirmation_required to true for sensitive actions: call, sms, email.

Examples:
Input: "Message John"
{"actions": [{"type": "sms", "params": {"contact": "John", "message": ""}}], "message": "Who do you want to message?", "confirmation_required": false}

Input: "Call mum"
{"actions": [{"type": "call", "params": {"contact": "mum"}}], "message": "Calling mum", "confirmation_required": true}

Input: "Open Spotify"
{"actions": [{"type": "open_app", "params": {"app": "Spotify"}}], "message": "Opening Spotify", "confirmation_required": false}

Input: "Email boss about the meeting"
{"actions": [{"type": "email", "params": {"recipient": "boss", "subject": "Meeting", "body": ""}}], "message": "What's the email about?", "confirmation_required": true}

Input: "Remind me to pick up kids at 5 PM"
{"actions": [{"type": "reminder", "params": {"text": "Pick up kids", "datetime": "2024-01-15T17:00:00"}}], "message": "Setting reminder for 5 PM", "confirmation_required": false}

Input: "Search for pizza recipe"
{"actions": [{"type": "web_search", "params": {"query": "pizza recipe"}}], "message": "Searching for pizza recipe", "confirmation_required": false}
"""


class NVIDIAClient:
    """OpenAI-compatible client for NVIDIA NIM."""

    def __init__(self) -> None:
        Config.validate()
        self.client = OpenAI(
            base_url=Config.NVIDIA_BASE_URL,
            api_key=Config.NVIDIA_API_KEY,
        )
        self.model = Config.LLM_MODEL

    def _format_context(self, history: list[dict]) -> str:
        """Format conversation history for system prompt."""
        if not history:
            return ""

        context_lines = ["\nConversation Context:"]
        for item in history[-5:]:  # Last 5 exchanges
            context_lines.append(f"User: {item['command']}")
            context_lines.append(f"Assistant: {item['response']}")
        context_lines.append("Current command:")
        return "\n".join(context_lines)

    def parse_intent(self, text: str, history: list[dict] | None = None) -> dict:
        """Parse user text into structured actions."""
        context = self._format_context(history or [])
        formatted_prompt = SYSTEM_PROMPT.format(context=context)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.1,
            max_tokens=512,
        )

        content = response.choices[0].message.content

        # Extract JSON from response
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # Try to find JSON block in markdown
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            return json.loads(content.strip())
