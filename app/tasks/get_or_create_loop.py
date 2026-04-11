import asyncio


def get_or_create_loop():
    try:
        # Пытаемся получить текущий цикл событий (сработает, если он уже был создан нами ранее)
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        # Если цикла нет (Python 3.11+) или он закрыт, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop