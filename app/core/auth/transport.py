from fastapi_users.authentication import BearerTransport

from app.core import settings

bearer_transport = BearerTransport(tokenUrl=settings.api.token_url)
