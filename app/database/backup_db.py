import asyncio
import logging
import os
import subprocess
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterator

from app.core import settings
from app.core.backup_status import save_last_result
from app.core.redis import redis_client
from app.database import worker_db_helper
from app.database.crud.yandex_tokens import YandexTokensRepository
from app.database.yandex_disk import create_yadisk_instance

if TYPE_CHECKING:
    from app.core.config import DbSettings


logger = logging.getLogger(__name__)

COMMAND_TIMEOUT_SECONDS = 1800


def generate_dump_name(db_name: str) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"{db_name}_backup_{timestamp}.dump"


def escape_pgpass_value(value: str) -> str:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("Параметры подключения содержат недопустимые символы")

    return value.replace("\\", "\\\\").replace(":", "\\:")


@contextmanager
def temporary_pgpass(db: "DbSettings") -> Iterator[str]:
    """
    Создать отдельный файл авторизации для одной операции.

    Пользовательские ~/.pgpass и pgpass.conf не изменяются.
    """
    path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix="fkapi_pgpass_",
            suffix=".conf",
            delete=False,
        ) as file:
            path = file.name

            # На Windows доступ также зависит от ACL
            # временного каталога.
            os.chmod(path, 0o600)

            values = (
                str(db.host),
                str(db.port),
                str(db.database),
                str(db.user),
                str(db.password),
            )

            line = ":".join(escape_pgpass_value(value) for value in values)

            file.write(line + "\n")

        yield path

    finally:
        if path is not None:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                logger.exception("Не удалось удалить временный файл pgpass")


async def run_command(
    cmd: list[str],
    pgpass_path: str,
    timeout_seconds: int = COMMAND_TIMEOUT_SECONDS,
) -> None:
    if not cmd:
        raise ValueError("Не указана команда для выполнения")

    if timeout_seconds <= 0:
        raise ValueError("Таймаут должен быть положительным")

    env = os.environ.copy()
    env["PGPASSFILE"] = pgpass_path

    # Используем пароль только из созданного для операции файла.
    env.pop("PGPASSWORD", None)

    logger.info(
        "Запуск %s, таймаут %s сек.",
        cmd[0],
        timeout_seconds,
    )

    try:
        process = await asyncio.to_thread(
            subprocess.run,
            cmd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )

    except subprocess.TimeoutExpired:
        logger.exception(
            "Превышен таймаут выполнения %s",
            cmd[0],
        )
        raise

    except Exception:
        logger.exception(
            "Не удалось выполнить %s",
            cmd[0],
        )
        raise

    if process.returncode != 0:
        logger.error(
            "%s завершился с кодом %s: %s",
            cmd[0],
            process.returncode,
            process.stderr,
        )

        raise subprocess.CalledProcessError(
            returncode=process.returncode,
            cmd=cmd,
            output=process.stdout,
            stderr=process.stderr,
        )

    if process.stderr:
        logger.warning(
            "Сообщения %s: %s",
            cmd[0],
            process.stderr,
        )

    logger.info("%s выполнен успешно", cmd[0])


async def create_database_dump() -> str:
    db = settings.db

    file_name = generate_dump_name(db.database)
    backups_dir = Path(db.backups_dir)
    dump_path = backups_dir / file_name

    # mode применяется только при создании каталога;
    # существующие права каталога не меняются.
    backups_dir.mkdir(
        mode=0o700,
        parents=True,
        exist_ok=True,
    )

    logger.info(
        "Начало создания дампа базы %s: %s",
        db.database,
        file_name,
    )

    cmd = [
        "pg_dump",
        "--no-password",
        "-U",
        str(db.user),
        "-h",
        str(db.host),
        "-p",
        str(db.port),
        "-F",
        "c",
        "-f",
        str(dump_path),
        str(db.database),
    ]

    try:
        with temporary_pgpass(db) as pgpass_path:
            await run_command(
                cmd,
                pgpass_path,
            )

        if not dump_path.is_file() or dump_path.stat().st_size == 0:
            raise RuntimeError("pg_dump не создал непустой файл дампа")

        os.chmod(dump_path, 0o600)

    except Exception:
        logger.exception("Ошибка создания дампа")

        try:
            dump_path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Не удалось удалить неполный файл дампа")

        raise

    logger.info(
        "Дамп базы успешно создан: %s",
        file_name,
    )

    return file_name


def validate_restore_dump(file_name: str) -> Path:
    """
    Разрешить восстановление только из непосредственного
    непустого .dump-файла в каталоге резервных копий.
    """
    if (
        not isinstance(file_name, str)
        or not file_name
        or "/" in file_name
        or "\\" in file_name
        or "\x00" in file_name
    ):
        raise ValueError("Недопустимое имя файла резервной копии")

    root = Path(settings.db.backups_dir).resolve()
    candidate = root / file_name

    if candidate.is_symlink():
        raise ValueError("Восстановление из символической ссылки запрещено")

    path = candidate.resolve(strict=True)

    if path.parent != root:
        raise ValueError("Файл находится вне каталога резервных копий")

    if path.suffix != ".dump":
        raise ValueError("Ожидается файл с расширением .dump")

    if not path.is_file():
        raise ValueError("Резервная копия не является файлом")

    if path.stat().st_size == 0:
        raise ValueError("Файл резервной копии пуст")

    return path


async def restore_database_from_dump(
    dump_file: str,
) -> None:
    """
    Восстановить БД из доверенного локального дампа.

    До вызова необходимо остановить бизнес-записи,
    планировщик и конфликтующие фоновые задачи.
    """
    db = settings.db
    dump_path = validate_restore_dump(dump_file)

    logger.warning(
        "Начало восстановления базы %s из %s",
        db.database,
        dump_path.name,
    )

    cmd = [
        "pg_restore",
        "--no-password",
        "-U",
        str(db.user),
        "-h",
        str(db.host),
        "-p",
        str(db.port),
        "-d",
        str(db.database),
        "--clean",
        "--if-exists",
        "--single-transaction",
        "--exit-on-error",
        str(dump_path),
    ]

    try:
        with temporary_pgpass(db) as pgpass_path:
            await run_command(
                cmd,
                pgpass_path,
            )

    except Exception:
        logger.exception(
            "Восстановление базы из %s завершилось ошибкой",
            dump_path.name,
        )
        raise

    logger.warning(
        "Восстановление базы из %s успешно завершено",
        dump_path.name,
    )


async def create_backup(task_name: str) -> str:
    logger.info("=" * 50)
    logger.info("Запуск процесса создания бэкапа")

    try:
        dump_file = await create_database_dump()

        logger.info(
            "Дамп создан: %s, копируем на Яндекс.Диск",
            dump_file,
        )

        async with worker_db_helper.async_session() as session:
            tokens_repo = YandexTokensRepository(session)

            yadisk = await create_yadisk_instance(
                tokens_repo=tokens_repo,
            )

            await yadisk.copy_photos_to_disk(dump_file)

            logger.info(
                "Файл %s скопирован на Яндекс.Диск",
                dump_file,
            )

            await worker_db_helper.synch_backups(session)
            logger.debug("Синхронизация бэкапов завершена")

    except Exception as exc:
        logger.exception("Критическая ошибка при создании бэкапа")

        # Сбой записи результата не должен скрыть
        # исходное исключение.
        try:
            save_last_result(
                name=task_name,
                ok=False,
                message=f"{type(exc).__name__}: {exc}",
            )
        except Exception:
            logger.exception("Не удалось сохранить сообщение " "об ошибке бэкапа")

        raise

    else:
        # Ошибка уведомления не превращает
        # успешно созданный бэкап в неуспешный.
        try:
            save_last_result(
                name=task_name,
                ok=True,
                message=("Бэкап создан и загружен на Яндекс.Диск: " f"{dump_file}"),
            )
        except Exception:
            logger.exception("Бэкап создан, но не удалось " "сохранить уведомление")

        logger.info(
            "Бэкап завершён. Результат: %s",
            dump_file,
        )
        logger.info("=" * 50)

        return dump_file

    finally:
        try:
            redis_client.delete(task_name)
        except Exception:
            logger.exception(
                "Не удалось удалить блокировку бэкапа %s. "
                "Она останется до истечения TTL.",
                task_name,
            )
