"""Utilities for handling response format validation and fallback mechanisms."""

import json
from typing import Dict, Any, Optional
from models.vehicle_response import VehicleResponseFormat
from utils.logging_config import get_logger

logger = get_logger(__name__)


def validate_response_format_schema() -> Optional[Dict[str, Any]]:
    """
    Validate that the VehicleResponseFormat schema is compatible with OpenAI.
    
    Returns:
        The validated schema dict, or None if validation fails.
    """
    try:
        schema = VehicleResponseFormat.model_json_schema()
        
        # Check required fields for OpenAI compatibility
        required_checks = [
            ('type' in schema, "Root schema must have 'type' field"),
            ('properties' in schema, "Schema must have 'properties' field"),
            ('additionalProperties' in schema, "Schema must have 'additionalProperties' field"),
        ]
        
        for check, error_msg in required_checks:
            if not check:
                logger.error(f"Schema validation failed: {error_msg}")
                return None
        
        # Validate each property has proper type definition
        for prop_name, prop_schema in schema.get('properties', {}).items():
            if 'type' not in prop_schema:
                logger.error(f"Property '{prop_name}' missing 'type' field")
                return None
        
        logger.debug("Response format schema validation passed")
        return schema
        
    except Exception as e:
        logger.error(f"Error validating response format schema: {e}")
        return None


def parse_fallback_response(response_content: str) -> Dict[str, Any]:
    """
    Parse a response that may or may not be in JSON format.
    
    Args:
        response_content: The raw response content
        
    Returns:
        A standardized response dictionary
    """
    # Try to parse as JSON first
    try:
        if response_content.strip().startswith('{') and response_content.strip().endswith('}'):
            parsed_json = json.loads(response_content)
            if isinstance(parsed_json, dict):
                return {
                    "response": parsed_json.get("message", response_content),
                    "success": True,
                    "plugins_used": parsed_json.get("plugins_used", []),
                    "data": parsed_json.get("data"),
                    "fallback_used": True
                }
    except json.JSONDecodeError:
        logger.debug("Response content is not valid JSON, treating as plain text")
    
    # Return as plain text response
    return {
        "response": response_content,
        "success": True,
        "plugins_used": [],
        "fallback_used": True
    }


def create_error_response(error_message: str, error_details: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        error_message: User-friendly error message
        error_details: Technical error details (optional)
        
    Returns:
        A standardized error response dictionary
    """
    response = {
        "response": error_message,
        "success": False,
        "plugins_used": [],
    }
    
    if error_details:
        response["error"] = error_details
    
    return response
