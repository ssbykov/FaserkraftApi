from app.database import Process, SessionDep
from app.database.crud.mixines import GetBackNextIdMixin


def get_process_repo(session: SessionDep) -> "ProcessRepository":
    return ProcessRepository(session)


class ProcessRepository(GetBackNextIdMixin[Process]):
    model = Process
