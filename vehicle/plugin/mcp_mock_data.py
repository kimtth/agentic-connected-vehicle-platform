from typing import Dict, Any, List
from datetime import datetime, timezone


def generate_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    condition = (
        "Sunny"
        if (latitude + longitude) % 3 == 0
        else "Cloudy" if (latitude + longitude) % 3 == 1 else "Partly Cloudy"
    )
    temperature = int(((latitude + 90) / 180) * 30 + 5)  # 5-35°C
    return {
        "location": {"latitude": latitude, "longitude": longitude},
        "current": {
            "temperature": temperature,
            "condition": condition,
            "humidity": 65,
            "wind_speed": 12,
        },
        "forecast": [
            {
                "day": "Today",
                "condition": condition,
                "high": temperature,
                "low": temperature - 5,
            },
            {
                "day": "Tomorrow",
                "condition": "Partly Cloudy",
                "high": temperature + 2,
                "low": temperature - 3,
            },
            {
                "day": "Day After",
                "condition": "Sunny",
                "high": temperature + 1,
                "low": temperature - 4,
            },
        ],
    }


def generate_forecast(
    latitude: float, longitude: float, days: int = 3
) -> List[Dict[str, Any]]:
    base = generate_weather(latitude, longitude)
    return base["forecast"][: max(1, min(10, days))]


def generate_traffic(route: str, latitude: float, longitude: float) -> Dict[str, Any]:
    level = (
        "Heavy"
        if len(route) % 3 == 0
        else "Moderate" if len(route) % 3 == 1 else "Light"
    )
    incidents = (
        [{"type": "Accident", "location": f"{round(latitude,2)},{round(longitude,2)}"}]
        if level == "Heavy"
        else []
    )
    return {
        "route": route,
        "level": level,
        "incidents": incidents,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def generate_pois(category: str, latitude: float, longitude: float) -> Dict[str, Any]:
    sample = [
        {"name": f"{category.title()} Spot A", "distance_km": 1.2},
        {"name": f"{category.title()} Spot B", "distance_km": 2.5},
        {"name": f"{category.title()} Spot C", "distance_km": 3.1},
    ]
    return {
        "category": category,
        "location": {"lat": latitude, "lon": longitude},
        "results": sample,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def generate_directions(
    destination: str, latitude: float, longitude: float
) -> Dict[str, Any]:
    steps = [
        f"Head north for 1 km from ({latitude:.4f},{longitude:.4f})",
        "Turn right at the next intersection",
        f"Continue straight for 2 km towards {destination}",
        f"Arrive at {destination}",
    ]
    return {
        "destination": destination,
        "start": {"lat": latitude, "lon": longitude},
        "steps": steps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
