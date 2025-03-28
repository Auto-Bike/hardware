import requests
import json
from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass
class RouteStep:
    instruction: str
    maneuver: str
    distance: float
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float


class RoutePlanner:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.endpoint = "https://routes.googleapis.com/directions/v2:computeRoutes"
        self.steps: Deque[RouteStep] = deque()

    def fetch_route(
        self, origin: dict, destination: dict, travel_mode: str = "BICYCLE"
    ) -> None:
        payload = json.dumps(
            {
                "origin": {"location": {"latLng": origin}},
                "destination": {"location": {"latLng": destination}},
                "travelMode": travel_mode,
            }
        )

        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.legs.steps",
            "Content-Type": "application/json",
        }

        response = requests.post(self.endpoint, headers=headers, data=payload)

        if response.status_code != 200:
            raise Exception(
                f"Google API error: {response.status_code} - {response.text}"
            )

        self._parse_steps(response.json())

    def _parse_steps(self, data: dict) -> None:
        self.steps.clear()
        steps_data = data.get("routes", [])[0]["legs"][0]["steps"]

        for step in steps_data:
            nav = step.get("navigationInstruction", {})
            route_step = RouteStep(
                instruction=nav.get("instructions", "No instruction"),
                maneuver=nav.get("maneuver", "No maneuver"),
                distance=step.get("distanceMeters", 0),
                start_lat=step["startLocation"]["latLng"]["latitude"],
                start_lng=step["startLocation"]["latLng"]["longitude"],
                end_lat=step["endLocation"]["latLng"]["latitude"],
                end_lng=step["endLocation"]["latLng"]["longitude"],
            )
            self.steps.append(route_step)

    def get_steps(self) -> Deque[RouteStep]:
        return self.steps


if __name__ == "__main__":
    API_KEY = "AIzaSyC077vVBOB3V3xiSqE3tyX2HZdA7vQADgE"

    origin = {"latitude": 43.2555916, "longitude": -79.9354599}
    destination = {"latitude": 43.2553011, "longitude": -79.9288588}

    planner = RoutePlanner(api_key=API_KEY)
    planner.fetch_route(origin, destination)

    for idx, step in enumerate(planner.get_steps(), 1):
        print(f"Step {idx}: {step.instruction} ({step.distance} meters)")
        print(f"    Start: ({step.start_lat}, {step.start_lng})")
        print(f"    End:   ({step.end_lat}, {step.end_lng})\n")
