"""Settings loaded from environment variables / a local .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    api_key: str
    api_secret: str
    testnet: bool
    db_path: Path

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.api_secret)

    @property
    def base_url(self) -> str:
        return "https://api-testnet.bybit.com" if self.testnet else "https://api.bybit.com"


def get_settings() -> Settings:
    db_path = Path(os.getenv("BYBIT_DB_PATH", "data/bybit.db"))
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    return Settings(
        api_key=os.getenv("BYBIT_API_KEY", "").strip(),
        api_secret=os.getenv("BYBIT_API_SECRET", "").strip(),
        testnet=os.getenv("BYBIT_TESTNET", "false").strip().lower() in {"1", "true", "yes"},
        db_path=db_path,
    )
