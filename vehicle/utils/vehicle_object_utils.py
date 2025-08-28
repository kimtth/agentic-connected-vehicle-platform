from typing import Any, Dict, Iterable, Optional

def ensure_dict(obj: Any) -> Dict[str, Any]:
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(by_alias=True)
        except Exception:
            pass
    # Fallback: only expose known fields we reference
    result = {}
    for k in (
        "vehicle_id", "vehicleId", "BatteryLevel", "Features", "LastLocation",
        "Brand", "VehicleModel", "Year", "CurrentTelemetry"
    ):
        if hasattr(obj, k):
            result[k] = getattr(obj, k)
    return result

def find_vehicle(vehicles: Iterable[Any], vid: str) -> Optional[Any]:
    if not vid:
        return None
    for v in vehicles:
        if getattr(v, "vehicle_id", None) == vid:
            return v
        if isinstance(v, dict) and v.get("vehicle_id") == vid:
            return v
        if hasattr(v, "model_dump"):
            try:
                d = v.model_dump(by_alias=True)
                if d.get("vehicleId") == vid or d.get("vehicle_id") == vid:
                    return v
            except Exception:
                continue
    return None

def extract_location(vehicle_status: Any, vehicle: Any) -> Optional[Dict[str, Any]]:
    vs = ensure_dict(vehicle_status)
    v = ensure_dict(vehicle)
    if "location" in vs:
        return vs["location"]
    last_loc = v.get("LastLocation") or v.get("lastLocation")
    if isinstance(last_loc, dict):
        return {
            "latitude": last_loc.get("Latitude") or last_loc.get("latitude", 0),
            "longitude": last_loc.get("Longitude") or last_loc.get("longitude", 0),
        }
    return None

def notification_to_dict(n: Any) -> Dict[str, Any]:
    return ensure_dict(n)
