import logging
import os
import ssl
from datetime import datetime, timezone, timedelta

import aiohttp
import certifi

from app.core import settings


class YaDisk:
    API_URL = "https://cloud-api.yandex.net/v1/disk/resources"
    TOKEN_INFO_URL = "https://login.yandex.ru/info"
    TOKEN_REFRESH_URL = "https://oauth.yandex.ru/token"

    def __init__(self, tokens_repo) -> None:
        self.tokens_repo = tokens_repo
        self.token = ""
        self.client_id = settings.yandex_disk.client_id
        self.client_secret = settings.yandex_disk.client_secret
        self.refresh_token = settings.yandex_disk.refresh_token
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": "OAuth {}".format(self.token),
        }
        self.folder_name = "db_backup"
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    async def initialize(self):
        try:
            access_token, refresh_token, expires_at = (
                await self.tokens_repo.get_tokens()
            )
            self.token = access_token
            self.refresh_token = refresh_token
            self.headers["Authorization"] = f"OAuth {self.token}"
        except Exception:
            async with aiohttp.ClientSession() as session:
                success = await self._refresh_token(session)
                if not success:
                    logging.error(
                        "Не удалось инициализировать токены через refresh_token: отсутствует валидный refresh_token или произошла ошибка обновления."
                    )
                    raise Exception(
                        "Не удалось инициализировать YaDisk: нет валидных токенов."
                    )

    async def _load_tokens_from_db(self):
        access_token, refresh_token, _ = await self.tokens_repo.get_tokens()
        self.token = access_token
        self.refresh_token = refresh_token
        self.headers["Authorization"] = f"OAuth {self.token}"

    async def _save_tokens_to_db(
        self, access_token: str, refresh_token: str, expires_at: datetime
    ):
        await self.tokens_repo.save_tokens(access_token, refresh_token, expires_at)
        self.token = access_token
        self.refresh_token = refresh_token
        self.headers["Authorization"] = f"OAuth {self.token}"

    async def _refresh_token(self, session: aiohttp.ClientSession) -> bool:
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
            async with session.post(
                self.TOKEN_REFRESH_URL, data=data, ssl=self.ssl_context
            ) as response:
                new_data = await response.json()
                if "access_token" in new_data and "refresh_token" in new_data:
                    # Сохраняем новые токены в базу
                    expires_in = new_data.get("expires_in")
                    expires_at = (
                        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
                        if expires_in
                        else None
                    )
                    await self._save_tokens_to_db(
                        new_data["access_token"],
                        new_data["refresh_token"],
                        expires_at,
                    )
                    return True
                logging.error(f"Ошибка обновления токена: {new_data}")
                return False
        except Exception as e:
            logging.error(f"Ошибка при рефреше токена: {e}")
            return False

    async def _check_token_valid(self, session: aiohttp.ClientSession) -> bool:
        try:
            await self._load_tokens_from_db()
            async with session.get(
                self.TOKEN_INFO_URL,
                headers=self.headers,
                ssl=self.ssl_context,
            ) as response:
                if response.status == 200:
                    return True
                elif response.status == 401:
                    return await self._refresh_token(session)
                logging.error(
                    f"Токен Яндекс.Диска невалиден, статус: {response.status}"
                )
                return False
        except Exception as e:
            logging.error(f"Ошибка при проверке токена Яндекс.Диска: {e}")
            return False

    async def _create_folder(self, session: aiohttp.ClientSession) -> None:
        if not await self._check_token_valid(session):
            return
        try:
            async with session.put(
                self.API_URL,
                headers=self.headers,
                params={"path": self.folder_name},
                ssl=self.ssl_context,
            ) as response:
                if response.status not in (201, 409):
                    raise Exception(f"Статус: {response.status}")
        except Exception as e:
            logging.error(f"Ошибка при создании папки на Яндекс.Диске: {e}")

    async def get_upload_url(
        self, session: aiohttp.ClientSession, file_name: str
    ) -> str | None:
        if not await self._check_token_valid(session):
            return None
        upload_url = self.API_URL + "/upload"
        params = {"path": f"{self.folder_name}/{file_name}", "overwrite": "true"}
        try:
            async with session.get(
                upload_url,
                headers=self.headers,
                params=params,
                ssl=self.ssl_context,
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
                    async with session.put(
                        upload_url, data=f, ssl=self.ssl_context
                    ) as response:
                        if response.status != 201:
                            raise Exception(f"Статус:{response.status}")
                        return None
            except Exception as e:
                logging.error(f"Ошибка при загрузке файла: {e}")
                return None


async def create_yadisk_instance(tokens_repo) -> YaDisk:
    yadisk = YaDisk(tokens_repo)
    await yadisk.initialize()
    return yadisk
