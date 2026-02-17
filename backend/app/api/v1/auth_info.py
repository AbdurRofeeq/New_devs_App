from fastapi import APIRouter, Depends, HTTPException, status, Request
from ...core.auth import authenticate_request, auth_cache
from ...core.tenant_resolver import TenantResolver
from ...models.auth import AuthenticatedUser
from ...database import supabase
import logging
import hashlib

from typing import List, Dict, Any

import asyncio

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)

async def get_user_departments(user_id: str) -> List[Dict[str, Any]]:
    """Get user's department assignments with department details."""
    try:
        # Step 1: Get the department IDs for the user
        user_dept_result = (
            supabase.service.table("user_departments")
            .select("department_id")
            .eq("user_id", user_id)
            .execute()
        )
        if not user_dept_result.data:
            return []

        department_ids = [item['department_id'] for item in user_dept_result.data]
        if not department_ids:
            return []

        # Step 2: Get the details for those departments
        departments_result = (
            supabase.service.table("departments")
            .select("*")
            .in_("id", department_ids)
            .execute()
        )
        
        return departments_result.data or []
    except Exception as e:
        logger.error(f"Error fetching user departments for user {user_id}: {e}")
        return []


@router.get("/me")
async def get_current_user_info(
    request: Request,
    user: AuthenticatedUser = Depends(authenticate_request)
):
    """Return current user's identity, permissions, cities, and tenant context.

    This endpoint consolidates data needed by the frontend to avoid any direct
    database queries from the browser for auth-related information.
    
    If 'refresh' query parameter is present, clears the auth cache for this user.
    """
    
    # Check if refresh is requested
    if request.query_params.get('refresh') == 'true':
        # Clear cache for this user's token
        auth_header = request.headers.get('authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]
            token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
            if token_hash in auth_cache:
                logger.info(f"AUTH /me: Clearing cache for user {user.email} on refresh request")
                del auth_cache[token_hash]
    try:
        # In parallel, fetch metadata and department assignments
        async def fetch_metadata():
            try:
                admin_resp = supabase.auth.admin.get_user_by_id(user.id)
                if getattr(admin_resp, "user", None):
                    u = admin_resp.user
                    return getattr(u, "user_metadata", None) or None, getattr(u, "app_metadata", None) or None
            except Exception as meta_err:
                logger.warning(f"AUTH /me: failed to load metadata for {user.id}: {meta_err}")
            return None, None

        metadata_task = asyncio.create_task(fetch_metadata())
        departments_task = asyncio.create_task(get_user_departments(user.id))

        (user_metadata, app_metadata) = await metadata_task
        departments = await departments_task

        # Get base permissions
        permissions = [
            {"section": p.section, "action": p.action} for p in (user.permissions or [])
        ]
        
        # This ensures /auth/me returns correct tenant like other endpoints
        tenant_id = await TenantResolver.resolve_tenant_id(user_id=user.id, user_email=user.email)

        # TO:
        # Get token payload from request
        token_payload = getattr(request.state, "token_payload", None)
        tenant_id = await TenantResolver.resolve_tenant_id(
            user_id=user.id, 
            user_email=user.email,
            token_payload=token_payload
        )
        logger.info(f"AUTH /me: Fresh tenant lookup for {user.email}: {tenant_id}")
        
      if tenant_id and not user.is_admin:
        try:
        # Get user's assigned smart views from a junction table
        user_smart_views_result = (
            supabase
            .table('user_smart_views')  # Assuming this table exists
            .select('smart_view_id')
            .eq('user_id', user.id)
            .eq('tenant_id', tenant_id)
            .execute()
        )
        
        assigned_view_ids = [item['smart_view_id'] for item in user_smart_views_result.data]
        
        if assigned_view_ids:
            # Get details for only the assigned smart views
            smart_views_result = (
                supabase
                .table('reservation_subsections')
                .select('id, name')
                .in_('id', assigned_view_ids)
                .eq('is_active', True)
                .execute()
            )
            
            for view in smart_views_result.data or []:
                permissions.append({
                    "section": f"smart_view_{view['id']}",
                    "action": "read"
                })
    except Exception as e:
        logger.error(f"Failed to fetch user's assigned smart views: {e}")

        return {
            "id": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "tenant_id": tenant_id,
            "permissions": permissions,
            "cities": list(user.cities or []),
            "departments": departments,
            "user_metadata": user_metadata,
            "app_metadata": app_metadata,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AUTH /me failed: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load user info")


@router.get("/departments/{user_id}")
async def get_user_departments_endpoint(
    user_id: str,
    user: AuthenticatedUser = Depends(authenticate_request)
):
    """Get departments for a specific user"""
    try:
        departments = await get_user_departments(user_id)
        # Return just the department IDs for simplicity
        return {"department_ids": [dept["id"] for dept in departments]}
    except Exception as e:
        logger.error(f"Failed to get departments for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user departments"
        )
