from fastapi_users import FastAPIUsers

from app.api.dependencies.backend import authentication_backend
from app.api.dependencies.user_manager import get_user_manager
from app.database.models import User

fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [authentication_backend],
)


current_user = fastapi_users.current_user(active=True, verified=True)
current_super_user = fastapi_users.current_user(
    superuser=True,
    active=True,
    verified=True,
)
