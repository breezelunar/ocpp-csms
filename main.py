import asyncio
import logging
import threading

import uvicorn

import config
from csms.server import start_websocket_server
from dashboard.routes import app
from database.connection import connect_db, disconnect_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_websocket_server() -> None:
    await start_websocket_server(config.WS_HOST, config.WS_PORT)


def run_http_server() -> None:
    uvicorn.run(
        app,
        host=config.HTTP_HOST,
        port=config.HTTP_PORT,
        log_level="info",
    )


async def main() -> None:
    await connect_db()
    try:
        http_thread = threading.Thread(target=run_http_server, daemon=True)
        http_thread.start()
        logger.info("HTTP dashboard started on %s:%s", config.HTTP_HOST, config.HTTP_PORT)

        await run_websocket_server()
    finally:
        await disconnect_db()


if __name__ == "__main__":
    asyncio.run(main())
