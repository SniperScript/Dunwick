"""
Borough Navigation & Deceptive Pathing Engine for 1924 Dunwick-on-Severn:
Routes the Ashford-Mercer Protagonist and Borough NPCs along High Street cobbles
and through building doorways while respecting locked or guarded foundry gates.
"""

import math
from config import BUILDINGS, WORLD_WIDTH, WORLD_HEIGHT


# Building entrance portals connecting to High Street
BUILDING_PORTALS = {
    "home": {"door_id": None, "inside": (450.0, 680.0), "street": (450.0, 775.0)},
    "cafe": {"door_id": None, "inside": (1290.0, 680.0), "street": (1290.0, 775.0)},
    "office": {"door_id": "office_door", "inside": (2140.0, 680.0), "street": (2140.0, 775.0)},
    "school": {"door_id": None, "inside": (450.0, 1080.0), "street": (450.0, 990.0)},
    "market": {"door_id": None, "inside": (1290.0, 1080.0), "street": (1290.0, 990.0)},
    "park": {"door_id": None, "inside": (2140.0, 1080.0), "street": (2140.0, 990.0)},
}


def get_sector_at(x: float, y: float) -> str:
    """Returns the building/sector ID containing (x, y), or 'street' if on High Street / wynds."""
    for sec in BUILDINGS:
        rx, ry, rw, rh = sec["rect"]
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return sec["id"]
    return "street"


def compute_nav_waypoints(start_x: float, start_y: float, target_x: float, target_y: float) -> list[dict]:
    """
    Computes a realistic borough path from (start_x, start_y) to (target_x, target_y)
    via building front doors and High Street cobbles.
    """
    start_sec = get_sector_at(start_x, start_y)
    end_sec = get_sector_at(target_x, target_y)

    waypoints = []
    if start_sec == end_sec:
        waypoints.append({"x": target_x, "y": target_y, "door_id": None})
        return waypoints

    if start_sec in BUILDING_PORTALS:
        p = BUILDING_PORTALS[start_sec]
        waypoints.append({"x": p["inside"][0], "y": p["inside"][1], "door_id": p["door_id"]})
        waypoints.append({"x": p["street"][0], "y": p["street"][1], "door_id": p["door_id"]})

    if end_sec in BUILDING_PORTALS:
        p = BUILDING_PORTALS[end_sec]
        waypoints.append({"x": p["street"][0], "y": p["street"][1], "door_id": None})
        waypoints.append({"x": p["inside"][0], "y": p["inside"][1], "door_id": p["door_id"]})

    waypoints.append({"x": target_x, "y": target_y, "door_id": None})
    return waypoints


def clamp_to_walkable(old_x: float, old_y: float, new_x: float, new_y: float, props_by_id: dict) -> tuple[float, float]:
    nx = max(125.0, min(WORLD_WIDTH - 125.0, new_x))
    ny = max(125.0, min(WORLD_HEIGHT - 125.0, new_y))

    old_sec = get_sector_at(old_x, old_y)
    new_sec = get_sector_at(nx, ny)

    if old_sec == new_sec:
        return nx, ny

    transition_sec = new_sec if new_sec in BUILDING_PORTALS else old_sec
    if transition_sec in BUILDING_PORTALS:
        portal = BUILDING_PORTALS[transition_sec]
        door_x = portal["inside"][0]
        door_y = 740.0 if transition_sec in ("home", "cafe", "office") else 1020.0
        dist_to_door = math.hypot(nx - door_x, ny - door_y)

        if dist_to_door <= 68.0:
            door_id = portal["door_id"]
            if door_id and door_id in props_by_id:
                if props_by_id[door_id].get("state") != "OPEN":
                    return old_x, old_y
            return nx, ny

        if get_sector_at(nx, old_y) == old_sec:
            return nx, old_y
        if get_sector_at(old_x, ny) == old_sec:
            return old_x, ny
        return old_x, old_y

    return nx, ny
