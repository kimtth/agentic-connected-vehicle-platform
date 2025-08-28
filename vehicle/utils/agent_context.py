from typing import Optional, Any

def extract_vehicle_id(context: Optional[Any], vehicle_id: Optional[str] = None) -> Optional[str]:
    """
    Return vehicle_id if provided, otherwise try to read it from Semantic Kernel current context.
    """
    if vehicle_id:
        return vehicle_id
    
    try:
        current_context = context.get_current()
        if current_context and hasattr(current_context, "arguments"):
            return current_context.arguments.get("vehicleId")
    except Exception:
        pass
    return None
