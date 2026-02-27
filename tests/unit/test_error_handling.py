"""Negative test cases for Pikar AI services.

This module contains tests for error paths, database failures,
rate limits, and invalid inputs.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from types import SimpleNamespace
from supabase import Client
from slowapi.errors import RateLimitExceeded

from app.exceptions import (
    PikarError,
    ValidationError,
    DatabaseError,
    CacheError,
    NotFoundError,
    ErrorCode,
)
from app.services.cache import CacheService, CacheResult
from app.services.crud_base import CRUDService


class TestCacheErrorHandling:
    """Test cache error vs cache miss distinction."""
    
    @pytest.mark.asyncio
    async def test_cache_miss_returns_miss_result(self):
        """Cache miss should return CacheResult with is_miss=True."""
        service = CacheService()
        service._redis = Mock()
        service._connected = True
        
        # Mock get returning None (cache miss)
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        service._redis = mock_redis
        
        result = await service.get_user_config("test_user")
        
        assert isinstance(result, CacheResult)
        assert result.is_miss is True
        assert result.found is False
        assert result.error is None
    
    @pytest.mark.asyncio
    async def test_cache_error_returns_error_result(self):
        """Redis connection error should return CacheResult with is_error=True."""
        from redis.exceptions import ConnectionError as RedisConnectionError
        
        service = CacheService()
        service._redis = None
        service._connected = False
        
        # Mock _ensure_connection returning None (connection failed)
        with patch.object(service, '_ensure_connection', return_value=None):
            result = await service.get_user_config("test_user")
            
            assert isinstance(result, CacheResult)
            assert result.is_error is True
            assert result.error is not None


class TestValidationErrorHandling:
    """Test input validation error handling."""
    
    def test_validation_error_with_code(self):
        """ValidationError should use the validation error code."""
        error = ValidationError(message="Invalid input")

        assert error.message == "Invalid input"
        assert error.code == ErrorCode.VALIDATION_ERROR
    
    def test_validation_error_http_status(self):
        """ValidationError should map to 400 status."""
        error = ValidationError(message="test")

        assert error.status_code == 400
    
    def test_not_found_error_http_status(self):
        """NotFoundError should map to 404 status."""
        error = NotFoundError(resource="Widget", resource_id="123")

        assert error.status_code == 404


class TestDatabaseErrorHandling:
    """Test database error handling."""
    
    def test_database_error_with_details(self):
        """DatabaseError should include details."""
        error = DatabaseError(
            message="Database operation failed",
            details={"table": "users", "operation": "insert"}
        )

        assert error.message == "Database operation failed"
        assert error.details["table"] == "users"
    
    def test_database_error_http_status(self):
        """DatabaseError should map to 500 status."""
        error = DatabaseError(message="DB error")

        assert error.status_code == 500


class TestCRUDServiceErrors:
    """Test CRUD service error handling."""
    
    def test_create_failure_returns_none(self):
        """CRUD create should return None on error."""
        mock_client = Mock(spec=Client)
        mock_client.table.return_value.insert.return_value.execute.side_effect = Exception("DB error")
        
        service = CRUDService(mock_client, "test_table")
        result = service.create({"name": "test"})
        
        assert result is None
    
    def test_get_by_id_not_found(self):
        """CRUD get_by_id should return None when not found."""
        mock_client = Mock(spec=Client)
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = Mock(data=[])
        
        service = CRUDService(mock_client, "test_table")
        result = service.get_by_id("nonexistent-id")
        
        assert result is None
    
    def test_delete_failure_returns_false(self):
        """CRUD delete should return False on error."""
        mock_client = Mock(spec=Client)
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.side_effect = Exception("DB error")
        
        service = CRUDService(mock_client, "test_table")
        result = service.delete("some-id")
        
        assert result is False
    
    def test_count_returns_zero_on_error(self):
        """CRUD count should return 0 on error."""
        mock_client = Mock(spec=Client)
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        
        service = CRUDService(mock_client, "test_table")
        result = service.count({"status": "active"})
        
        assert result == 0
    
    def test_exists_returns_false_on_error(self):
        """CRUD exists should return False on error."""
        mock_client = Mock(spec=Client)
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("DB error")
        
        service = CRUDService(mock_client, "test_table")
        result = service.exists("email", "test@example.com")
        
        assert result is False


class TestRateLimitHandling:
    """Test rate limiting error handling."""
    
    def test_rate_limit_exception(self):
        """Rate limit exceeded should have proper HTTP status."""
        limit = SimpleNamespace(error_message="Rate limit exceeded", limit="10/minute")
        error = RateLimitExceeded(limit)

        assert error.status_code == 429


class TestInputValidation:
    """Test input validation."""
    
    def test_empty_user_id_validation(self):
        """Empty user ID should raise ValidationError."""
        from app.agents.tools.validation import UserIdInput
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            UserIdInput(user_id="")
    
    def test_sql_injection_prevention(self):
        """SQL injection attempts should be rejected."""
        from app.agents.tools.validation import validate_sql_safe
        
        # These should be blocked
        assert validate_sql_safe("'; DROP TABLE users;--") is False
        assert validate_sql_safe("1; DELETE FROM users") is False
        assert validate_sql_safe("UNION SELECT * FROM passwords") is False
        
        # These should be allowed
        assert validate_sql_safe("John O'Connor") is True
        assert validate_sql_safe("Test user name") is True
    
    def test_xss_prevention(self):
        """XSS attempts should be sanitized."""
        from app.agents.tools.validation import sanitize_html
        
        # Script tags should be removed
        result = sanitize_html("<script>alert('xss')</script>Hello")
        assert "<script>" not in result
        
        # Event handlers should be removed
        result = sanitize_html("<img onclick='alert(1)'>")
        assert "onclick" not in result
    
    def test_uuid_validation(self):
        """Invalid UUIDs should be rejected."""
        from app.agents.tools.validation import UUIDInput
        from pydantic import ValidationError as PydanticValidationError
        
        # Invalid UUIDs
        with pytest.raises(PydanticValidationError):
            UUIDInput(id="not-a-uuid")
        
        with pytest.raises(PydanticValidationError):
            UUIDInput(id="123")
        
        # Valid UUID
        result = UUIDInput(id="550e8400-e29b-41d4-a716-446655440000")
        assert result.id == "550e8400-e29b-41d4-a716-446655440000"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
