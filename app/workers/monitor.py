import httpx
import asyncio
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.endpoint import Endpoint, EndpointStatus
from app.models.check import Check, FailureReason
from app.models.alert import AlertType, AlertSeverity
from app.services.alert_service import create_alert
from app.core.logging import get_logger

logger = get_logger(__name__)


async def ping_endpoint(endpoint: Endpoint, db: AsyncSession) -> Check:
    """
    Hit the endpoint, record the result, update endpoint state,
    trigger alerts if needed. Returns the Check record.
    """
    success = False
    status_code = None
    latency_ms = None
    failure_reason = FailureReason.NONE
    error_message = None

    start = datetime.utcnow()

    try:
        async with httpx.AsyncClient(timeout=endpoint.timeout_seconds) as client:
            response = await client.request(
                method=endpoint.method.value,
                url=endpoint.url,
                headers=endpoint.headers or {},
                json=endpoint.body if endpoint.body else None,
            )

        latency_ms = (datetime.utcnow() - start).total_seconds() * 1000
        status_code = response.status_code

        if status_code == endpoint.expected_status_code:
            success = True
        else:
            failure_reason = FailureReason.WRONG_STATUS
            error_message = f"Expected {endpoint.expected_status_code}, got {status_code}"

    except httpx.TimeoutException:
        failure_reason = FailureReason.TIMEOUT
        error_message = f"Request timed out after {endpoint.timeout_seconds}s"

    except httpx.ConnectError:
        failure_reason = FailureReason.CONNECTION_ERROR
        error_message = "Could not connect to host"

    except httpx.RequestError as e:
        failure_reason = FailureReason.NETWORK_ERROR
        error_message = str(e)

    # --- save the check record ---
    check = Check(
        endpoint_id=endpoint.id,
        success=success,
        status_code=status_code,
        latency_ms=latency_ms,
        failure_reason=failure_reason,
        error_message=error_message,
        checked_at=start,
    )
    db.add(check)

    # --- update endpoint state ---
    endpoint.last_checked_at = start

    if success:
        was_failing = endpoint.status == EndpointStatus.FAILING

        endpoint.consecutive_failures = 0
        endpoint.last_success_at = start
        endpoint.status = EndpointStatus.ACTIVE

        # recovered — fire a recovery alert
        if was_failing:
            await create_alert(
                db=db,
                endpoint=endpoint,
                alert_type=AlertType.ENDPOINT_RECOVERED,
                severity=AlertSeverity.INFO,
                message=f"{endpoint.name} recovered after being down.",
            )

        # check latency threshold even on success
        if latency_ms and latency_ms > endpoint.latency_threshold_ms:
            await create_alert(
                db=db,
                endpoint=endpoint,
                alert_type=AlertType.HIGH_LATENCY,
                severity=AlertSeverity.WARNING,
                message=(
                    f"{endpoint.name} responded in {latency_ms:.1f}ms "
                    f"(threshold: {endpoint.latency_threshold_ms}ms)"
                ),
            )
    else:
        endpoint.consecutive_failures += 1
        endpoint.status = EndpointStatus.FAILING

        logger.warning(
            f"Check FAILED | endpoint={endpoint.name} | reason={failure_reason} "
            f"| consecutive={endpoint.consecutive_failures}"
        )

        # only alert when we hit the threshold — not on every single failure
        if endpoint.consecutive_failures == endpoint.max_consecutive_failures:
            await create_alert(
                db=db,
                endpoint=endpoint,
                alert_type=AlertType.ENDPOINT_DOWN,
                severity=AlertSeverity.CRITICAL,
                message=(
                    f"{endpoint.name} has failed {endpoint.consecutive_failures} "
                    f"consecutive checks. Reason: {failure_reason}. {error_message or ''}"
                ),
            )

    await db.flush()
    return check