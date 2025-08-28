from typing import Optional

def extract_vehicle_id(vehicle_id: Optional[str] = None) -> Optional[str]:
    """
    Return vehicle_id if provided, otherwise try to read it from Semantic Kernel current context.
    Supports both 'vehicle_id' and 'vehicleId' keys.
    """
    if vehicle_id:
        return vehicle_id
    try:
        from semantic_kernel.kernel import Kernel
        kernel = Kernel.get_current()
        if kernel and hasattr(kernel, "arguments"):
            return kernel.arguments.get("vehicleId")
    except Exception:
        pass
    return None
