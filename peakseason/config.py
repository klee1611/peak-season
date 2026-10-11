"""Settings from environment variables (see .env.example)."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    model_base_url: str = "http://localhost:11434/v1"
    model_name: str = "gemma4:e2b-it-qat"  # smallest multimodal Gemma that classified well
    model_api_key: str = "ollama"  # Ollama ignores it; hosted endpoints may need one
    model_timeout_s: float = 180.0

    sqlite_path: Path = ROOT / ".cache" / "peakseason.db"
    site_data_dir: Path = ROOT / "site" / "data"
    targets_dir: Path = ROOT / "targets"
    prompts_dir: Path = ROOT / "prompts"
    spots_path: Path = ROOT / "data" / "spots.yaml"
    history_dir: Path = ROOT / "data" / "history"
    # Public address of the site, for canonical links, hreflang and the sitemap.
    site_url: str = "https://peak-season-dvl.pages.dev"

    serpapi_api_key: str | None = None
    serpapi_cache_hours: float = 48
    serpapi_reserve: int = 20
    serpapi_max_calls_per_run: int = 10

    max_photos_per_run: int = 80
    max_photos_per_cell: int = 3
    classify_deadline_min: float = 90
    # Minutes of the deadline kept for reading SerpApi snippets (only when a key is set), so
    # paid searches are not left unread behind the photo queue.
    text_reserve_min: float = 20
    window_days: int = 7
    fetch_days: int = 10
    inat_user_agent: str = (
        "PeakSeason/0.1 (+https://github.com/klee1611/peak-season; open-source hackathon)"
    )


def get_settings() -> Settings:
    return Settings()
