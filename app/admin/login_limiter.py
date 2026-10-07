import asyncio
import hashlib
from dataclasses import dataclass

from starlette.requests import Request

from app.core.redis import redis_client


WINDOW_SECONDS = 300
IP_LIMIT = 30
IP_LOGIN_LIMIT = 10


RATE_LIMIT_SCRIPT = """
local ip_count = tonumber(redis.call('GET', KEYS[1]) or '0')
local pair_count = tonumber(redis.call('GET', KEYS[2]) or '0')

local ip_limit = tonumber(ARGV[1])
local pair_limit = tonumber(ARGV[2])
local window = tonumber(ARGV[3])

local wait = 0

if ip_count >= ip_limit then
    local ttl = redis.call('TTL', KEYS[1])
    if ttl < 1 then
        redis.call('EXPIRE', KEYS[1], window)
        ttl = window
    end
    wait = math.max(wait, ttl)
end

if pair_count >= pair_limit then
    local ttl = redis.call('TTL', KEYS[2])
    if ttl < 1 then
        redis.call('EXPIRE', KEYS[2], window)
        ttl = window
    end
    wait = math.max(wait, ttl)
end

if wait > 0 then
    return wait
end

local new_ip_count = redis.call('INCR', KEYS[1])
if new_ip_count == 1 or redis.call('TTL', KEYS[1]) < 0 then
    redis.call('EXPIRE', KEYS[1], window)
end

local new_pair_count = redis.call('INCR', KEYS[2])
if new_pair_count == 1 or redis.call('TTL', KEYS[2]) < 0 then
    redis.call('EXPIRE', KEYS[2], window)
end

return 0
"""


@dataclass(frozen=True)
class LoginLimit:
    allowed: bool
    retry_after: int = 0


def client_address(request: Request) -> str:
    if request.client is None:
        return "unknown"

    # Не читаем X-Forwarded-For напрямую.
    # За прокси адрес должен обрабатываться сервером
    # только для доверенных прокси.
    return request.client.host


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def check_login_limit(
    request: Request,
    username: str,
) -> LoginLimit:
    address = client_address(request)
    normalized_username = username.strip().casefold()

    ip_key = f"admin:login:ip:{digest(address)}"
    pair_key = (
        "admin:login:pair:"
        f"{digest(address + chr(0) + normalized_username)}"
    )

    retry_after = await asyncio.to_thread(
        redis_client.eval,
        RATE_LIMIT_SCRIPT,
        2,
        ip_key,
        pair_key,
        IP_LIMIT,
        IP_LOGIN_LIMIT,
        WINDOW_SECONDS,
    )

    seconds = int(retry_after)

    return LoginLimit(
        allowed=seconds == 0,
        retry_after=max(seconds, 0),
    )