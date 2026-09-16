from pydantic import BaseModel

from core import settings
from database.models.employee import Role


class VersionInfoResponse(BaseModel):
    version_name: str
    apk_file: str
    roles: list[Role]
    force_update: bool
    changelog: str


class ReleaseFileData(BaseModel):
    version_name: str
    apk_file: str = settings.app_update.release_file
    roles: list[Role] = [Role.master, Role.worker]
    force_update: bool = False
    changelog: str = ""