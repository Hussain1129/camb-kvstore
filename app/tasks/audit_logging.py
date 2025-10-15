import redis
import json
from huey import crontab
from datetime import datetime
from typing import Dict, Any
from app.tasks import huey
from app.config import settings
from app.utils.logger import get_logger
from app.utils.metrics import background_task_count, background_task_duration, track_time

logger = get_logger(__name__)


@huey.task()
@track_time(background_task_duration, {"task_name": "log_audit_event"})
def log_audit_event(event_type: str, tenant_id: str, details: Dict[str, Any]):
    """
    Task to log audit events for key-value operations.
    Stores audit logs in Redis with a TTL of 30 days.
    """
    try:
        logger.info(f"Logging audit event: {event_type} for tenant: {tenant_id}")

        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        redis_client.ping()

        audit_event = {
            "event_type": event_type,
            "tenant_id": tenant_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details
        }

        audit_key = f"audit:{tenant_id}:{datetime.utcnow().timestamp()}"

        redis_client.setex(
            audit_key,
            2592000,
            json.dumps(audit_event)
        )

        logger.debug(f"Audit event logged: {event_type} for tenant: {tenant_id}")

        background_task_count.labels(task_name="log_audit_event", status="success").inc()

        redis_client.close()

        return True

    except Exception as e:
        logger.error(f"Error logging audit event: {str(e)}")
        background_task_count.labels(task_name="log_audit_event", status="error").inc()
        raise


@huey.periodic_task(crontab(hour='0', minute='0'))       # schedule to run at everyday midnight
@track_time(background_task_duration, {"task_name": "aggregate_audit_logs"})
def aggregate_audit_logs():
    """
    Periodic task to aggregate audit logs daily.
    Runs at midnight to generate daily statistics.
    """
    try:
        logger.info("Starting audit log aggregation")

        aggregation_data = {}

        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        redis_client.ping()

        for key in redis_client.scan_iter(match="audit:*"):
            try:
                audit_data = json.loads(redis_client.get(key))
                tenant_id = audit_data["tenant_id"]
                event_type = audit_data["event_type"]

                if tenant_id not in aggregation_data:
                    aggregation_data[tenant_id] = {}

                if event_type not in aggregation_data[tenant_id]:
                    aggregation_data[tenant_id][event_type] = 0

                aggregation_data[tenant_id][event_type] += 1

            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse audit log {key}: {str(e)}")
                continue

        for tenant_id, stats in aggregation_data.items():
            daily_stats_key = f"audit_stats:{tenant_id}:{datetime.utcnow().date().isoformat()}"
            redis_client.setex(
                daily_stats_key,
                2592000,
                json.dumps(stats)
            )

        logger.info(f"Audit log aggregation completed for {len(aggregation_data)} tenants")

        background_task_count.labels(task_name="aggregate_audit_logs", status="success").inc()

        redis_client.close()

        return len(aggregation_data)

    except Exception as e:
        logger.error(f"Error in audit log aggregation: {str(e)}")
        background_task_count.labels(task_name="aggregate_audit_logs", status="error").inc()
        raise


def get_tenant_audit_logs(tenant_id: str, limit: int = 100):
    """
    Retrieve audit logs for a specific tenant.
    Returns the most recent audit events.
    """
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        redis_client.ping()

        audit_logs = []

        for key in redis_client.scan_iter(match=f"audit:{tenant_id}:*"):
            try:
                audit_data = json.loads(redis_client.get(key))
                audit_logs.append(audit_data)
            except (json.JSONDecodeError, TypeError):
                continue

        audit_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        redis_client.close()

        return audit_logs[:limit]

    except Exception as e:
        logger.error(f"Error retrieving audit logs for tenant {tenant_id}: {str(e)}")
        raise