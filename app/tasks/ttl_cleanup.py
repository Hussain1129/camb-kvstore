from app.config import settings
from app.tasks import huey
from redis import Redis as Redis_Client, ConnectionError
from app.utils.logger import get_logger
from huey import crontab

logger = get_logger(__name__)


@huey.periodic_task(crontab(minute=f'*/{settings.CLEANUP_INTERVAL_SECONDS // 60}'))
def cleanup_expired_keys():
    """
    Periodic task to clean-up expired keys and their metadata.
    Runs every CLEANUP_INTERVAL_SECONDS to ensure consistency.
    """
    try:
        logger.info("Starting the TTL cleanup task to clean the expired keys")

        redis_client = Redis_Client(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        redis_client.ping()

        cleaned_count = 0
        sets_of_tenants = []

        for key in redis_client.scan_iter(match="tenant_keys:*"):
            sets_of_tenants.append(key)

        for tenant_set_key in sets_of_tenants:
            tenant_id = tenant_set_key.split(":", 1)[1]

            keys_to_check = list(redis_client.smembers(tenant_set_key))

            for key in keys_to_check:
                kv_key = f"kv:{tenant_id}:{key}"
                metadata_key = f"kv:{tenant_id}:{key}:metadata"

                if not redis_client.exists(kv_key):
                    pipeline = redis_client.pipeline()
                    pipeline.delete(metadata_key)
                    pipeline.srem(tenant_set_key, key)
                    pipeline.execute()

                    cleaned_count += 1
                    logger.debug(f"Cleaned up expired key: {key} for tenant: {tenant_id}")

        logger.info(f"TTL cleanup task completed. Cleaned {cleaned_count} expired keys")


        redis_client.close()

        return cleaned_count

    except ConnectionError as e:
        logger.error(f"Redis connection error in TTL cleanup: {str(e)}")
        raise ConnectionError(f"Redis connection error in TTL cleanup: {str(e)}")
    except Exception as e:
        logger.error(f"Error in TTL cleanup task: {str(e)}")
        raise Exception(f"Error in TTL cleanup task: {str(e)}")


@huey.task()
def cleanup_ex_tenant_keys(tenant_id: str):
    """
    Task to clean up all keys for a specific tenant.
    This will be called when a tenant is deleted.
    """
    try:
        logger.info(f"Starting cleanup for tenant: {tenant_id}")

        redis_client = Redis_Client(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True
        )

        redis_client.ping()

        cleaned_count = 0

        kv_pattern = f"kv:{tenant_id}:*"
        for key in redis_client.scan_iter(match=kv_pattern):
            redis_client.delete(key)
            cleaned_count += 1

        tenant_set_key = f"tenant_keys:{tenant_id}"
        redis_client.delete(tenant_set_key)

        logger.info(f"Cleanup completed for tenant {tenant_id}. Deleted {cleaned_count} keys")


        redis_client.close()

        return cleaned_count

    except Exception as e:
        logger.error(f"Error in tenant cleanup task for {tenant_id}: {str(e)}")
        raise Exception(f"Error in tenant cleanup task for {tenant_id}: {str(e)}")