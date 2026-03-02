import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from app.core import settings
from app.database import db_helper
from app.database.crud.yandex_tokens import YandexTokensRepository
from app.database.yandex_disk import create_yadisk_instance

if TYPE_CHECKING:
    from app.core.config import DbSettings

# Настройка логгера для модуля


def generate_dump_name(db_name: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{db_name}_backup_{timestamp}.dump"


def create_pgpass_file(pgpass_path: str, db: "DbSettings") -> None:
    try:
        Path(pgpass_path).parent.mkdir(parents=True, exist_ok=True)
        with open(pgpass_path, "w") as f:
            f.write(f"{db.host}:{db.port}:{db.database}:{db.user}:{db.password}\n")
        os.chmod(pgpass_path, 0o600)
        logging.debug(f"PGpass файл создан: {pgpass_path}")
    except Exception as e:
        logging.error(f"Ошибка при создании pgpass файла {pgpass_path}: {e}")
        raise


def remove_pgpass_file(pgpass_path: str) -> None:
    try:
        os.remove(pgpass_path)
        logging.debug(f"PGpass файл удален: {pgpass_path}")
    except FileNotFoundError:
        logging.warning(f"Файл pgpass {pgpass_path} не найден для удаления")
    except Exception as e:
        logging.error(f"Ошибка при удалении pgpass файла {pgpass_path}: {e}")


async def run_command(cmd: list[str], pgpass_path: str) -> None:
    env = os.environ.copy()
    env["PGPASSFILE"] = pgpass_path

    logging.debug(f"Выполнение команды: {' '.join(cmd)}")

    try:
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
            error_msg = f"Ошибка выполнения команды (код {process.returncode}): {process.stderr}"
            logging.error(error_msg)
            if process.stdout:
                logging.debug(f"stdout команды: {process.stdout}")
            raise subprocess.CalledProcessError(process.returncode, cmd, process.stderr)

        logging.debug(
            f"Команда выполнена успешно. stdout: {process.stdout[:200]}..."
        )  # Первые 200 символов

    except subprocess.CalledProcessError as e:
        logging.error(f"subprocess error: {e}")
        raise
    except Exception as e:
        logging.error(f"Неожиданная ошибка при выполнении команды: {e}")
        raise


async def create_database_dump() -> str:
    db = settings.db
    file_name = generate_dump_name(db.database)
    backups_dir = db.backups_dir
    dump_file = os.path.join(backups_dir, file_name)

    logging.info(f"Начало создания дампа базы данных {db.database} в файл {dump_file}")

    try:
        os.makedirs(backups_dir, exist_ok=True)
        os.chmod(backups_dir, 0o777)
        logging.debug(f"Директория для бэкапов подготовлена: {backups_dir}")
    except Exception as e:
        logging.error(f"Ошибка при создании директории для бэкапов {backups_dir}: {e}")
        raise

    if os.name == "nt":  # Windows
        pgpass_path = os.path.join(
            os.getenv("APPDATA", ""), "postgresql", "pgpass.conf"
        )
    else:  # Linux/macOS
        pgpass_path = os.path.expanduser("~/.pgpass")

    logging.debug(f"Путь к pgpass файлу: {pgpass_path}")

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
        logging.info(f"Дамп базы данных успешно создан: {dump_file}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка при выполнении pg_dump: {e}")
        # Проверяем наличие файла дампа, возможно он создался частично
        if os.path.exists(dump_file):
            try:
                os.remove(dump_file)
                logging.debug(f"Частично созданный файл дампа удален: {dump_file}")
            except Exception as remove_error:
                logging.error(
                    f"Не удалось удалить частично созданный файл дампа: {remove_error}"
                )
        raise
    except Exception as e:
        logging.error(f"Неожиданная ошибка при создании дампа: {e}")
        raise
    finally:
        remove_pgpass_file(pgpass_path)

    return file_name


async def restore_database_from_dump(dump_file: str) -> None:
    db = settings.db
    path_dump_file = Path(settings.db.backups_dir) / dump_file

    logging.info(f"Начало восстановления базы данных из дампа: {path_dump_file}")

    if not path_dump_file.exists():
        logging.error(f"Файл дампа {path_dump_file} не найден")
        return None

    if os.name == "nt":  # Windows
        pgpass_path = os.path.join(
            os.getenv("APPDATA", ""), "postgresql", "pgpass.conf"
        )
    else:  # Linux/macOS
        pgpass_path = os.path.expanduser("~/.pgpass")

    logging.debug(f"Путь к pgpass файлу: {pgpass_path}")

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
            "--if-exists",  # Добавляем флаг для избежания ошибок при отсутствии объектов
            str(path_dump_file),
        ]

        logging.debug(f"Команда восстановления: {' '.join(cmd)}")
        await run_command(cmd, pgpass_path)
        logging.info(f"База данных успешно восстановлена из дампа {dump_file}")

    except subprocess.CalledProcessError as e:
        logging.error(f"Ошибка при выполнении pg_restore: {e}")
        logging.error(
            f"stderr: {e.stderr if hasattr(e, 'stderr') else 'Неизвестная ошибка'}"
        )
        raise
    except Exception as e:
        logging.error(f"Неожиданная ошибка при восстановлении из дампа: {e}")
        raise
    finally:
        remove_pgpass_file(pgpass_path)


async def create_backup() -> str | None:
    logging.info("=" * 50)
    logging.info("Запуск процесса создания бэкапа")

    dump_file = None
    try:
        if dump_file := await create_database_dump():
            logging.info(
                f"Дамп создан: {dump_file}, начинаем копирование на Яндекс.Диск"
            )

            async for session in db_helper.get_session():
                try:
                    tokens_repo = YandexTokensRepository(session)
                    yadisk = await create_yadisk_instance(tokens_repo=tokens_repo)
                    await yadisk.copy_photos_to_disk(dump_file)
                    logging.info(f"Файл {dump_file} успешно скопирован на Яндекс.Диск")

                    await db_helper.synch_backups()
                    logging.debug("Синхронизация бэкапов завершена")

                except Exception as e:
                    logging.error(f"Ошибка при работе с Яндекс.Диском: {e}")
                    raise
                finally:
                    await session.close()
                break
    except Exception as e:
        logging.error(f"Критическая ошибка при создании бэкапа: {e}")
        logging.exception("Полный стек ошибки:")  # Добавляет traceback
        return None

    logging.info(f"Процесс создания бэкапа завершен. Результат: {dump_file}")
    logging.info("=" * 50)
    return dump_file


if __name__ == "__main__":
    asyncio.run(create_backup())
