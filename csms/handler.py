import logging
from datetime import datetime, timezone

from ocpp.routing import on
from ocpp.v16 import ChargePoint as OcppChargePoint
from ocpp.v16 import call_result
from ocpp.v16.enums import (
    Action,
    AuthorizationStatus,
    RegistrationStatus,
)

from database.repositories import (
    ChargePointRepository,
    IdTagRepository,
    TransactionRepository,
)

logger = logging.getLogger(__name__)


class ChargePointHandler(OcppChargePoint):
    """Handles OCPP 1.6 messages from a single charge point."""

    @on(Action.BootNotification)
    async def on_boot_notification(
        self,
        charge_point_vendor: str,
        charge_point_model: str,
        **kwargs,
    ) -> call_result.BootNotificationPayload:
        logger.info(
            "BootNotification from %s: vendor=%s model=%s",
            self.id,
            charge_point_vendor,
            charge_point_model,
        )
        await ChargePointRepository.upsert(
            self.id,
            {
                "vendor": charge_point_vendor,
                "model": charge_point_model,
                "status": "Available",
                "last_boot": datetime.now(timezone.utc).isoformat(),
            },
        )
        return call_result.BootNotificationPayload(
            current_time=datetime.now(timezone.utc).isoformat(),
            interval=10,
            status=RegistrationStatus.accepted,
        )

    @on(Action.Heartbeat)
    async def on_heartbeat(self, **kwargs) -> call_result.HeartbeatPayload:
        logger.debug("Heartbeat from %s", self.id)
        await ChargePointRepository.update_last_seen(self.id)
        return call_result.HeartbeatPayload(
            current_time=datetime.now(timezone.utc).isoformat()
        )

    @on(Action.Authorize)
    async def on_authorize(self, id_tag: str, **kwargs) -> call_result.AuthorizePayload:
        logger.info("Authorize request from %s for id_tag=%s", self.id, id_tag)
        tag = await IdTagRepository.get(id_tag)
        if tag and tag.get("status") == "Accepted":
            status = AuthorizationStatus.accepted
        else:
            status = AuthorizationStatus.invalid
        return call_result.AuthorizePayload(id_tag_info={"status": status})

    @on(Action.StartTransaction)
    async def on_start_transaction(
        self,
        connector_id: int,
        id_tag: str,
        meter_start: int,
        timestamp: str,
        **kwargs,
    ) -> call_result.StartTransactionPayload:
        logger.info(
            "StartTransaction from %s: connector=%s id_tag=%s meter_start=%s",
            self.id,
            connector_id,
            id_tag,
            meter_start,
        )
        tag = await IdTagRepository.get(id_tag)
        if tag and tag.get("status") == "Accepted":
            auth_status = AuthorizationStatus.accepted
            transaction_id = await TransactionRepository.create(
                {
                    "charge_point_id": self.id,
                    "connector_id": connector_id,
                    "id_tag": id_tag,
                    "meter_start": meter_start,
                    "start_time": timestamp,
                    "status": "Active",
                }
            )
        else:
            auth_status = AuthorizationStatus.invalid
            transaction_id = 0

        return call_result.StartTransactionPayload(
            transaction_id=transaction_id,
            id_tag_info={"status": auth_status},
        )

    @on(Action.StopTransaction)
    async def on_stop_transaction(
        self,
        transaction_id: int,
        meter_stop: int,
        timestamp: str,
        **kwargs,
    ) -> call_result.StopTransactionPayload:
        logger.info(
            "StopTransaction from %s: transaction_id=%s meter_stop=%s",
            self.id,
            transaction_id,
            meter_stop,
        )
        await TransactionRepository.stop(
            transaction_id,
            {
                "meter_stop": meter_stop,
                "stop_time": timestamp,
                "status": "Completed",
            },
        )
        return call_result.StopTransactionPayload()

    @on(Action.StatusNotification)
    async def on_status_notification(
        self,
        connector_id: int,
        error_code: str,
        status: str,
        **kwargs,
    ) -> call_result.StatusNotificationPayload:
        logger.info(
            "StatusNotification from %s: connector=%s status=%s error=%s",
            self.id,
            connector_id,
            status,
            error_code,
        )
        await ChargePointRepository.update_status(self.id, connector_id, status)
        return call_result.StatusNotificationPayload()

    @on(Action.MeterValues)
    async def on_meter_values(
        self,
        connector_id: int,
        meter_value: list,
        **kwargs,
    ) -> call_result.MeterValuesPayload:
        logger.debug(
            "MeterValues from %s: connector=%s values=%s",
            self.id,
            connector_id,
            meter_value,
        )
        transaction_id = kwargs.get("transaction_id")
        if transaction_id is not None:
            await TransactionRepository.add_meter_values(
                transaction_id, meter_value
            )
        return call_result.MeterValuesPayload()
