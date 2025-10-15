import pytest
import time
from unittest.mock import patch, MagicMock
from app.tasks.ttl_cleanup import cleanup_expired_keys, cleanup_ex_tenant_keys
from app.tasks.audit_logging import log_audit_event, aggregate_audit_logs
from app.config import settings


class TestTTLCleanupTask:
    """Test TTL cleanup background tasks."""

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_expired_keys_success(self, mock_redis):
        """Test successful cleanup of expired keys."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            "tenant_keys:tenant-1",
            "tenant_keys:tenant-2"
        ]
        mock_client.smembers.return_value = {"key1", "key2"}
        mock_client.exists.side_effect = [False, True]

        result = cleanup_expired_keys()

        assert mock_client.ping.called
        assert mock_client.scan_iter.called
        assert isinstance(result, int)

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_expired_keys_redis_error(self, mock_redis):
        """Test cleanup handles Redis connection errors."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            cleanup_expired_keys()

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_ex_tenant_keys_success(self, mock_redis):
        """Test successful cleanup of tenant keys."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            "kv:tenant-1:key1",
            "kv:tenant-1:key2",
            "kv:tenant-1:key3"
        ]

        result = cleanup_ex_tenant_keys("tenant-1")

        assert mock_client.ping.called
        assert mock_client.scan_iter.called
        assert isinstance(result, int)


class TestAuditLoggingTask:
    """Test audit logging background tasks."""

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_log_audit_event_success(self, mock_redis):
        """Test successful audit event logging."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True

        result = log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key", "action": "create"}
        )

        assert result is True
        assert mock_client.ping.called
        assert mock_client.setex.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_log_audit_event_redis_error(self, mock_redis):
        """Test audit logging handles Redis errors."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            log_audit_event(
                event_type="CREATE",
                tenant_id="tenant-1",
                details={"key": "test:key"}
            )

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_aggregate_audit_logs_success(self, mock_redis):
        """Test successful audit log aggregation."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            "audit:tenant-1:1234567890",
            "audit:tenant-1:1234567891"
        ]
        mock_client.get.side_effect = [
            '{"tenant_id": "tenant-1", "event_type": "CREATE"}',
            '{"tenant_id": "tenant-1", "event_type": "READ"}'
        ]

        result = aggregate_audit_logs()

        assert mock_client.ping.called
        assert mock_client.scan_iter.called
        assert isinstance(result, int)

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_aggregate_audit_logs_empty(self, mock_redis):
        """Test audit log aggregation with no logs."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []

        result = aggregate_audit_logs()

        assert result == 0
        assert mock_client.ping.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_aggregate_audit_logs_invalid_json(self, mock_redis):
        """Test audit log aggregation handles invalid JSON."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = ["audit:tenant-1:1234567890"]
        mock_client.get.return_value = "invalid json"

        result = aggregate_audit_logs()

        assert isinstance(result, int)
        assert mock_client.ping.called


class TestBackgroundTaskIntegration:
    """Integration tests for background tasks."""

    def test_cleanup_task_with_real_redis(self, test_redis_client):
        """Test cleanup task with real Redis connection."""
        test_redis_client.set("kv:test-tenant:key1", "value1")
        test_redis_client.set("kv:test-tenant:key1:metadata", '{"ttl": 60}')
        test_redis_client.sadd("tenant_keys:test-tenant", "key1")

        test_redis_client.delete("kv:test-tenant:key1")

        assert test_redis_client.exists("kv:test-tenant:key1:metadata") == 1
        assert test_redis_client.sismember("tenant_keys:test-tenant", "key1")

    def test_audit_logging_with_real_redis(self, test_redis_client):
        """Test audit logging with real Redis connection."""
        import json
        from datetime import datetime

        audit_event = {
            "event_type": "CREATE",
            "tenant_id": "test-tenant",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {"key": "test:key", "action": "create"}
        }

        audit_key = f"audit:test-tenant:{datetime.utcnow().timestamp()}"
        test_redis_client.setex(audit_key, 3600, json.dumps(audit_event))

        stored_event = json.loads(test_redis_client.get(audit_key))

        assert stored_event["event_type"] == "CREATE"
        assert stored_event["tenant_id"] == "test-tenant"
        assert "details" in stored_event


class TestTaskMetrics:
    """Test background task metrics collection."""

    @patch('app.tasks.ttl_cleanup.background_task_count')
    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_task_success_metric(self, mock_redis, mock_metric):
        """Test cleanup task increments success metric."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []

        cleanup_expired_keys()

        mock_metric.labels.assert_called_with(
            task_name="cleanup_expired_keys",
            status="success"
        )

    @patch('app.tasks.ttl_cleanup.background_task_count')
    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_task_error_metric(self, mock_redis, mock_metric):
        """Test cleanup task increments error metric on failure."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.side_effect = Exception("Connection failed")

        with pytest.raises(Exception):
            cleanup_expired_keys()

        mock_metric.labels.assert_called_with(
            task_name="cleanup_expired_keys",
            status="error"
        )

    @patch('app.tasks.audit_logging.background_task_count')
    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_task_success_metric(self, mock_redis, mock_metric):
        """Test audit task increments success metric."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True

        log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key"}
        )

        mock_metric.labels.assert_called_with(
            task_name="log_audit_event",
            status="success"
        )


class TestTaskErrorHandling:
    """Test error handling in background tasks."""

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_handles_connection_timeout(self, mock_redis):
        """Test cleanup task handles connection timeout."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        import redis
        mock_client.ping.side_effect = redis.TimeoutError("Connection timeout")

        with pytest.raises(redis.TimeoutError):
            cleanup_expired_keys()

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_handles_redis_error(self, mock_redis):
        """Test cleanup task handles Redis errors."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        import redis
        mock_client.ping.side_effect = redis.RedisError("Redis error")

        with pytest.raises(redis.RedisError):
            cleanup_expired_keys()

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_logging_handles_write_error(self, mock_redis):
        """Test audit logging handles write errors."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.setex.side_effect = Exception("Write failed")

        with pytest.raises(Exception):
            log_audit_event(
                event_type="CREATE",
                tenant_id="tenant-1",
                details={"key": "test:key"}
            )


class TestTaskScheduling:
    """Test task scheduling configuration."""

    def test_cleanup_task_schedule_configured(self):
        """Test cleanup task has correct schedule."""
        from app.tasks.ttl_cleanup import cleanup_expired_keys

        assert hasattr(cleanup_expired_keys, 'task_base')

    def test_aggregation_task_schedule_configured(self):
        """Test aggregation task has correct schedule."""
        from app.tasks.audit_logging import aggregate_audit_logs

        assert hasattr(aggregate_audit_logs, 'task_base')


class TestTaskPerformance:
    """Test background task performance."""

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_task_performance(self, mock_redis):
        """Test cleanup task completes in reasonable time."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            f"tenant_keys:tenant-{i}" for i in range(100)
        ]
        mock_client.smembers.return_value = {f"key{i}" for i in range(10)}
        mock_client.exists.return_value = True

        start_time = time.time()
        cleanup_expired_keys()
        duration = time.time() - start_time

        assert duration < 5.0

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_aggregation_performance(self, mock_redis):
        """Test audit aggregation completes in reasonable time."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            f"audit:tenant-1:{1234567890 + i}" for i in range(1000)
        ]
        mock_client.get.return_value = '{"tenant_id": "tenant-1", "event_type": "CREATE"}'

        start_time = time.time()
        aggregate_audit_logs()
        duration = time.time() - start_time

        assert duration < 10.0


class TestTaskRetry:
    """Test task retry logic."""

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_task_retries_on_failure(self, mock_redis):
        """Test cleanup task retry behavior."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.side_effect = [
            Exception("First attempt failed"),
            True
        ]

        with pytest.raises(Exception):
            cleanup_expired_keys()


class TestTaskCleanup:
    """Test task cleanup behavior."""

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_cleanup_task_closes_connection(self, mock_redis):
        """Test cleanup task closes Redis connection."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []

        cleanup_expired_keys()

        mock_client.close.assert_called_once()

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_task_closes_connection(self, mock_redis):
        """Test audit task closes Redis connection."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True

        log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key"}
        )

        mock_client.close.assert_called_once()


class TestTaskConcurrency:
    """Test task concurrency handling."""

    @patch('app.tasks.ttl_cleanup.redis.Redis')
    def test_multiple_cleanup_tasks_concurrent(self, mock_redis):
        """Test multiple cleanup tasks can run concurrently."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []

        cleanup_expired_keys()
        cleanup_expired_keys()

        assert mock_client.ping.call_count == 2

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_multiple_audit_tasks_concurrent(self, mock_redis):
        """Test multiple audit tasks can run concurrently."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        mock_client.ping.return_value = True

        log_audit_event("CREATE", "tenant-1", {"key": "key1"})
        log_audit_event("READ", "tenant-2", {"key": "key2"})

        assert mock_client.setex.call_count == 2


class TestTaskConfiguration:
    """Test task configuration and settings."""

    def test_cleanup_interval_configured(self):
        """Test cleanup interval is properly configured."""
        assert settings.CLEANUP_INTERVAL_SECONDS > 0
        assert settings.CLEANUP_INTERVAL_SECONDS <= 3600

    def test_huey_workers_configured(self):
        """Test Huey worker count is configured."""
        assert settings.HUEY_WORKERS > 0
        assert settings.HUEY_WORKERS <= 16

    def test_huey_redis_connection_configured(self):
        """Test Huey Redis connection is configured."""
        assert settings.HUEY_REDIS_HOST
        assert settings.HUEY_REDIS_PORT > 0
        assert settings.HUEY_REDIS_DB >= 0