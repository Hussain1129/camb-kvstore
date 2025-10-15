from prometheus_client import Counter, Histogram, Gauge
from functools import wraps
from time import time
from typing import Callable
import asyncio

request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

active_connections = Gauge(
    'active_connections',
    'Number of active connections'
)

kvstore_operations = Counter(
    'kvstore_operations_total',
    'Total KV store operations',
    ['operation', 'tenant_id', 'status']
)

kvstore_operation_duration = Histogram(
    'kvstore_operation_duration_seconds',
    'KV store operation duration in seconds',
    ['operation']
)

redis_connection_errors = Counter(
    'redis_connection_errors_total',
    'Total Redis connection errors'
)

background_task_count = Counter(
    'background_tasks_total',
    'Total background tasks executed',
    ['task_name', 'status']
)

background_task_duration = Histogram(
    'background_task_duration_seconds',
    'Background task duration in seconds',
    ['task_name']
)


def track_time(metric: Histogram, labels: dict = None):
    """Decorator to track execution time."""

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator