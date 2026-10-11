from dataclasses import dataclass
from typing import List

@dataclass
class City:
    name: str
    state: str  
    lat: float
    lon: float

CITIES: List[City] = [
    City('Delhi NCR', 'Delhi', 28.6139, 77.2090),
    City('Mumbai', 'Maharashtra', 19.0760, 72.8777),
    City('Chennai', 'Tamil Nadu', 13.0827, 80.2707),
    City('Kolkata', 'West Bengal', 22.5726, 88.3639),
    City('Bengaluru', 'Karnataka', 12.9716, 77.5946),
    City('Hyderabad', 'Telangana', 17.3850, 78.4867),
    City('Ahmedabad', 'Gujarat', 23.0225, 72.5714),
    City('Pune', 'Maharashtra', 18.5204, 73.8567),
    City('Jaipur', 'Rajasthan', 26.9124, 75.7873),
    City('Lucknow', 'Uttar Pradesh', 26.8467, 80.9462),
    City('Nagpur', 'Maharashtra', 21.1458, 79.0882),
    City('Bhopal', 'Madhya Pradesh', 23.2599, 77.4126),
    City('Chandigarh', 'Chandigarh', 30.7333, 76.7794),
    City('Guwahati', 'Assam', 26.1445, 91.7362),
    City('Visakhapatnam', 'Andhra Pradesh', 17.6868, 83.2185),
]

def get_cities_list() -> list[dict]:
    return [{'name': c.name, 'state': c.state, 'lat': c.lat, 'lon': c.lon} for c in CITIES]
