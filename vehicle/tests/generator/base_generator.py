"""
Base generator interface and common constants for data generation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
import uuid
from datetime import datetime, timezone


class BaseGenerator(ABC):
    """Base interface for all data generators"""
    
    @abstractmethod
    def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate a single data entity"""
        pass
    
    def generate_batch(self, count: int, **kwargs) -> List[Dict[str, Any]]:
        """Generate multiple data entities"""
        return [self.generate(**kwargs) for _ in range(count)]
    
    @staticmethod
    def generate_id() -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def get_current_timestamp() -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()


# Common constants that can be used across generators
COMMON_REGIONS = ["North America", "Europe", "Asia", "South America", "Australia"]
COMMON_PRIORITIES = ["Low", "Normal", "High"]
COMMON_DEVICE_TYPES = ["Mobile App", "Web Portal", "In-car System", "Voice Assistant"]
