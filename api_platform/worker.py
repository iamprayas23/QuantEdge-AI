"""Async Worker & Job Dispatcher

Supports Redis/RQ background worker and in-memory background worker fallback.
"""
import os
import threading
import logging
from typing import Callable, Any
from uuid import UUID

logger = logging.getLogger("quantedge.worker")

_redis_conn = None
_rq_queue = None


def get_queue():
    global _redis_conn, _rq_queue
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    use_in_memory = os.getenv("USE_IN_MEMORY_QUEUE", "false").lower() in ("true", "1")

    if use_in_memory:
        return None

    if _rq_queue is not None:
        return _rq_queue

    try:
        import redis
        from rq import Queue
        _redis_conn = redis.from_url(redis_url, socket_connect_timeout=1)
        _redis_conn.ping()
        _rq_queue = Queue("quantedge_backtests", connection=_redis_conn)
        logger.info("Connected to Redis worker queue.")
        return _rq_queue
    except Exception as e:
        logger.warning(f"Redis queue unavailable ({e}), using in-memory background worker.")
        return None


def dispatch_job(func: Callable, *args: Any, **kwargs: Any):
    """
    Dispatch a job asynchronously. Uses Redis Queue if available,
    otherwise spawns a daemon thread.
    """
    q = get_queue()
    if q is not None:
        try:
            return q.enqueue(func, *args, **kwargs)
        except Exception as e:
            logger.warning(f"Failed to enqueue to Redis ({e}), falling back to thread.")

    # In-memory thread fallback
    t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
    t.start()
    return t
