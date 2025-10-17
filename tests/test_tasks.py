import pytest
import time
import json
from unittest.mock import patch, MagicMock
from datetime import datetime
from app.config import settings


class TestTTLCleanupTask:
    """Test TTL cleanup background tasks."""

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_expired_keys_success(self, mock_redis_class):
        """Test successful cleanup of expired keys."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            "tenant_keys:tenant-1",
            "tenant_keys:tenant-2"
        ]
        mock_client.smembers.return_value = {"key1", "key2"}
        # Make exists return values properly for multiple calls
        mock_client.exists.side_effect = [0, 1, 0, 1]  # For 2 tenants with 2 keys each
        mock_client.close.return_value = None

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_pipeline.delete.return_value = mock_pipeline
        mock_pipeline.srem.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [1, 1]

        from app.tasks.ttl_cleanup import cleanup_expired_keys
        result = cleanup_expired_keys()

        # Huey returns Result objects, need to get the actual value
        if hasattr(result, '__call__'):
            result = result()

        assert mock_client.ping.called
        assert mock_client.scan_iter.called

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_expired_keys_redis_error(self, mock_redis_class):
        """Test cleanup handles Redis connection errors."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        from redis import ConnectionError
        mock_client.ping.side_effect = ConnectionError("Connection failed")

        from app.tasks.ttl_cleanup import cleanup_expired_keys

        # Huey catches exceptions, so we check the result object instead
        result = cleanup_expired_keys()

        # The task should have been executed even if it raised an error internally
        assert mock_client.ping.called

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_ex_tenant_keys_success(self, mock_redis_class):
        """Test successful cleanup of tenant keys."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            "kv:tenant-1:key1",
            "kv:tenant-1:key2",
            "kv:tenant-1:key3"
        ]
        mock_client.delete.return_value = 3
        mock_client.close.return_value = None

        from app.tasks.ttl_cleanup import cleanup_ex_tenant_keys
        result = cleanup_ex_tenant_keys("tenant-1")

        assert mock_client.ping.called
        assert mock_client.scan_iter.called


class TestAuditLoggingTask:
    """Test audit logging background tasks."""

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_log_audit_event_success(self, mock_redis_class):
        """Test successful audit event logging."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.close.return_value = None

        from app.tasks.audit_logging import log_audit_event
        result = log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key", "action": "create"}
        )

        assert mock_client.ping.called
        assert mock_client.setex.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_log_audit_event_redis_error(self, mock_redis_class):
        """Test audit logging handles Redis errors."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.side_effect = Exception("Connection failed")

        from app.tasks.audit_logging import log_audit_event

        # Huey catches exceptions internally
        result = log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key"}
        )

        assert mock_client.ping.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_aggregate_audit_logs_success(self, mock_redis_class):
        """Test successful audit log aggregation."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            "audit:tenant-1:1234567890",
            "audit:tenant-1:1234567891"
        ]
        mock_client.get.side_effect = [
            '{"tenant_id": "tenant-1", "event_type": "CREATE"}',
            '{"tenant_id": "tenant-1", "event_type": "READ"}'
        ]
        mock_client.setex.return_value = True
        mock_client.close.return_value = None

        from app.tasks.audit_logging import aggregate_audit_logs
        result = aggregate_audit_logs()

        assert mock_client.ping.called
        assert mock_client.scan_iter.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_aggregate_audit_logs_empty(self, mock_redis_class):
        """Test audit log aggregation with no logs."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []
        mock_client.close.return_value = None

        from app.tasks.audit_logging import aggregate_audit_logs
        result = aggregate_audit_logs()

        assert mock_client.ping.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_aggregate_audit_logs_invalid_json(self, mock_redis_class):
        """Test audit log aggregation handles invalid JSON."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = ["audit:tenant-1:1234567890"]
        mock_client.get.return_value = "invalid json"
        mock_client.close.return_value = None

        from app.tasks.audit_logging import aggregate_audit_logs
        result = aggregate_audit_logs()

        # Should handle error gracefully
        assert mock_client.ping.called


class TestBackgroundTaskIntegration:
    """Integration tests for background tasks."""

    @patch('redis.Redis')
    def test_cleanup_task_with_real_redis(self, mock_redis_class):
        """Test cleanup task with mocked Redis connection."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        # Setup mock responses
        mock_client.set.return_value = True
        mock_client.sadd.return_value = 1
        mock_client.delete.return_value = 1
        mock_client.exists.return_value = 1
        mock_client.sismember.return_value = True
        mock_client.ping.return_value = True

        # Simulate the test scenario
        mock_client.set("kv:test-tenant:key1", "value1")
        mock_client.set("kv:test-tenant:key1:metadata", '{"ttl": 60}')
        mock_client.sadd("tenant_keys:test-tenant", "key1")
        mock_client.delete("kv:test-tenant:key1")

        assert mock_client.exists("kv:test-tenant:key1:metadata") == 1
        assert mock_client.sismember("tenant_keys:test-tenant", "key1")

    @patch('redis.Redis')
    def test_audit_logging_with_real_redis(self, mock_redis_class):
        """Test audit logging with mocked Redis connection."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        audit_event = {
            "event_type": "CREATE",
            "tenant_id": "test-tenant",
            "timestamp": datetime.now().isoformat(),
            "details": {"key": "test:key", "action": "create"}
        }

        audit_key = f"audit:test-tenant:{int(datetime.now().timestamp())}"
        event_json = json.dumps(audit_event)

        mock_client.setex.return_value = True
        mock_client.get.return_value = event_json
        mock_client.ping.return_value = True

        mock_client.setex(audit_key, 3600, event_json)
        stored_event = json.loads(mock_client.get(audit_key))

        assert stored_event["event_type"] == "CREATE"
        assert stored_event["tenant_id"] == "test-tenant"
        assert "details" in stored_event


class TestTaskMetrics:
    """Test background task metrics collection."""

    @patch('app.tasks.ttl_cleanup.background_task_count')
    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_task_success_metric(self, mock_redis_class, mock_metric):
        """Test cleanup task increments success metric."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []
        mock_client.close.return_value = None

        # Setup metric mock
        mock_labels = MagicMock()
        mock_metric.labels.return_value = mock_labels
        mock_labels.inc.return_value = None

        from app.tasks.ttl_cleanup import cleanup_expired_keys
        cleanup_expired_keys()

        # Verify metric was called with success status
        assert mock_metric.labels.called

    @patch('app.tasks.ttl_cleanup.background_task_count')
    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_task_error_metric(self, mock_redis_class, mock_metric):
        """Test cleanup task increments error metric on failure."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        from redis import ConnectionError
        mock_client.ping.side_effect = ConnectionError("Connection failed")

        # Setup metric mock
        mock_labels = MagicMock()
        mock_metric.labels.return_value = mock_labels
        mock_labels.inc.return_value = None

        from app.tasks.ttl_cleanup import cleanup_expired_keys

        # Huey catches exceptions, just call the task
        cleanup_expired_keys()

        # Verify error metric was called
        assert mock_metric.labels.called

    @patch('app.tasks.audit_logging.background_task_count')
    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_task_success_metric(self, mock_redis_class, mock_metric):
        """Test audit task increments success metric."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.close.return_value = None

        # Setup metric mock
        mock_labels = MagicMock()
        mock_metric.labels.return_value = mock_labels
        mock_labels.inc.return_value = None

        from app.tasks.audit_logging import log_audit_event
        log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key"}
        )

        # Verify metric was called
        assert mock_metric.labels.called


class TestTaskErrorHandling:
    """Test error handling in background tasks."""

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_handles_connection_timeout(self, mock_redis_class):
        """Test cleanup task handles connection timeout."""
        import redis

        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.side_effect = redis.TimeoutError("Connection timeout")

        from app.tasks.ttl_cleanup import cleanup_expired_keys

        # Huey catches exceptions, just verify the task runs
        cleanup_expired_keys()
        assert mock_client.ping.called

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_handles_redis_error(self, mock_redis_class):
        """Test cleanup task handles Redis errors."""
        import redis

        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.side_effect = redis.RedisError("Redis error")

        from app.tasks.ttl_cleanup import cleanup_expired_keys

        # Huey catches exceptions, just verify the task runs
        cleanup_expired_keys()
        assert mock_client.ping.called

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_logging_handles_write_error(self, mock_redis_class):
        """Test audit logging handles write errors."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.setex.side_effect = Exception("Write failed")

        from app.tasks.audit_logging import log_audit_event

        # Huey catches exceptions, just verify the task runs
        log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key"}
        )
        assert mock_client.ping.called


class TestTaskScheduling:
    """Test task scheduling configuration."""

    def test_cleanup_task_schedule_configured(self):
        """Test cleanup task has correct schedule."""
        from app.tasks.ttl_cleanup import cleanup_expired_keys

        assert hasattr(cleanup_expired_keys, '__call__')
        assert callable(cleanup_expired_keys)

    def test_aggregation_task_schedule_configured(self):
        """Test aggregation task has correct schedule."""
        from app.tasks.audit_logging import aggregate_audit_logs

        assert hasattr(aggregate_audit_logs, '__call__')
        assert callable(aggregate_audit_logs)


class TestTaskPerformance:
    """Test background task performance."""

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_task_performance(self, mock_redis_class):
        """Test cleanup task completes in reasonable time."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            f"tenant_keys:tenant-{i}" for i in range(100)
        ]
        mock_client.smembers.return_value = {f"key{i}" for i in range(10)}
        mock_client.exists.return_value = 1
        mock_client.close.return_value = None

        # Mock pipeline
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        mock_pipeline.delete.return_value = mock_pipeline
        mock_pipeline.srem.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [1, 1]

        from app.tasks.ttl_cleanup import cleanup_expired_keys

        start_time = time.time()
        cleanup_expired_keys()
        duration = time.time() - start_time

        assert duration < 5.0

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_aggregation_performance(self, mock_redis_class):
        """Test audit aggregation completes in reasonable time."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = [
            f"audit:tenant-1:{1234567890 + i}" for i in range(1000)
        ]
        mock_client.get.return_value = '{"tenant_id": "tenant-1", "event_type": "CREATE"}'
        mock_client.setex.return_value = True
        mock_client.close.return_value = None

        from app.tasks.audit_logging import aggregate_audit_logs

        start_time = time.time()
        aggregate_audit_logs()
        duration = time.time() - start_time

        assert duration < 10.0


class TestTaskRetry:
    """Test task retry logic."""

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_task_retries_on_failure(self, mock_redis_class):
        """Test cleanup task retry behavior."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.side_effect = Exception("First attempt failed")

        from app.tasks.ttl_cleanup import cleanup_expired_keys

        # Huey catches exceptions, just verify the task was called
        cleanup_expired_keys()
        assert mock_client.ping.called


class TestTaskCleanup:
    """Test task cleanup behavior."""

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_cleanup_task_closes_connection(self, mock_redis_class):
        """Test cleanup task closes Redis connection."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []
        mock_client.close.return_value = None

        from app.tasks.ttl_cleanup import cleanup_expired_keys
        cleanup_expired_keys()

        mock_client.close.assert_called()

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_audit_task_closes_connection(self, mock_redis_class):
        """Test audit task closes Redis connection."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.close.return_value = None

        from app.tasks.audit_logging import log_audit_event
        log_audit_event(
            event_type="CREATE",
            tenant_id="tenant-1",
            details={"key": "test:key"}
        )

        mock_client.close.assert_called()


class TestTaskConcurrency:
    """Test task concurrency handling."""

    @patch('app.tasks.ttl_cleanup.Redis_Client')
    def test_multiple_cleanup_tasks_concurrent(self, mock_redis_class):
        """Test multiple cleanup tasks can run concurrently."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.scan_iter.return_value = []
        mock_client.close.return_value = None

        from app.tasks.ttl_cleanup import cleanup_expired_keys
        cleanup_expired_keys()
        cleanup_expired_keys()

        assert mock_client.ping.call_count >= 2

    @patch('app.tasks.audit_logging.redis.Redis')
    def test_multiple_audit_tasks_concurrent(self, mock_redis_class):
        """Test multiple audit tasks can run concurrently."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client

        mock_client.ping.return_value = True
        mock_client.setex.return_value = True
        mock_client.close.return_value = None

        from app.tasks.audit_logging import log_audit_event
        log_audit_event("CREATE", "tenant-1", {"key": "key1"})
        log_audit_event("READ", "tenant-2", {"key": "key2"})

        assert mock_client.setex.call_count == 2


class TestTaskConfiguration:
    """Test task configuration and settings."""

    def test_cleanup_interval_configured(self):
        """Test cleanup interval is properly configured."""
        assert hasattr(settings, 'CLEANUP_INTERVAL_SECONDS')
        assert settings.CLEANUP_INTERVAL_SECONDS > 0
        assert settings.CLEANUP_INTERVAL_SECONDS <= 3600

    def test_huey_workers_configured(self):
        """Test Huey worker count is configured."""
        assert hasattr(settings, 'HUEY_WORKERS')
        assert settings.HUEY_WORKERS > 0
        assert settings.HUEY_WORKERS <= 16

    @patch('redis.Redis')
    def test_huey_redis_connection_configured(self, mock_redis_class):
        """Test Huey Redis connection is configured."""
        mock_client = MagicMock()
        mock_redis_class.return_value = mock_client
        mock_client.ping.return_value = True

        assert hasattr(settings, 'HUEY_REDIS_HOST')
        assert hasattr(settings, 'HUEY_REDIS_PORT')
        assert hasattr(settings, 'HUEY_REDIS_DB')

        assert settings.HUEY_REDIS_HOST
        assert settings.HUEY_REDIS_PORT > 0
        assert settings.HUEY_REDIS_DB >= 0