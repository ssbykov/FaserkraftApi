from app.database import Process
from app.database.crud.mixines import GetBackNextIdMixin


class ProcessRepository(GetBackNextIdMixin[Process]):
    model = Process
