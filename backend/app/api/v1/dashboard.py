from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from decimal import Decimal
from app.services.cache import get_revenue_summary
from app.core.auth import authenticate_request as get_current_user
from app.database import supabase
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dashboard/summary")
async def get_dashboard_summary(
    property_id: str,
    current_user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    
    # Get the user's tenant_id
    tenant_id = getattr(current_user, "tenant_id", None)
    if not tenant_id:
        logger.error(f"User {getattr(current_user, 'email', 'unknown')} has no tenant_id")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not associated with a tenant"
        )
    
    #Verify the property belongs to this tenant!
    try:
        property_check = (
            supabase.table("properties")
            .select("id")
            .eq("id", property_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        
        if not property_check.data:
            logger.warning(f"Property {property_id} not found for tenant {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Property not found or access denied"
            )
    except Exception as e:
        logger.error(f"Error validating property access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating property access"
        )
    
    # Get revenue data (should return Decimal objects)
    revenue_data = await get_revenue_summary(property_id, tenant_id)
    
    # FIX: Return Decimal as string to preserve precision
    # JSON doesn't support Decimal, so we convert to string
    total_revenue = revenue_data['total']
    if isinstance(total_revenue, Decimal):
        # Format as string with 2 decimal places
        total_revenue_str = f"{total_revenue:.2f}"
    else:
        # If it's already a number, convert properly
        total_revenue_str = f"{Decimal(str(total_revenue)):.2f}"
    
    return {
        "property_id": revenue_data['property_id'],
        "total_revenue": total_revenue_str,  # Return as string to preserve precision
        "total_revenue_float": float(total_revenue),  # Optional: keep float for charts
        "currency": revenue_data['currency'],
        "reservations_count": revenue_data['count']
    }