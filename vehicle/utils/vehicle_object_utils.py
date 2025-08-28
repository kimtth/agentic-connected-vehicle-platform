from typing import Any, Dict, Iterable, Optional

# Mapping of possible source attribute names to unified camelCase output keys
_CAMEL_FIELD_MAP = {
    "vehicle_id": "vehicleId",
    "vehicleId": "vehicleId",
    "BatteryLevel": "batteryLevel",
    "Features": "features",
    "LastLocation": "lastLocation",
    "Brand": "brand",
    "VehicleModel": "vehicleModel",
    "Year": "year",
    "CurrentTelemetry": "currentTelemetry",
    "StartDate": "startDate",
    "ServiceCode": "serviceCode",
}

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
    # Fallback: expose only known fields, normalized to camelCase
    result: Dict[str, Any] = {}
    for original, camel in _CAMEL_FIELD_MAP.items():
        if hasattr(obj, original) and camel not in result:
            result[camel] = getattr(obj, original)
    return result

def find_vehicle(vehicles: Iterable[Any], vid: str) -> Optional[Any]:
    if not vid:
        return None
    for v in vehicles:
        if getattr(v, "vehicleId", None) == vid:
            return v
        if isinstance(v, dict) and v.get("vehicleId") == vid:
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
