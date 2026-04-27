"""FastAPI backend for Helios Core."""

import os
import sys
from pathlib import Path

# Add parent to path for shared imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import Config
from shared.models import CommandRequest, CommandResponse, Action
from llm import NVIDIAClient

app = FastAPI(title="Helios Core API", version="1.0.0")

# CORS for mobile app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM client
llm_client = NVIDIAClient()


@app.get("/health")
async def health_check():
    """Check if backend is running."""
    return {"status": "ok", "llm_model": Config.LLM_MODEL}


@app.post("/process", response_model=CommandResponse)
async def process_command(cmd: CommandRequest):
    """Process voice command and return actions."""
    try:
        result = llm_client.parse_intent(cmd.text)

        actions = [Action(**a) for a in result.get("actions", [])]

        return CommandResponse(
            text=cmd.text,
            actions=actions,
            message=result.get("message", "Done"),
        )

    except Exception as e:
        return CommandResponse(
            text=cmd.text,
            actions=[Action(type="speak", params={"text": f"Error: {str(e)}"})],
            message=str(e),
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
