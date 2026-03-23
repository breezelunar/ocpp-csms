import logging

import websockets
from websockets.server import WebSocketServerProtocol

from csms.handler import ChargePointHandler

logger = logging.getLogger(__name__)


async def on_connect(websocket: WebSocketServerProtocol, path: str) -> None:
    """Handle a new WebSocket connection from a charge point."""
    charge_point_id = path.strip("/").split("/")[-1]
    logger.info("Charge point connected: %s", charge_point_id)

    cp = ChargePointHandler(charge_point_id, websocket)
    try:
        await cp.start()
    except websockets.exceptions.ConnectionClosedOK:
        logger.info("Charge point disconnected (clean): %s", charge_point_id)
    except websockets.exceptions.ConnectionClosedError as exc:
        logger.warning("Charge point disconnected (error): %s — %s", charge_point_id, exc)
    except Exception as exc:
        logger.exception("Unexpected error for %s: %s", charge_point_id, exc)


async def start_websocket_server(host: str, port: int) -> None:
    """Start the OCPP WebSocket server and serve forever."""
    logger.info("Starting OCPP WebSocket server on ws://%s:%s", host, port)
    async with websockets.serve(
        on_connect,
        host,
        port,
        subprotocols=["ocpp1.6"],
    ):
        logger.info("OCPP WebSocket server is running")
        import asyncio
        await asyncio.Future()  # run forever
