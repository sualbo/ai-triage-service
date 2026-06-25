from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AI Triage Service")
    environment: str = os.getenv("ENVIRONMENT", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
    llm_fake_mode: bool = os.getenv("LLM_FAKE_MODE", "false").lower() in {"1", "true", "yes", "on"}

    requests_per_minute: int = int(os.getenv("REQUESTS_PER_MINUTE", "10"))
    db_path: str = os.getenv("DB_PATH", "data/tickets.db")
    log_file: str = os.getenv("LOG_FILE", "logs/app.log")

    def ensure_runtime_dirs(self) -> None:
        for filepath in (self.db_path, self.log_file):
            path = Path(filepath)
            if path.parent and str(path.parent) != ".":
                path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
