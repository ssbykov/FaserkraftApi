import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import aiohttp

from app.core import settings
from app.database import db_helper
from app.database.crud.yandex_tokens import YandexTokensRepository
from app.database.yandex_disk import create_yadisk_instance

if TYPE_CHECKING:
    from app.core.config import DbSettings


def generate_dump_name(db_name: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{db_name}_backup_{timestamp}.dump"


def create_pgpass_file(pgpass_path: str, db: "DbSettings") -> None:
    Path(pgpass_path).parent.mkdir(parents=True, exist_ok=True)
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


async def create_backup() -> str | None:
    if dump_file := await create_database_dump():
        async for session in db_helper.get_session():
            tokens_repo = YandexTokensRepository(session)
            yadisk = await create_yadisk_instance(tokens_repo=tokens_repo)
            await yadisk.copy_photos_to_disk(dump_file)
            await db_helper.synch_backups()
            break
    return dump_file


if __name__ == "__main__":
    asyncio.run(create_backup())
