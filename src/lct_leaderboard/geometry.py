import math
from typing import Iterable, List, Sequence


Coordinate = Sequence[float]

EARTH_RADIUS_M = 6371008.8


def line_length_m(coordinates: Iterable[Coordinate]) -> float:
    points = list(coordinates)
    if len(points) < 2:
        return 0.0

    if _looks_like_lon_lat(points):
        return sum(_haversine_m(a, b) for a, b in zip(points, points[1:]))

    return sum(_euclidean_m(a, b) for a, b in zip(points, points[1:]))


def geometry_length_m(geometry: dict) -> float:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "LineString":
        return line_length_m(coordinates or [])

    if geometry_type == "MultiLineString":
        return sum(line_length_m(line) for line in coordinates or [])

    return 0.0


def _looks_like_lon_lat(points: List[Coordinate]) -> bool:
    for point in points:
        if len(point) < 2:
            return False
        lon = point[0]
        lat = point[1]
        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return False
    return True


def _haversine_m(a: Coordinate, b: Coordinate) -> float:
    lon1, lat1 = math.radians(a[0]), math.radians(a[1])
    lon2, lat2 = math.radians(b[0]), math.radians(b[1])
    delta_lon = lon2 - lon1
    delta_lat = lat2 - lat1
    h = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def _euclidean_m(a: Coordinate, b: Coordinate) -> float:
    return math.dist(a[:2], b[:2])
