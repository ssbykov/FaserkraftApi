from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from api.api_v1.dependencies import get_current_employee
from core import settings
from database.models.app_update import VersionInfoResponse
from database.schemas.employee import EmployeeRead
from update.get_apk_info import load_release_info

router = APIRouter(
    prefix=settings.api.v1.update,
    tags=["app-update"],
)


@router.get("/version", response_model=VersionInfoResponse)
async def get_latest_version(
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> Optional[VersionInfoResponse]:
    try:
        release = load_release_info()
    except Exception as e:
        return None

    return VersionInfoResponse(
        version_name=release.version_name,
        apk_file=release.apk_file,
        roles=release.roles,
        force_update=release.force_update,
        changelog=release.changelog,
    )


@router.get("/download")
async def download_apk(
    employee: Annotated[EmployeeRead, Depends(get_current_employee)],
) -> FileResponse:
    try:
        release = load_release_info()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    apk_path = settings.app_update.release_dir / release.apk_file

    return FileResponse(
        path=apk_path,
        media_type="application/vnd.android.package-archive",
        filename=release.apk_file,
        headers={
            "Content-Disposition": f'attachment; filename="{release.apk_file}"'
        },
    )
