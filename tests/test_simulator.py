"""
Simple charge-point simulator used for integration/manual testing.

Run directly with:
    python -m tests.test_simulator ws://localhost:9000/CP-SIM-001

The simulator:
1. Connects to the CSMS via WebSocket.
2. Sends BootNotification.
3. Sends a Heartbeat.
4. Authorizes an RFID tag.
5. Starts and then stops a transaction.
6. Disconnects.
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone

import websockets
from ocpp.v16 import ChargePoint as OcppChargePoint
from ocpp.v16 import call
from ocpp.v16.enums import (
    ChargePointErrorCode,
    ChargePointStatus,
    Reason,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("cp-simulator")

DEFAULT_URL = "ws://localhost:9000/CP-SIM-001"
ID_TAG = "RFID-TEST-001"


class SimulatedChargePoint(OcppChargePoint):
    """Minimal OCPP 1.6 charge point for simulation / testing."""

    async def send_boot_notification(self) -> bool:
        request = call.BootNotificationPayload(
            charge_point_vendor="SimVendor",
            charge_point_model="SimModel",
        )
        response = await self.call(request)
        logger.info("BootNotification response: status=%s", response.status)
        return response.status == "Accepted"

    async def send_heartbeat(self) -> None:
        request = call.HeartbeatPayload()
        response = await self.call(request)
        logger.info("Heartbeat response: current_time=%s", response.current_time)

    async def authorize(self, id_tag: str) -> str:
        request = call.AuthorizePayload(id_tag=id_tag)
        response = await self.call(request)
        status = response.id_tag_info["status"]
        logger.info("Authorize response for %s: status=%s", id_tag, status)
        return status

    async def send_status_notification(
        self, connector_id: int, status: str, error_code: str = "NoError"
    ) -> None:
        request = call.StatusNotificationPayload(
            connector_id=connector_id,
            error_code=error_code,
            status=status,
        )
        await self.call(request)
        logger.info("StatusNotification sent: connector=%s status=%s", connector_id, status)

    async def start_transaction(
        self, connector_id: int, id_tag: str, meter_start: int = 0
    ) -> int:
        request = call.StartTransactionPayload(
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=meter_start,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        response = await self.call(request)
        logger.info(
            "StartTransaction response: transaction_id=%s auth_status=%s",
            response.transaction_id,
            response.id_tag_info["status"],
        )
        return response.transaction_id

    async def stop_transaction(
        self,
        transaction_id: int,
        meter_stop: int,
        reason: str = Reason.local,
    ) -> None:
        request = call.StopTransactionPayload(
            transaction_id=transaction_id,
            meter_stop=meter_stop,
            timestamp=datetime.now(timezone.utc).isoformat(),
            reason=reason,
        )
        await self.call(request)
        logger.info("StopTransaction sent: transaction_id=%s meter_stop=%s", transaction_id, meter_stop)


async def run_simulation(url: str) -> None:
    logger.info("Connecting to CSMS at %s", url)
    async with websockets.connect(
        url,
        subprotocols=["ocpp1.6"],
    ) as ws:
        cp_id = url.rstrip("/").split("/")[-1]
        cp = SimulatedChargePoint(cp_id, ws)

        # Run the ChargePoint message loop in the background
        loop_task = asyncio.create_task(cp.start())

        try:
            # 1. Boot
            accepted = await cp.send_boot_notification()
            if not accepted:
                logger.error("BootNotification rejected — aborting simulation")
                return

            await asyncio.sleep(0.5)

            # 2. Status: Available
            await cp.send_status_notification(1, ChargePointStatus.available)

            # 3. Heartbeat
            await cp.send_heartbeat()

            # 4. Authorize
            auth_status = await cp.authorize(ID_TAG)

            # 5. Start transaction
            if auth_status == "Accepted":
                await cp.send_status_notification(1, ChargePointStatus.charging)
                tx_id = await cp.start_transaction(1, ID_TAG, meter_start=0)

                # Simulate some charging time
                await asyncio.sleep(1)

                # 6. Stop transaction
                await cp.stop_transaction(tx_id, meter_stop=1500)
                await cp.send_status_notification(1, ChargePointStatus.available)
            else:
                logger.warning("Authorization failed; skipping transaction")

            logger.info("Simulation completed successfully")

        finally:
            loop_task.cancel()
            try:
                await loop_task
            except (asyncio.CancelledError, Exception):
                pass


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    asyncio.run(run_simulation(url))
