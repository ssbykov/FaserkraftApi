import asyncio

_loop: asyncio.AbstractEventLoop | None = None


def get_or_create_loop() -> asyncio.AbstractEventLoop | None:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
    return _loop