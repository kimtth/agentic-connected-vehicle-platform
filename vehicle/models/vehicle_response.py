from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class VehicleResponseFormat(BaseModel):
    """
    Structured response format for vehicle agent interactions.
    Ensures consistent API responses with proper JSON schema constraints.
    """
    
    message: str = Field(
        ..., 
        description="The main response message to the user"
    )
    
    status: str = Field(
        default="completed",
        description="Status of the request (completed, error, processing)",
        pattern="^(completed|error|processing)$"
    )
    
    plugins_used: Optional[List[str]] = Field(
        default=None,
        description="List of plugins/agents that were used to process the request"
    )
    
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional structured data related to the response"
    )
    
    timestamp: Optional[str] = Field(
        default=None,
        description="Timestamp of the response"
    )
    
    @classmethod
    def model_json_schema(cls, by_alias: bool = True, ref_template: str = '#/$defs/{model}') -> Dict[str, Any]:
        """Generate JSON schema with proper type definitions for OpenAI compatibility."""
        schema = super().model_json_schema(by_alias=by_alias, ref_template=ref_template)
        
        # Ensure proper type definitions for all properties
        if 'properties' in schema:
            if 'data' in schema['properties']:
                schema['properties']['data'] = {
                    "type": "object",
                    "additionalProperties": False,
                    "description": "Additional structured data related to the response"
                }
            
            if 'plugins_used' in schema['properties']:
                schema['properties']['plugins_used'] = {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of plugins/agents that were used to process the request"
                }
                
            if 'message' in schema['properties']:
                schema['properties']['message'] = {
                    "type": "string",
                    "description": "The main response message to the user"
                }
                
            if 'status' in schema['properties']:
                schema['properties']['status'] = {
                    "type": "string",
                    "pattern": "^(completed|error|processing)$",
                    "description": "Status of the request (completed, error, processing)"
                }
                
            if 'timestamp' in schema['properties']:
                schema['properties']['timestamp'] = {
                    "type": "string",
                    "description": "Timestamp of the response"
                }
        
        # Ensure additionalProperties is false at the root level
        schema['additionalProperties'] = False
        
        return schema
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "additionalProperties": False,
            "required": ["message"],
            "type": "object"
        }