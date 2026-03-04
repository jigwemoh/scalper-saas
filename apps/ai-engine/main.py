"""
AI Engine entrypoint.
Starts the signal scan loop and weekly retraining loop.
"""
import asyncio
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("ai-engine")


async def main() -> None:
    from scheduler.scan_job import start_scan_loop, get_predictor
    from scheduler.retrain_job import start_retrain_loop

    logger.info("AI Engine starting up...")
    logger.info(f"Bridge URL: {os.getenv('MT5_BRIDGE_URL', 'http://localhost:9000')}")
    logger.info(f"Redis URL: {os.getenv('REDIS_URL', 'redis://localhost:6379/0')}")

    predictor = get_predictor()  # Shared singleton — passed to retrain so it can reload in-place

    await asyncio.gather(
        start_scan_loop(),
        start_retrain_loop(predictor),
    )


if __name__ == "__main__":
    asyncio.run(main())
