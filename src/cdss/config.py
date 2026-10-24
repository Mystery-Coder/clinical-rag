"""Paths and environment settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]


def _path(name: str, default: str) -> Path:
    raw = os.getenv(name, default)
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    return path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    passage_cap: int
    top_k: int
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    nice_api_key: str
    nice_api_base: str

    @property
    def passages_dir(self) -> Path:
        return self.data_dir / "passages"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "index"

    @property
    def mimic_dir(self) -> Path:
        return self.data_dir / "mimic-iv-demo"

    @property
    def primekg_dir(self) -> Path:
        return self.data_dir / "primekg"

    @property
    def eval_dir(self) -> Path:
        return self.data_dir / "eval"


def get_settings() -> Settings:
    return Settings(
        data_dir=_path("DATA_DIR", "data"),
        passage_cap=int(os.getenv("PASSAGE_CAP", "500")),
        top_k=int(os.getenv("TOP_K", "5")),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", ""),
        nice_api_key=os.getenv("NICE_API_KEY", ""),
        nice_api_base=os.getenv(
            "NICE_API_BASE", "https://syndication.nice.org.uk/services"
        ),
    )


NOTICE = (
    "This is decision support for a clinician. It is not a diagnosis or a treatment order."
)
FLAG = "unsupported by retrieved sources, verify independently"
