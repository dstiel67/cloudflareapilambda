"""
Tests for the main Lambda function handler.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock

# Add the parent directory to the path to import lambda_function
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the lambda_function module directly
import importlib.util
spec = importlib.util.spec_from_file_location("lambda_function", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lambda_function.py"))
lambda_function_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lambda_function_module)


class TestLambdaHandler:
    """Test cases for the main lambda_handler function."""
    
    def test_lambda_handler_basic_structure(self):
        """Test that lambda_handler returns expected structure."""
        # Arrange
        event = {}
        context = Mock()
        
        # Act
        result = lambda_function_module.lambda_handler(event, context)
        
        # Assert
        assert isinstance(result, dict)
        assert "success" in result
        assert "statistics" in result
        assert "execution_time_ms" in result["statistics"]
    
    def test_lambda_handler_includes_required_statistics(self):
        """Test that response includes all required statistics fields."""
        # Arrange
        event = {}
        context = Mock()
        
        # Act
        result = lambda_function_module.lambda_handler(event, context)
        
        # Assert
        stats = result["statistics"]
        required_fields = [
            "records_processed",
            "records_stored", 
            "execution_time_ms",
            "cloudflare_api_calls",
            "dynamodb_writes"
        ]
        
        for field in required_fields:
            assert field in stats, f"Missing required field: {field}"