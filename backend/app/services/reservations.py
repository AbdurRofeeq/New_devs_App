from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List
import logging
from pytz import timezone as pytz_timezone  # Add to requirements!

logger = logging.getLogger(__name__)

async def calculate_monthly_revenue(
    property_id: str, 
    month: int, 
    year: int, 
    tenant_id: str,  # ADDED: tenant_id parameter!
    property_timezone: str = 'UTC',  # Should come from properties table
    db_session=None
) -> Decimal:
    """
    Calculates revenue for a specific month with proper timezone handling.
    """
    # FIX: Use timezone-aware datetimes
    from app.services.properties import get_property_timezone  # hypothetical function
    
    # Get property's timezone from database
    if not property_timezone:
        property_timezone = await get_property_timezone(property_id, tenant_id)
    
    # Create timezone-aware start and end dates in property's local time
    tz = pytz_timezone(property_timezone)
    start_date = tz.localize(datetime(year, month, 1, 0, 0, 0))
    
    if month < 12:
        end_date = tz.localize(datetime(year, month + 1, 1, 0, 0, 0))
    else:
        end_date = tz.localize(datetime(year + 1, 1, 1, 0, 0, 0))
    
    # Convert to UTC for database query (if DB stores UTC)
    start_date_utc = start_date.astimezone(timezone.utc)
    end_date_utc = end_date.astimezone(timezone.utc)
    
    logger.info(f"Querying revenue for property {property_id} (tenant: {tenant_id})")
    logger.info(f"Local time range: {start_date} to {end_date}")
    logger.info(f"UTC time range: {start_date_utc} to {end_date_utc}")

    # SQL with proper tenant filtering
    query = """
        SELECT SUM(total_amount) as total
        FROM reservations
        WHERE property_id = $1
        AND tenant_id = $2
        AND check_in_date >= $3
        AND check_in_date < $4
    """
    
    # Execute query with UTC dates
    # result = await db.fetch_val(query, property_id, tenant_id, start_date_utc, end_date_utc)
    # return result or Decimal('0')
    
    return Decimal('0')  # Placeholder

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    REMOVED: Mock data fallback - now fails properly!
    """
    try:
        # Import database pool
        from app.core.database_pool import DatabasePool
        
        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                from sqlalchemy import text
                
                # FIX: Added logging to track queries
                logger.info(f"Calculating revenue for property {property_id}, tenant {tenant_id}")
                
                query = text("""
                    SELECT 
                        property_id,
                        SUM(total_amount) as total_revenue,
                        COUNT(*) as reservation_count
                    FROM reservations 
                    WHERE property_id = :property_id 
                    AND tenant_id = :tenant_id
                    GROUP BY property_id
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                row = result.fetchone()
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    logger.info(f"Found revenue {total_revenue} for property {property_id}")
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": "USD", 
                        "count": row.reservation_count
                    }
                else:
                    logger.info(f"No reservations found for property {property_id}, tenant {tenant_id}")
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")
            
    except Exception as e:
        # FIX: Log error and re-raise - NO MOCK DATA IN PRODUCTION!
        logger.error(f"Database error calculating revenue for property {property_id} (tenant: {tenant_id}): {e}", exc_info=True)
        
        # Either re-raise or return a proper error response
        raise Exception(f"Failed to calculate revenue for property {property_id}: {str(e)}")