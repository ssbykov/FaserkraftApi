from app.database import SessionDep
from app.database.crud.mixines import GetBackNextIdMixin
from app.database.models import InventoryItem


def get_step_definition_repo(session: SessionDep) -> "InventoryItemRepository":
    return InventoryItemRepository(session)


class InventoryItemRepository(GetBackNextIdMixin[InventoryItem]):
    model = InventoryItem