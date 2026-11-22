"""QuantEdge Background RQ Worker Daemon"""
import os
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quantedge.worker_daemon")

sys.path.insert(0, os.path.abspath("."))


def run_worker():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    logger.info(f"Connecting to Redis queue at {redis_url}...")

    max_retries = 30
    conn = None

    import redis
    from rq import Worker, Queue

    for i in range(max_retries):
        try:
            conn = redis.from_url(redis_url)
            conn.ping()
            logger.info("Connected to Redis successfully.")
            break
        except Exception as e:
            logger.warning(f"Waiting for Redis... attempt {i+1}/{max_retries} ({e})")
            time.sleep(2)

    if not conn:
        logger.error("Could not connect to Redis. Worker exiting.")
        sys.exit(1)

    listen_queues = ["quantedge_backtests"]
    logger.info(f"Worker listening on queues: {listen_queues}")
    worker = Worker(listen_queues, connection=conn)
    worker.work()


if __name__ == "__main__":
    run_worker()
