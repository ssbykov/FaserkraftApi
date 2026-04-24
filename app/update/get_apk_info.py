import json

from app.database.models.app_update import ReleaseFileData
from core import settings


def load_release_info() -> ReleaseFileData:
    release_file = settings.app_update.release_file
    if not release_file.exists():
        raise FileNotFoundError(f"Release file not found: {release_file}")

    try:
        data = json.loads(release_file.read_text(encoding="utf-8"))
        release = ReleaseFileData.model_validate(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in release file: {e}")
    except Exception as e:
        raise ValueError(f"Invalid release metadata: {e}")

    return release
