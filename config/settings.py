"""
Central configuration management for the Autonomous Agent System.
All settings are loaded from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ── Groq ──────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(..., env="GROQ_API_KEY")
    GROQ_MODEL_PRIMARY: str = Field("llama3-70b-8192", env="GROQ_MODEL_PRIMARY")
    GROQ_MODEL_FAST: str = Field("mixtral-8x7b-32768", env="GROQ_MODEL_FAST")
    GROQ_MODEL_CODE: str = Field("llama3-70b-8192", env="GROQ_MODEL_CODE")
    GROQ_TEMPERATURE: float = Field(0.1, env="GROQ_TEMPERATURE")
    GROQ_MAX_TOKENS: int = Field(4096, env="GROQ_MAX_TOKENS")

    # ── FastAPI ────────────────────────────────────────────────────────────────
    API_HOST: str = Field("0.0.0.0", env="API_HOST")
    API_PORT: int = Field(8000, env="API_PORT")
    API_WORKERS: int = Field(1, env="API_WORKERS")
    API_LOG_LEVEL: str = Field("info", env="API_LOG_LEVEL")

    # ── Agent Behaviour ────────────────────────────────────────────────────────
    MAX_RETRIES: int = Field(3, env="MAX_RETRIES")
    MAX_RESEARCH_RESULTS: int = Field(5, env="MAX_RESEARCH_RESULTS")
    HUMAN_IN_LOOP_THRESHOLD: int = Field(3, env="HUMAN_IN_LOOP_THRESHOLD")
    CONFIDENCE_THRESHOLD: float = Field(0.6, env="CONFIDENCE_THRESHOLD")

    # ── Paths ──────────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).parent.parent
    ARTIFACTS_DIR: Path = BASE_DIR / "artifacts"
    LOGS_DIR: Path = BASE_DIR / "logs"
    CHROMA_PERSIST_DIR: str = Field("./chroma_db", env="CHROMA_PERSIST_DIR")

    # ── Docker ─────────────────────────────────────────────────────────────────
    DOCKER_SANDBOX_IMAGE: str = Field(
        "python:3.11-slim", env="DOCKER_SANDBOX_IMAGE"
    )
    DOCKER_EXECUTION_TIMEOUT: int = Field(60, env="DOCKER_EXECUTION_TIMEOUT")
    DOCKER_MEMORY_LIMIT: str = Field("512m", env="DOCKER_MEMORY_LIMIT")
    DOCKER_CPU_LIMIT: float = Field(1.0, env="DOCKER_CPU_LIMIT")
    USE_DOCKER: bool = Field(False, env="USE_DOCKER")   # Disable if Docker unavailable

    # ── Web Search ─────────────────────────────────────────────────────────────
    SEARCH_MAX_RESULTS: int = Field(5, env="SEARCH_MAX_RESULTS")
    SEARCH_TIMEOUT: int = Field(10, env="SEARCH_TIMEOUT")

    # ── Metrics ────────────────────────────────────────────────────────────────
    METRICS_ENABLED: bool = Field(True, env="METRICS_ENABLED")
    PROMETHEUS_PORT: int = Field(9090, env="PROMETHEUS_PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def model_post_init(self, __context) -> None:
        self.ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
