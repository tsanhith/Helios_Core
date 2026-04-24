from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI()


class CommandRequest(BaseModel):
    text: str


@app.post("/process_command")
async def process_command(command: CommandRequest):
    return [
        {
            "action": "speak",
            "message": f"I heard you say {command.text}",
        }
    ]
