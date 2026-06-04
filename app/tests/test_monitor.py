import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endpoint import Endpoint, HttpMethod, EndpointStatus
from app.models.check import FailureReason
from app.workers.monitor import ping_endpoint

pytestmark = pytest.mark.asyncio


def make_endpoint(**kwargs) -> Endpoint:
    """Helper — build an Endpoint with sensible defaults."""
    defaults = dict(
        id=uuid4(),
        name="Test",
        url="https://example.com/api",
        method=HttpMethod.GET,
        headers={},
        body=None,
        expected_status_code=200,
        timeout_seconds=10,
        latency_threshold_ms=2000.0,
        max_consecutive_failures=3,
        consecutive_failures=0,
        status=EndpointStatus.ACTIVE,
        last_checked_at=None,
        last_success_at=None,
    )
    defaults.update(kwargs)
    endpoint = Endpoint()
    for k, v in defaults.items():
        setattr(endpoint, k, v)
    return endpoint


def make_mock_db() -> AsyncSession:
    """Mock DB session — we don't want real DB writes in unit tests."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


async def test_successful_check():
    endpoint = make_endpoint()
    db = make_mock_db()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=mock_response
        )
        check = await ping_endpoint(endpoint, db)

    assert check.success is True
    assert check.status_code == 200
    assert check.failure_reason == FailureReason.NONE
    assert check.latency_ms is not None
    assert endpoint.consecutive_failures == 0
    assert endpoint.status == EndpointStatus.ACTIVE


async def test_wrong_status_code():
    endpoint = make_endpoint(expected_status_code=200)
    db = make_mock_db()

    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=mock_response
        )
        check = await ping_endpoint(endpoint, db)

    assert check.success is False
    assert check.status_code == 500
    assert check.failure_reason == FailureReason.WRONG_STATUS
    assert endpoint.consecutive_failures == 1
    assert endpoint.status == EndpointStatus.FAILING


async def test_timeout_failure():
    import httpx
    endpoint = make_endpoint()
    db = make_mock_db()

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=httpx.TimeoutException("timed out")
        )
        check = await ping_endpoint(endpoint, db)

    assert check.success is False
    assert check.failure_reason == FailureReason.TIMEOUT
    assert check.latency_ms is None
    assert endpoint.consecutive_failures == 1


async def test_connection_error():
    import httpx
    endpoint = make_endpoint()
    db = make_mock_db()

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        check = await ping_endpoint(endpoint, db)

    assert check.success is False
    assert check.failure_reason == FailureReason.CONNECTION_ERROR


async def test_alert_triggered_on_consecutive_failures():
    """Alert should only fire when consecutive failures == threshold, not before."""
    endpoint = make_endpoint(
        consecutive_failures=2,   # one away from threshold
        max_consecutive_failures=3,
        status=EndpointStatus.FAILING,
    )
    db = make_mock_db()

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client, \
         patch("app.workers.monitor.create_alert", new_callable=AsyncMock) as mock_alert:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        await ping_endpoint(endpoint, db)

    # 2+1 = 3 which equals threshold, alert must fire
    mock_alert.assert_called_once()
    call_kwargs = mock_alert.call_args.kwargs
    assert call_kwargs["alert_type"].value == "endpoint_down"


async def test_recovery_alert_triggered():
    """When endpoint was FAILING and now succeeds, a recovery alert fires."""
    endpoint = make_endpoint(
        consecutive_failures=5,
        status=EndpointStatus.FAILING,
    )
    db = make_mock_db()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client, \
         patch("app.workers.monitor.create_alert", new_callable=AsyncMock) as mock_alert:
        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=mock_response
        )
        await ping_endpoint(endpoint, db)

    mock_alert.assert_called_once()
    call_kwargs = mock_alert.call_args.kwargs
    assert call_kwargs["alert_type"].value == "endpoint_recovered"
    assert endpoint.consecutive_failures == 0
    assert endpoint.status == EndpointStatus.ACTIVE


async def test_high_latency_alert():
    """Latency over threshold should trigger a warning alert even on success."""
    endpoint = make_endpoint(latency_threshold_ms=100.0)
    db = make_mock_db()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("app.workers.monitor.httpx.AsyncClient") as mock_client, \
         patch("app.workers.monitor.create_alert", new_callable=AsyncMock) as mock_alert, \
         patch("app.workers.monitor.datetime") as mock_dt:

        # simulate 500ms latency by manipulating datetime
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 0, 0, 500000)  # 500ms later
        mock_dt.utcnow.side_effect = [start_time, end_time]

        mock_client.return_value.__aenter__.return_value.request = AsyncMock(
            return_value=mock_response
        )
        check = await ping_endpoint(endpoint, db)

    mock_alert.assert_called_once()
    call_kwargs = mock_alert.call_args.kwargs
    assert call_kwargs["alert_type"].value == "high_latency"