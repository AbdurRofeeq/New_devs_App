import json
import redis.asyncio as redis
from typing import Dict, Any, Optional
import os
import logging
from decimal import Decimal

# Initialize Redis client (typically configured centrally).
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
logger = logging.getLogger(__name__)

class DecimalEncoder(json.JSONEncoder):
    """Custom JSON encoder for Decimal objects."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)  # Convert Decimal to string to preserve precision
        return super().default(obj)

async def get_revenue_summary(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Fetches revenue summary, utilizing caching to improve performance.
    
    IMPORTANT: Cache keys include BOTH property_id AND tenant_id to prevent
    cross-tenant data leakage!
    """
    # Include tenant_id in cache key to prevent cross-tenant cache poisoning
    cache_key = f"revenue:{tenant_id}:{property_id}"
    
    try:
        # Try to get from cache
        cached = await redis_client.get(cache_key)
        if cached:
            logger.debug(f"Cache hit for {cache_key}")
            return json.loads(cached)
        
        logger.debug(f"Cache miss for {cache_key}")
        
        # Revenue calculation is delegated to the reservation service.
        from app.services.reservations import calculate_total_revenue
        
        # Calculate revenue
        result = await calculate_total_revenue(property_id, tenant_id)
        
        # FIX: Ensure result has proper format and handle Decimal objects
        if 'total' in result and isinstance(result['total'], Decimal):
            # Convert Decimal to string for JSON serialization
            result['total'] = str(result['total'])
        
        # Cache the result for 5 minutes
        await redis_client.setex(
            cache_key, 
            300, 
            json.dumps(result, cls=DecimalEncoder)  # Use custom encoder
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_revenue_summary for property {property_id}, tenant {tenant_id}: {e}")
        # Fall back to direct calculation without caching
        from app.services.reservations import calculate_total_revenue
        return await calculate_total_revenue(property_id, tenant_id)


async def invalidate_revenue_cache(property_id: str, tenant_id: str) -> None:
    """
    Invalidate cache for a specific property when data changes.
    """
    cache_key = f"revenue:{tenant_id}:{property_id}"
    try:
        await redis_client.delete(cache_key)
        logger.info(f"Invalidated cache for {cache_key}")
    except Exception as e:
        logger.error(f"Error invalidating cache for {cache_key}: {e}")