"""FastAPI backend for Helios Core."""

import os
import sys
import uuid
from pathlib import Path

# Add parent to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import Config
from shared.models import CommandRequest, CommandResponse, Action
from shared.database import Database
from llm import NVIDIAClient

app = FastAPI(title="Helios Core API", version="2.0.0")

# CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM client and database
llm_client = NVIDIAClient()
db = Database()


def _generate_session_id() -> str:
    """Generate a new session ID."""
    return str(uuid.uuid4())[:8]


@app.get("/health")
async def health_check():
    """Check if backend is running."""
    return {"status": "ok", "llm_model": Config.LLM_MODEL, "version": "2.0.0"}


@app.get("/session/new")
async def new_session():
    """Create a new session."""
    session_id = _generate_session_id()
    db.create_session(session_id)
    return {"session_id": session_id}


@app.post("/process", response_model=CommandResponse)
async def process_command(cmd: CommandRequest):
    """Process voice command and return actions."""
    session_id = cmd.session_id or _generate_session_id()

    try:
        # Load conversation history for context
        history = db.get_recent_conversations(session_id, limit=5)

        # Parse intent with context
        result = llm_client.parse_intent(cmd.text, history)

        actions = [Action(**a) for a in result.get("actions", [])]
        confirmation_required = result.get("confirmation_required", False)
        message = result.get("message", "Done")

        # Save conversation
        actions_dicts = [
            {"type": a.type, "params": a.params, "confirmation_required": a.confirmation_required}
            for a in actions
        ]
        db.save_conversation(session_id, cmd.text, message, actions_dicts)

        return CommandResponse(
            text=cmd.text,
            actions=actions,
            message=message,
            confirmation_required=confirmation_required,
        )

    except Exception as e:
        error_response = CommandResponse(
            text=cmd.text,
            actions=[Action(type="speak", params={"text": f"Error: {str(e)}"})],
            message=str(e),
        )
        return error_response


@app.post("/confirm/{action_id}")
async def confirm_action(action_id: int):
    """Confirm a pending action."""
    db.confirm_action(action_id)
    return {"status": "confirmed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
