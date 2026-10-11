from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    api_key: str = field(default="", repr=False)
    model: str = "gemini-2.5-flash"
    daily_limit: int = 10
    minimum_interval: int = 30
    ai_timeout: int = 20

    @classmethod
    def load(cls) -> Settings:
        load_dotenv(PROJECT_ROOT / ".env", override=False)
        return cls(
            data_dir=Path(os.getenv("SCANNER_DATA_DIR", str(PROJECT_ROOT / "data"))),
            api_key=os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            daily_limit=max(0, int(os.getenv("GEMINI_DAILY_LIMIT", "10"))),
            minimum_interval=max(0, int(os.getenv("GEMINI_MIN_INTERVAL", "30"))),
        )


def configure_logging(settings: Settings) -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(settings.data_dir / "scanner.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger = logging.getLogger("scanner_outo")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
