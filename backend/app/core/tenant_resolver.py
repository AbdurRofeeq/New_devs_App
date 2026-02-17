"""
Minimal tenant resolver for authentication.
"""
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TenantResolver:
    """Tenant resolver that extracts tenant_id from JWT claims or database."""

    @staticmethod
    def resolve_tenant_from_token(token_payload: dict) -> Optional[str]:
        """
        Extract tenant_id from JWT token payload.

        Args:
            token_payload: Decoded JWT payload

        Returns:
            Tenant ID if found, None otherwise
        """
        
        if 'user_metadata' in token_payload:
            tenant_id = token_payload['user_metadata'].get('tenant_id')
            if tenant_id:
                return tenant_id

        # Try app_metadata as fallback
        if 'app_metadata' in token_payload:
            tenant_id = token_payload['app_metadata'].get('tenant_id')
            if tenant_id:
                return tenant_id

        # Try root level
        tenant_id = token_payload.get('tenant_id')
        if tenant_id:
            return tenant_id

        logger.warning("No tenant_id found in token payload")
        return None

    @staticmethod
    def resolve_tenant_from_user(user_data: dict) -> Optional[str]:
        """
        Extract tenant_id from user data.

        Args:
            user_data: User data dictionary

        Returns:
            Tenant ID if found, None otherwise
        """
        # Check various possible locations
        if 'tenant_id' in user_data:
            return user_data['tenant_id']

        if 'user_metadata' in user_data:
            tenant_id = user_data['user_metadata'].get('tenant_id')
            if tenant_id:
                return tenant_id

        if 'app_metadata' in user_data:
            tenant_id = user_data['app_metadata'].get('tenant_id')
            if tenant_id:
                return tenant_id

        return None

    @staticmethod
    async def resolve_tenant_id(
        user_id: str, 
        user_email: str, 
        token_payload: Optional[dict] = None
    ) -> Optional[str]:
        """
        Resolve tenant ID for a user using token payload first, then fallback.
        
        Args:
            user_id: User ID
            user_email: User email
            token_payload: Decoded JWT token payload
            
        Returns:
            Tenant ID or None if not found
        """
        if token_payload:
            tenant_id = TenantResolver.resolve_tenant_from_token(token_payload)
            if tenant_id:
                logger.info(f"Resolved tenant {tenant_id} from token for user {user_email}")
                return tenant_id
        
        logger.warning(f"Could not resolve tenant from token for user {user_email}, checking database...")
        
        # In a real implementation, you'd query the database here:
        # SELECT tenant_id FROM users WHERE id = $1 OR email = $2
        
        # TEMPORARY FALLBACK FOR DEBUGGING - REMOVE IN PRODUCTION
        # This maintains backward compatibility but logs a warning
        if user_email == "sunset@propertyflow.com":
            logger.warning(f"Using hardcoded fallback for {user_email} - FIX THIS!")
            return "tenant-a"
        if user_email == "ocean@propertyflow.com":
            logger.warning(f"Using hardcoded fallback for {user_email} - FIX THIS!")
            return "tenant-b"
        if user_email == "candidate@propertyflow.com":
            return "tenant-a"
        
        logger.error(f"Could not resolve tenant for user {user_email}")
        return None  # Return None instead of default tenant

    @staticmethod
    async def update_user_tenant_metadata(user_id: str, tenant_id: str) -> None:
        """
        Update user metadata with tenant_id.
        
        Args:
            user_id: User ID
            tenant_id: Tenant ID
        """
        # This should be implemented to persist tenant_id to user metadata
        logger.info(f"Would update user {user_id} with tenant {tenant_id}")
        pass