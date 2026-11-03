"""Local-only persistence for private dream records."""

from pathlib import Path
from uuid import uuid4

from models import DreamRecord
from coding_models import DreamCoding
from storyboard_models import Storyboard


DATA_DIR = Path(__file__).parent / "data"


def save_dream_record(record: DreamRecord) -> tuple[str, Path]:
    """Save a record in its own ignored data folder and return its session id."""
    session_id = str(uuid4())
    session_dir = DATA_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=False)

    record_path = session_dir / "dream_record.json"
    record_path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
    return session_id, record_path


def save_dream_coding(session_id: str, coding: DreamCoding) -> Path:
    """Save coding beside the associated dream record, validating the folder id."""
    session_dir = DATA_DIR / session_id
    if not session_dir.is_dir() or session_dir.resolve().parent != DATA_DIR.resolve():
        raise ValueError("Unknown local dream session.")
    coding_path = session_dir / "dream_coding.json"
    coding_path.write_text(coding.model_dump_json(indent=2), encoding="utf-8")
    return coding_path


def session_dir_for(session_id: str) -> Path:
    session_dir = DATA_DIR / session_id
    if not session_dir.is_dir() or session_dir.resolve().parent != DATA_DIR.resolve():
        raise ValueError("Unknown local dream session.")
    return session_dir


def save_storyboard(session_id: str, storyboard: Storyboard) -> Path:
    storyboard_path = session_dir_for(session_id) / "storyboard.json"
    storyboard_path.write_text(storyboard.model_dump_json(indent=2), encoding="utf-8")
    return storyboard_path


def load_storyboard(session_id: str) -> Storyboard | None:
    storyboard_path = session_dir_for(session_id) / "storyboard.json"
    if not storyboard_path.exists():
        return None
    return Storyboard.model_validate_json(storyboard_path.read_text(encoding="utf-8"))
