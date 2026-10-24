"""
Neighborhood Navigation & Deceptive Pathing Engine ("The Stanford Method"):
Routes the Mercer Family and Town NPCs along Main Street sidewalks and through
building doorways while respecting locked/barricaded security gates.
"""

import math
from config import SECTORS, WORLD_WIDTH, WORLD_HEIGHT


# Building entrance portals connecting to Main Street (y=790)
BUILDING_PORTALS = {
    "home": {"door_id": None, "inside": (420.0, 625.0), "street": (420.0, 770.0)},
    "parlor": {"door_id": None, "inside": (1230.0, 625.0), "street": (1230.0, 770.0)},
    "office": {"door_id": "office_door", "inside": (2040.0, 615.0), "street": (2040.0, 770.0)},
    "school": {"door_id": None, "inside": (420.0, 960.0), "street": (420.0, 815.0)},
    "shop": {"door_id": None, "inside": (1230.0, 960.0), "street": (1230.0, 815.0)},
    "park": {"door_id": None, "inside": (2040.0, 960.0), "street": (2040.0, 815.0)},
}


def get_sector_at(x: float, y: float) -> str:
    """Returns the building/sector ID containing (x, y), or 'street' if on Main Street / avenues."""
    for sec in SECTORS:
        rx, ry, rw, rh = sec["rect"]
        if rx <= x <= rx + rw and ry <= y <= ry + rh:
            return sec["id"]
    return "street"


def compute_nav_waypoints(start_x: float, start_y: float, target_x: float, target_y: float) -> list[dict]:
    """
    Computes a realistic neighborhood path from (start_x, start_y) to (target_x, target_y)
    via building front doors and Main Street sidewalks.
    """
    start_sec = get_sector_at(start_x, start_y)
    end_sec = get_sector_at(target_x, target_y)

    waypoints = []
    if start_sec == end_sec:
        waypoints.append({"x": target_x, "y": target_y, "door_id": None})
        return waypoints

    # Step 1: Exit current building onto Main Street
    if start_sec in BUILDING_PORTALS:
        p = BUILDING_PORTALS[start_sec]
        waypoints.append({"x": p["inside"][0], "y": p["inside"][1], "door_id": p["door_id"]})
        waypoints.append({"x": p["street"][0], "y": p["street"][1], "door_id": p["door_id"]})

    # Step 2: Walk along Main Street to destination building entrance
    if end_sec in BUILDING_PORTALS:
        p = BUILDING_PORTALS[end_sec]
        waypoints.append({"x": p["street"][0], "y": p["street"][1], "door_id": None})
        waypoints.append({"x": p["inside"][0], "y": p["inside"][1], "door_id": p["door_id"]})

    waypoints.append({"x": target_x, "y": target_y, "door_id": None})
    return waypoints


def clamp_to_walkable(old_x: float, old_y: float, new_x: float, new_y: float, props_by_id: dict) -> tuple[float, float]:
    """
    Enforces building walls so characters enter/exit buildings through their front doorways
    and cannot walk through a locked or barricaded Sub-Station Security Gate.
    """
    nx = max(125.0, min(WORLD_WIDTH - 125.0, new_x))
    ny = max(125.0, min(WORLD_HEIGHT - 125.0, new_y))

    old_sec = get_sector_at(old_x, old_y)
    new_sec = get_sector_at(nx, ny)

    if old_sec == new_sec:
        return nx, ny

    # Check if crossing a building doorway
    transition_sec = new_sec if new_sec in BUILDING_PORTALS else old_sec
    if transition_sec in BUILDING_PORTALS:
        portal = BUILDING_PORTALS[transition_sec]
        door_x = portal["inside"][0]
        door_y = 660.0 if transition_sec in ("home", "parlor", "office") else 920.0
        dist_to_door = math.hypot(nx - door_x, ny - door_y)

        if dist_to_door <= 68.0:
            door_id = portal["door_id"]
            if door_id and door_id in props_by_id:
                if props_by_id[door_id]["state"] != "OPEN":
                    return old_x, old_y
            return nx, ny

        # Slide along wall if not at doorway
        if get_sector_at(nx, old_y) == old_sec:
            return nx, old_y
        if get_sector_at(old_x, ny) == old_sec:
            return old_x, ny
        return old_x, old_y

    return nx, ny
