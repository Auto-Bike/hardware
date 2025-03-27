import requests
import json
from collections import deque
import math

url = "https://routes.googleapis.com/directions/v2:computeRoutes"

payload = json.dumps(
    {
        "origin": {
            "location": {"latLng": {"latitude": 43.2555916, "longitude": -79.9354599}}
        },
        "destination": {
            "location": {"latLng": {"latitude": 43.2553011, "longitude": -79.9288588}}
        },
        "travelMode": "BICYCLE",
    }
)
headers = {
    "X-Goog-Api-Key": "AIzaSyC077vVBOB3V3xiSqE3tyX2HZdA7vQADgE",
    "X-Goog-FieldMask": "routes.legs.steps",
    "Content-Type": "application/json",
}

response = requests.request("POST", url, headers=headers, data=payload)

steps = response.json()["routes"][0]["legs"][0]["steps"]


que = deque()
for idx, step in enumerate(steps, 1):
    instruction = step.get("navigationInstruction", {}).get(
        "instructions", "No instruction"
    )
    maneuver = step.get("navigationInstruction", {}).get("maneuver", "No maneuver")
    distance = step.get("distanceMeters", 0)

    start_lat = step["startLocation"]["latLng"]["latitude"]
    start_lng = step["startLocation"]["latLng"]["longitude"]
    end_lat = step["endLocation"]["latLng"]["latitude"]
    end_lng = step["endLocation"]["latLng"]["longitude"]

    que.append(
        {
            "instruction": instruction,
            "maneuver": maneuver,
            "distance": distance,
            "start_lat": start_lat,
            "start_lng": start_lng,
            "end_lat": end_lat,
            "end_lng": end_lng,
        }
    )
    # print(f"Step {idx}: {instruction} ({distance} meters)")
    # print(f"    Start: ({start_lat}, {start_lng})")
    # print(f"    End:   ({end_lat}, {end_lng})\n")
# print(deque)
for i in que:
    print(i)
    print("\n")

# get the first instruction, check the distance, based on speed param file, calculate the time
# meanwhile also check if deque is empty, if not, get the next instruction turning direction,
# if there is turning direction, construct a precise paramater file to allow it turning

# if there is no turning direction, just calculate the time based on the distance then stop


#
"""
while que:
    que = deque()
    value = que.popleft()
    if not que:
        que_next = que[0]
        if que_next["instruction"] == "turn left":
            # construct a precise paramater file to allow it turning
            # calculate the time based on the distance then stop
            distance = get_distance()
            forward_distance = distance - TURNLEFT_param["distance"]
            turning_distance = distance - forward_distance
            forward_time = forward_distance / SPEED_param["forward"]
            Big_Motor(forward_time)
            #turning left
            turning_time = turning_distance / SPEED_param["left"]
            
            
        else turn right:
            # calculate the time based on the distance then stop
            
    else:
        

"""
