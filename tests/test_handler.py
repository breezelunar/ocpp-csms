"""
Tests for ChargePointHandler (csms/handler.py).

The handler relies on database repositories.  We mock those so the
tests don't need a live MongoDB instance.
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from csms.handler import ChargePointHandler


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_handler(cp_id: str = "CP-001") -> ChargePointHandler:
    """Return a ChargePointHandler with a mocked websocket connection."""
    ws = MagicMock()
    ws.subprotocol = "ocpp1.6"
    ws.send = AsyncMock()
    ws.recv = AsyncMock(side_effect=asyncio.CancelledError)
    return ChargePointHandler(cp_id, ws)


# ── BootNotification ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("csms.handler.ChargePointRepository.upsert", new_callable=AsyncMock)
async def test_boot_notification_returns_accepted(mock_upsert):
    handler = _make_handler()
    result = await handler.on_boot_notification(
        charge_point_vendor="Acme",
        charge_point_model="EV-3000",
    )
    from ocpp.v16.enums import RegistrationStatus
    assert result.status == RegistrationStatus.accepted
    mock_upsert.assert_awaited_once()


@pytest.mark.asyncio
@patch("csms.handler.ChargePointRepository.upsert", new_callable=AsyncMock)
async def test_boot_notification_stores_vendor_and_model(mock_upsert):
    handler = _make_handler("CP-TEST")
    await handler.on_boot_notification(
        charge_point_vendor="TestVendor",
        charge_point_model="TestModel",
    )
    call_args = mock_upsert.call_args
    assert call_args[0][0] == "CP-TEST"
    data = call_args[0][1]
    assert data["vendor"] == "TestVendor"
    assert data["model"] == "TestModel"


# ── Heartbeat ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("csms.handler.ChargePointRepository.update_last_seen", new_callable=AsyncMock)
async def test_heartbeat_returns_current_time(mock_update):
    handler = _make_handler()
    result = await handler.on_heartbeat()
    assert result.current_time is not None
    mock_update.assert_awaited_once_with("CP-001")


# ── Authorize ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch(
    "csms.handler.IdTagRepository.get",
    new_callable=AsyncMock,
    return_value={"_id": "RFID-001", "status": "Accepted"},
)
async def test_authorize_accepted(mock_get):
    handler = _make_handler()
    result = await handler.on_authorize(id_tag="RFID-001")
    from ocpp.v16.enums import AuthorizationStatus
    assert result.id_tag_info["status"] == AuthorizationStatus.accepted


@pytest.mark.asyncio
@patch(
    "csms.handler.IdTagRepository.get",
    new_callable=AsyncMock,
    return_value=None,
)
async def test_authorize_invalid_unknown_tag(mock_get):
    handler = _make_handler()
    result = await handler.on_authorize(id_tag="UNKNOWN")
    from ocpp.v16.enums import AuthorizationStatus
    assert result.id_tag_info["status"] == AuthorizationStatus.invalid


@pytest.mark.asyncio
@patch(
    "csms.handler.IdTagRepository.get",
    new_callable=AsyncMock,
    return_value={"_id": "RFID-BLK", "status": "Blocked"},
)
async def test_authorize_blocked_tag(mock_get):
    handler = _make_handler()
    result = await handler.on_authorize(id_tag="RFID-BLK")
    from ocpp.v16.enums import AuthorizationStatus
    assert result.id_tag_info["status"] == AuthorizationStatus.invalid


# ── StartTransaction ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("csms.handler.TransactionRepository.create", new_callable=AsyncMock, return_value=42)
@patch(
    "csms.handler.IdTagRepository.get",
    new_callable=AsyncMock,
    return_value={"_id": "RFID-001", "status": "Accepted"},
)
async def test_start_transaction_accepted(mock_get, mock_create):
    handler = _make_handler()
    result = await handler.on_start_transaction(
        connector_id=1,
        id_tag="RFID-001",
        meter_start=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    from ocpp.v16.enums import AuthorizationStatus
    assert result.transaction_id == 42
    assert result.id_tag_info["status"] == AuthorizationStatus.accepted
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
@patch("csms.handler.TransactionRepository.create", new_callable=AsyncMock, return_value=7)
@patch(
    "csms.handler.IdTagRepository.get",
    new_callable=AsyncMock,
    return_value=None,
)
async def test_start_transaction_invalid_tag(mock_get, mock_create):
    handler = _make_handler()
    result = await handler.on_start_transaction(
        connector_id=1,
        id_tag="BAD-TAG",
        meter_start=100,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    from ocpp.v16.enums import AuthorizationStatus
    assert result.id_tag_info["status"] == AuthorizationStatus.invalid
    mock_create.assert_not_awaited()


# ── StopTransaction ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("csms.handler.TransactionRepository.stop", new_callable=AsyncMock)
async def test_stop_transaction(mock_stop):
    handler = _make_handler()
    await handler.on_stop_transaction(
        transaction_id=42,
        meter_stop=500,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    mock_stop.assert_awaited_once()
    call_data = mock_stop.call_args[0][1]
    assert call_data["meter_stop"] == 500
    assert call_data["status"] == "Completed"


# ── StatusNotification ────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("csms.handler.ChargePointRepository.update_status", new_callable=AsyncMock)
async def test_status_notification(mock_update):
    handler = _make_handler()
    await handler.on_status_notification(
        connector_id=1,
        error_code="NoError",
        status="Charging",
    )
    mock_update.assert_awaited_once_with("CP-001", 1, "Charging")


# ── MeterValues ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@patch("csms.handler.TransactionRepository.add_meter_values", new_callable=AsyncMock)
async def test_meter_values_with_transaction(mock_add):
    handler = _make_handler()
    values = [{"timestamp": "2024-01-01T00:00:00Z", "sampledValue": []}]
    await handler.on_meter_values(
        connector_id=1,
        meter_value=values,
        transaction_id=42,
    )
    mock_add.assert_awaited_once_with(42, values)


@pytest.mark.asyncio
@patch("csms.handler.TransactionRepository.add_meter_values", new_callable=AsyncMock)
async def test_meter_values_without_transaction(mock_add):
    handler = _make_handler()
    await handler.on_meter_values(connector_id=1, meter_value=[])
    mock_add.assert_not_awaited()
