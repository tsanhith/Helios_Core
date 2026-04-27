"""Configuration shared across backend and mobile."""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration."""

    # NVIDIA NIM
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
    NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
    LLM_MODEL = "meta/llama-3.1-8b-instruct"

    # Backend
    BACKEND_HOST = "http://127.0.0.1:8000"

    @classmethod
    def validate(cls) -> None:
        if not cls.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY not set in .env")
