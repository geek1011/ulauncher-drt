import requests
import urllib
from typing import Iterable

class DRTApiException(Exception):
    def __init__(self, msg: str):
        Exception.__init__(self, msg)

class DRTApi:
    def __init__(self, api_base: str = "https://drtapi.geek1011.net"):
        self.api_base = api_base
    
    def stops(self, q: str = None) -> Iterable['Stop']:
        return [Stop.parse(obj) for obj in self.req("stops", {"q": q})]
    
    def stop(self, id: str) -> 'Stop':
        return Stop.parse(self.req(f"stops/{urllib.parse.quote(str(id), '')}"))
    
    def departures(self, id: str) -> Iterable['Departure']:
        return [Departure.parse(obj) for obj in self.req(f"stops/{urllib.parse.quote(str(id), '')}/departures")]

    def req(self, path: str, params: object = None) -> object:
        obj = requests.get(f"{self.api_base}/v2/{path}", params=params).json()
        if obj["status"] != "success":
            raise DRTApiException(obj["result"])
        return obj["result"]

class Stop:
    def __init__(self, id: int, name: str, lat: float, lon: float):
        self.id = id
        self.name = name
        self.lat = lat
        self.lon = lon
    
    def parse(obj: object) -> 'Stop':
        return Stop(obj["id"], obj["name"], obj["lat"], obj["lon"])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lon": self.lon
        }

class Departure:
    def __init__(self, route_id: str, destination: str, is_real_time: bool, time: str, time_late: str):
        self.route_id = route_id
        self.destination = destination
        self.is_real_time = is_real_time
        self.time = time
        self.time_late = time_late

    def parse(obj: object) -> 'Departure':
        return Departure(obj["routeId"], obj["destination"], obj["isRealTime"], obj["time"], obj["timeLate"])
