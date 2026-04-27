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

Respond ONLY with a JSON object in this format:
{
    "actions": [{"type": "action_name", "params": {...}}],
    "message": "What to say to user"
}

Examples:
Input: "Message John"
{"actions": [{"type": "sms", "params": {"contact": "John", "message": ""}}], "message": "Who do you want to message?"}

Input: "Call mum"
{"actions": [{"type": "call", "params": {"contact": "mum"}}], "message": "Calling mum"}

Input: "Open Spotify"
{"actions": [{"type": "open_app", "params": {"app": "Spotify"}}], "message": "Opening Spotify"}
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

    def parse_intent(self, text: str) -> dict:
        """Parse user text into structured actions."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
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
