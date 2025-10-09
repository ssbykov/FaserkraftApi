import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp

from app.core import settings
from app.database import db_helper

if TYPE_CHECKING:
    from app.core.config import DbSettings


def generate_dump_name(db_name: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{db_name}_backup_{timestamp}.dump"


def create_pgpass_file(pgpass_path: str, db: "DbSettings") -> None:
    with open(pgpass_path, "w") as f:
        f.write(f"{db.host}:{db.port}:{db.database}:{db.user}:{db.password}\n")
    os.chmod(pgpass_path, 0o600)


def remove_pgpass_file(pgpass_path: str) -> None:
    try:
        os.remove(pgpass_path)
    except FileNotFoundError:
        logging.warning("Файл pgpass не найден для удаления")


async def run_command(cmd: list[str], pgpass_path: str) -> None:
    env = os.environ.copy()
    env["PGPASSFILE"] = pgpass_path

    loop = asyncio.get_running_loop()
    process = await loop.run_in_executor(
        None,
        lambda: subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        ),
    )

    if process.returncode != 0:
        logging.error(f"Ошибка выполнения команды: {process.stderr}")
        raise subprocess.CalledProcessError(process.returncode, cmd)


async def create_database_dump() -> str:
    db = settings.db
    file_name = generate_dump_name(db.database)
    backups_dir = db.backups_dir
    dump_file = os.path.join(backups_dir, file_name)

    os.makedirs(backups_dir, exist_ok=True)
    os.chmod(backups_dir, 0o777)

    if os.name == "nt":  # Windows
        pgpass_path = os.path.join(
            os.getenv("APPDATA", ""), "postgresql", "pgpass.conf"
        )
    else:  # Linux/macOS
        pgpass_path = os.path.expanduser("~/.pgpass")

    try:
        create_pgpass_file(pgpass_path, db)

        cmd = [
            "pg_dump",
            "-U",
            db.user,
            "-h",
            db.host,
            "-p",
            str(db.port),
            "-F",
            "c",
            "-f",
            dump_file,
            db.database,
        ]

        await run_command(cmd, pgpass_path)

    finally:
        remove_pgpass_file(pgpass_path)

    return file_name


async def restore_database_from_dump(dump_file: str) -> None:
    db = settings.db
    path_dump_file = Path(settings.db.backups_dir) / dump_file

    if not path_dump_file.exists():
        logging.error(f"Файл дампа {path_dump_file} не найден")
        return None

    if os.name == "nt":  # Windows
        pgpass_path = os.path.join(
            os.getenv("APPDATA", ""), "postgresql", "pgpass.conf"
        )
    else:  # Linux/macOS
        pgpass_path = os.path.expanduser("~/.pgpass")

    try:
        create_pgpass_file(pgpass_path, db)

        cmd = [
            "pg_restore",
            "-U",
            db.user,
            "-h",
            db.host,
            "-p",
            str(db.port),
            "-d",
            db.database,
            "-c",
            str(path_dump_file),
        ]

        await run_command(cmd, pgpass_path)

    finally:
        remove_pgpass_file(pgpass_path)


class YaDisk:
    API_URL = "https://cloud-api.yandex.net/v1/disk/resources"

    def __init__(self) -> None:
        self.token = settings.yandex_disk.token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "OAuth {}".format(self.token),
        }
        self.folder_name = "db_backup"

    async def _create_folder(self, session: aiohttp.ClientSession) -> None:
        try:
            async with session.put(
                self.API_URL, headers=self.headers, params={"path": self.folder_name}
            ) as response:
                if response.status not in (201, 409):
                    raise Exception(f"Статус: {response.status}")
        except Exception as e:
            logging.error(f"Ошибка при создании папки на Яндекс.Диске: {e}")

    async def get_upload_url(
        self, session: aiohttp.ClientSession, file_name: str
    ) -> str | None:
        upload_url = self.API_URL + "/upload"
        params = {"path": f"{self.folder_name}/{file_name}", "overwrite": "true"}
        try:
            async with session.get(
                upload_url, headers=self.headers, params=params
            ) as response:
                if response.status != 200:
                    raise Exception(f"Статус: {response.status}")
                data = await response.json()
                return str(data.get("href", ""))
        except Exception as e:
            logging.error(f"Ошибка при получении ссылки для загрузки файла: {e}")
            return None

    async def copy_photos_to_disk(self, file_name: str) -> None:
        async with aiohttp.ClientSession() as session:
            await self._create_folder(session)
            upload_url = await self.get_upload_url(session, file_name)
            if not upload_url:
                return None

            file_path = os.path.join(settings.db.backups_dir, file_name)
            try:
                with open(file_path, "rb") as f:
                    async with session.put(upload_url, data=f) as response:
                        if response.status != 201:
                            raise Exception(f"Статус:{response.status}")
                        return None
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла: {e}")
                return None


async def create_backup() -> str | None:
    if dump_file := await create_database_dump():
        yadisk = YaDisk()
        await yadisk.copy_photos_to_disk(dump_file)
        await db_helper.synch_backups()
    return dump_file


if __name__ == "__main__":
    asyncio.run(create_backup())
