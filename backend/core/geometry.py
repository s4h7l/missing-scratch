"""Finite-mirror visibility with two independent geometric solvers."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, sin

EPSILON = 1e-8


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Disk:
    blocker_id: str
    center: Point
    radius: float


@dataclass(frozen=True)
class Scene:
    camera: Point
    target: Point
    mirror_start: Point
    mirror_end: Point
    reflective_normal: Point
    camera_heading: float  # radians, in the same coordinate system as the points
    camera_fov: float  # full field of view, radians
    blockers: tuple[Disk, ...] = ()


@dataclass(frozen=True)
class Check:
    visible: bool
    hit: Point | None
    reason: str
    blocker_id: str | None = None


def _dot(a: Point, b: Point) -> float:
    return a.x * b.x + a.y * b.y


def _sub(a: Point, b: Point) -> Point:
    return Point(a.x - b.x, a.y - b.y)


def _add(a: Point, b: Point) -> Point:
    return Point(a.x + b.x, a.y + b.y)


def _scale(a: Point, k: float) -> Point:
    return Point(a.x * k, a.y * k)


def _distance(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def _unit(a: Point) -> Point:
    length = hypot(a.x, a.y)
    if length <= EPSILON:
        raise ValueError("A zero-length direction is not valid")
    return Point(a.x / length, a.y / length)


def _mirror_parameter(scene: Scene, point: Point) -> float:
    edge = _sub(scene.mirror_end, scene.mirror_start)
    return _dot(_sub(point, scene.mirror_start), edge) / _dot(edge, edge)


def _point_on_mirror(scene: Scene, t: float) -> Point:
    return _add(scene.mirror_start, _scale(_sub(scene.mirror_end, scene.mirror_start), t))


def _virtual_image(scene: Scene) -> Point:
    edge = _unit(_sub(scene.mirror_end, scene.mirror_start))
    normal = Point(-edge.y, edge.x)
    offset = _dot(_sub(scene.target, scene.mirror_start), normal)
    return _sub(scene.target, _scale(normal, 2.0 * offset))


def _line_hit(scene: Scene, image: Point) -> Point | None:
    """Intersect camera-to-virtual-target with the infinite mirror line."""
    ray = _sub(image, scene.camera)
    edge = _sub(scene.mirror_end, scene.mirror_start)
    denominator = ray.x * edge.y - ray.y * edge.x
    if abs(denominator) <= EPSILON:
        return None
    offset = _sub(scene.mirror_start, scene.camera)
    ray_t = (offset.x * edge.y - offset.y * edge.x) / denominator
    if ray_t <= 0.0:
        return None
    return _add(scene.camera, _scale(ray, ray_t))


def _point_segment_distance(point: Point, start: Point, end: Point) -> float:
    edge = _sub(end, start)
    length_sq = _dot(edge, edge)
    if length_sq <= EPSILON:
        return _distance(point, start)
    t = max(0.0, min(1.0, _dot(_sub(point, start), edge) / length_sq))
    return _distance(point, _add(start, _scale(edge, t)))


def _blocker_on_path(scene: Scene, hit: Point) -> Disk | None:
    for disk in scene.blockers:
        if (
            _point_segment_distance(disk.center, scene.camera, hit) <= disk.radius
            or _point_segment_distance(disk.center, hit, scene.target) <= disk.radius
        ):
            return disk
    return None


def _finish_check(scene: Scene, hit: Point | None) -> Check:
    if hit is None:
        return Check(False, None, "no_mirror_intersection")
    t = _mirror_parameter(scene, hit)
    if t < -EPSILON / _distance(scene.mirror_start, scene.mirror_end) or t > 1.0 + EPSILON / _distance(scene.mirror_start, scene.mirror_end):
        return Check(False, hit, "outside_finite_mirror")

    normal = _unit(scene.reflective_normal)
    if _dot(_sub(scene.camera, hit), normal) <= EPSILON:
        return Check(False, hit, "camera_on_nonreflective_side")
    if _dot(_sub(scene.target, hit), normal) <= EPSILON:
        return Check(False, hit, "target_on_nonreflective_side")

    camera_ray = _sub(hit, scene.camera)
    ray_angle = atan2(camera_ray.y, camera_ray.x)
    angle_error = atan2(sin(ray_angle - scene.camera_heading), cos(ray_angle - scene.camera_heading))
    if abs(angle_error) > scene.camera_fov / 2.0 + EPSILON:
        return Check(False, hit, "outside_camera_fov")

    disk = _blocker_on_path(scene, hit)
    if disk is not None:
        return Check(False, hit, "blocked", disk.blocker_id)
    return Check(True, hit, "clear")


def solve_by_reflection(scene: Scene) -> Check:
    """Solver A: reflect the target across the mirror, then intersect the ray."""
    for point, reason in ((scene.camera, "camera_on_nonreflective_side"), (scene.target, "target_on_nonreflective_side")):
        if _dot(_sub(point, scene.mirror_start), scene.reflective_normal) <= EPSILON:
            return Check(False, None, reason)
    hit = _line_hit(scene, _virtual_image(scene))
    return _finish_check(scene, hit)


def solve_by_path_minimization(scene: Scene) -> Check:
    """Solver B: minimize camera-to-mirror plus mirror-to-target path length."""
    start, end = scene.mirror_start, scene.mirror_end
    width = _distance(start, end)
    tangent = _unit(_sub(end, start))
    normal = _unit(scene.reflective_normal)
    projections = []
    for point, reason in ((scene.camera, "camera_on_nonreflective_side"), (scene.target, "target_on_nonreflective_side")):
        offset = _sub(point, start)
        height = _dot(offset, normal)
        if height <= EPSILON:
            return Check(False, None, reason)
        projections.append((_dot(offset, tangent), height))

    # Along the infinite mirror, the path length has a strictly increasing
    # derivative. Its zero lies between the two projected endpoints.
    left, right = sorted(position for position, _ in projections)
    for _ in range(54):
        mid = (left + right) / 2
        slope = sum((mid - x) / hypot(mid - x, h) for x, h in projections)
        if slope < 0:
            left = mid
        else:
            right = mid
    coordinate = (left + right) / 2
    hit = _add(start, _scale(tangent, coordinate))
    if coordinate < -EPSILON or coordinate > width + EPSILON:
        return Check(False, hit, "outside_finite_mirror")

    view = _unit(_sub(hit, scene.camera))
    heading = Point(cos(scene.camera_heading), sin(scene.camera_heading))
    if _dot(view, heading) < cos(scene.camera_fov / 2) - EPSILON:
        return Check(False, hit, "outside_camera_fov")

    # Intersect each closed segment with the disk by solving a quadratic.
    for disk in scene.blockers:
        for first, last in ((scene.camera, hit), (hit, scene.target)):
            v, w = _sub(last, first), _sub(first, disk.center)
            a, b = _dot(v, v), _dot(w, v)
            discriminant = b*b - a*(_dot(w, w) - disk.radius**2)
            if discriminant >= 0:
                root = discriminant ** 0.5
                if -b + root >= 0 and -b - root <= a:
                    return Check(False, hit, "blocked", disk.blocker_id)
    return Check(True, hit, "clear")


def verify(scene: Scene) -> tuple[Check, Check]:
    """Return both solver results; callers must reject disagreement."""
    return solve_by_reflection(scene), solve_by_path_minimization(scene)

