import logging
from dataclasses import dataclass

import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings
from app.core.logging_config import get_logger, log_event
from app.models.user import User


logger = get_logger(__name__)


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    max_requests: int
    window_seconds: int = 60


AUTH_LOGIN_RATE_LIMIT = RateLimitRule(
    name="auth_login",
    max_requests=settings.rate_limit_auth_login_per_minute,
)

AUTH_REGISTER_RATE_LIMIT = RateLimitRule(
    name="auth_register",
    max_requests=settings.rate_limit_auth_register_per_minute,
)

RAG_RATE_LIMIT = RateLimitRule(
    name="rag",
    max_requests=settings.rate_limit_rag_per_minute,
)

KEYWORD_SEARCH_RATE_LIMIT = RateLimitRule(
    name="keyword_search",
    max_requests=settings.rate_limit_keyword_search_per_minute,
)

RERANK_RATE_LIMIT = RateLimitRule(
    name="rerank",
    max_requests=settings.rate_limit_rerank_per_minute,
)

EVAL_RATE_LIMIT = RateLimitRule(
    name="eval",
    max_requests=settings.rate_limit_eval_per_minute,
)

UPLOAD_RATE_LIMIT = RateLimitRule(
    name="upload",
    max_requests=settings.rate_limit_upload_per_minute,
)

DOCUMENT_PROCESSING_RATE_LIMIT = RateLimitRule(
    name="document_processing",
    max_requests=settings.rate_limit_document_processing_per_minute,
)

READ_RATE_LIMIT = RateLimitRule(
    name="read",
    max_requests=settings.rate_limit_read_per_minute,
)

CHUNKS_READ_RATE_LIMIT = RateLimitRule(
    name="chunks_read",
    max_requests=settings.rate_limit_chunks_read_per_minute,
)


class RedisRateLimiter:
    LUA_SCRIPT = """
    local key = KEYS[1]
    local limit = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])

    local current = redis.call("INCR", key)

    if current == 1 then
        redis.call("EXPIRE", key, window)
    end

    local ttl = redis.call("TTL", key)

    return {current, ttl}
    """

    def __init__(self, redis_url: str) -> None:
        self.client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    def check(
        self,
        *,
        key: str,
        rule: RateLimitRule,
    ) -> dict[str, int | str]:
        current, ttl = self.client.eval(
            self.LUA_SCRIPT,
            1,
            key,
            rule.max_requests,
            rule.window_seconds,
        )

        current_count = int(current)
        ttl_seconds = max(int(ttl), 1)
        remaining = max(rule.max_requests - current_count, 0)

        if current_count > rule.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Rate limit exceeded for '{rule.name}'. "
                        f"Try again in {ttl_seconds} seconds."
                    ),
                    "policy": rule.name,
                    "limit": rule.max_requests,
                    "window_seconds": rule.window_seconds,
                    "retry_after_seconds": ttl_seconds,
                },
                headers={
                    "Retry-After": str(ttl_seconds),
                    "X-RateLimit-Limit": str(rule.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl_seconds),
                },
            )

        return {
            "policy": rule.name,
            "limit": rule.max_requests,
            "remaining": remaining,
            "reset_seconds": ttl_seconds,
        }


rate_limiter = RedisRateLimiter(settings.redis_url)


def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client is not None:
        return request.client.host

    return "unknown"


def build_user_rate_limit_key(
    *,
    current_user: User,
    request: Request,
    rule: RateLimitRule,
) -> str:
    return (
        "rate_limit:"
        f"user:{current_user.id}:"
        f"policy:{rule.name}:"
        f"method:{request.method}:"
        f"path:{request.url.path}"
    )


def build_ip_rate_limit_key(
    *,
    request: Request,
    rule: RateLimitRule,
) -> str:
    return (
        "rate_limit:"
        f"ip:{get_client_ip(request)}:"
        f"policy:{rule.name}:"
        f"method:{request.method}:"
        f"path:{request.url.path}"
    )


def enforce_user_rate_limit(
    *,
    request: Request,
    current_user: User,
    rule: RateLimitRule,
) -> dict[str, int | str]:
    if not settings.rate_limit_enabled:
        return {
            "policy": rule.name,
            "limit": rule.max_requests,
            "remaining": rule.max_requests,
            "reset_seconds": rule.window_seconds,
        }

    key = build_user_rate_limit_key(
        current_user=current_user,
        request=request,
        rule=rule,
    )

    try:
        result = rate_limiter.check(
            key=key,
            rule=rule,
        )

        log_event(
            logger=logger,
            event="rate_limit_allowed",
            message="Request allowed by user rate limiter",
            user_id=current_user.id,
            path=request.url.path,
            method=request.method,
            policy=rule.name,
            limit=rule.max_requests,
            remaining=result["remaining"],
            reset_seconds=result["reset_seconds"],
        )

        return result

    except HTTPException:
        log_event(
            logger=logger,
            event="rate_limit_blocked",
            message="Request blocked by user rate limiter",
            level=logging.WARNING,
            user_id=current_user.id,
            path=request.url.path,
            method=request.method,
            policy=rule.name,
            limit=rule.max_requests,
        )

        raise

    except Exception as error:
        logger.exception(
            "User rate limiter failed",
            extra={
                "event": "rate_limit_error",
                "extra_fields": {
                    "user_id": current_user.id,
                    "path": request.url.path,
                    "method": request.method,
                    "policy": rule.name,
                    "error": str(error),
                },
            },
        )

        if settings.rate_limit_fail_open:
            return {
                "policy": rule.name,
                "limit": rule.max_requests,
                "remaining": rule.max_requests,
                "reset_seconds": rule.window_seconds,
            }

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter unavailable.",
        ) from error


def enforce_ip_rate_limit(
    *,
    request: Request,
    rule: RateLimitRule,
) -> dict[str, int | str]:
    if not settings.rate_limit_enabled:
        return {
            "policy": rule.name,
            "limit": rule.max_requests,
            "remaining": rule.max_requests,
            "reset_seconds": rule.window_seconds,
        }

    key = build_ip_rate_limit_key(
        request=request,
        rule=rule,
    )

    client_ip = get_client_ip(request)

    try:
        result = rate_limiter.check(
            key=key,
            rule=rule,
        )

        log_event(
            logger=logger,
            event="rate_limit_allowed",
            message="Request allowed by IP rate limiter",
            client_ip=client_ip,
            path=request.url.path,
            method=request.method,
            policy=rule.name,
            limit=rule.max_requests,
            remaining=result["remaining"],
            reset_seconds=result["reset_seconds"],
        )

        return result

    except HTTPException:
        log_event(
            logger=logger,
            event="rate_limit_blocked",
            message="Request blocked by IP rate limiter",
            level=logging.WARNING,
            client_ip=client_ip,
            path=request.url.path,
            method=request.method,
            policy=rule.name,
            limit=rule.max_requests,
        )

        raise

    except Exception as error:
        logger.exception(
            "IP rate limiter failed",
            extra={
                "event": "rate_limit_error",
                "extra_fields": {
                    "client_ip": client_ip,
                    "path": request.url.path,
                    "method": request.method,
                    "policy": rule.name,
                    "error": str(error),
                },
            },
        )

        if settings.rate_limit_fail_open:
            return {
                "policy": rule.name,
                "limit": rule.max_requests,
                "remaining": rule.max_requests,
                "reset_seconds": rule.window_seconds,
            }

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter unavailable.",
        ) from error