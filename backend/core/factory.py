"""Construct reproducible paired layouts and verify every answer before release."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import atan2, cos, hypot, radians, sin
from random import Random
from secrets import randbits, token_hex
from typing import Literal

from backend.core.geometry import Check, Disk, Point, Scene, verify

Kind = Literal["visibility", "obstruction", "repair"]
Answer = Literal["VISIBLE", "NOT_VISIBLE", "A", "B", "C"]
LABELS = ("A", "B", "C")
QUESTIONS = {
    "visibility": "Can the camera see X through the mirror?",
    "obstruction": "Removing which single object restores the reflected view of X?",
    "repair": "Which mirror setting restores the reflected view of X from the current setup?",
}


class RejectedLayout(Exception):
    """A candidate is ambiguous or fails an optical constraint."""


class GenerationExhausted(Exception):
    pass


@dataclass(frozen=True)
class Trial:
    scene: Scene
    checks: tuple[Check, Check]

    @property
    def visible(self) -> bool:
        return self.checks[0].visible


@dataclass(frozen=True)
class Task:
    task_id: str
    kind: Kind
    seed: int
    base: Trial
    alternatives: dict[str, Trial]
    answer: str

    @property
    def options(self):
        return ("VISIBLE", "NOT_VISIBLE") if self.kind == "visibility" else LABELS


def separation(a: Point, b: Point) -> float:
    return hypot(a.x - b.x, a.y - b.y)


def sight_angle(start: Point, end: Point) -> float:
    return atan2(end.y - start.y, end.x - start.x)


def distance_to_leg(point: Point, a: Point, b: Point) -> float:
    dx, dy = b.x - a.x, b.y - a.y
    fraction = ((point.x - a.x)*dx + (point.y - a.y)*dy) / (dx*dx + dy*dy)
    fraction = min(1, max(0, fraction))
    return hypot(point.x - a.x - fraction*dx, point.y - a.y - fraction*dy)


def checked(scene: Scene) -> Trial:
    first, second = verify(scene)
    if (first.visible, first.reason, first.blocker_id) != (second.visible, second.reason, second.blocker_id):
        raise RejectedLayout()
    hit = first.hit
    if hit is None or second.hit is None or separation(hit, second.hit) > 0.01:
        raise RejectedLayout()
    if min(separation(hit, tip) for tip in (scene.mirror_start, scene.mirror_end)) < 5:
        raise RejectedLayout()
    offset = sight_angle(scene.camera, hit) - scene.camera_heading
    error = abs(atan2(sin(offset), cos(offset)))
    if abs(error - scene.camera_fov/2) < radians(3):
        raise RejectedLayout()
    for disk in scene.blockers:
        clearance = min(distance_to_leg(disk.center, a, b) for a, b in
                        ((scene.camera, hit), (hit, scene.target))) - disk.radius
        if abs(clearance) < 3:
            raise RejectedLayout()
    return Trial(scene, (first, second))


def with_mirror(scene: Scene, center: Point, half_width: float, angle: float) -> Scene:
    dx, dy = half_width*cos(angle), half_width*sin(angle)
    return replace(scene, mirror_start=Point(center.x-dx, center.y-dy),
                   mirror_end=Point(center.x+dx, center.y+dy),
                   reflective_normal=Point(-sin(angle), cos(angle)))


def layouts(rng: Random) -> tuple[list[Scene], Scene]:
    camera = Point(rng.uniform(95, 160), rng.uniform(315, 360))
    target = Point(rng.uniform(535, 610), rng.uniform(310, 355))
    center = Point(rng.uniform(330, 370), rng.uniform(135, 175))
    scene = Scene(camera, target, center, center, Point(0, 1),
                  sight_angle(camera, center), radians(68))
    mid, delta = radians(rng.uniform(-3, 3)), radians(rng.uniform(10, 14))
    half = rng.uniform(155, 175)
    angles = [mid - delta, mid, mid + delta]
    rng.shuffle(angles)
    choices = [with_mirror(scene, center, half, a) for a in angles]
    broken = with_mirror(scene, center, half, mid + rng.choice([-1, 1])*radians(26))
    return choices, broken


def on_leg(a: Point, b: Point, fraction: float, offset: float = 0) -> Point:
    dx, dy = b.x-a.x, b.y-a.y
    length = hypot(dx, dy)
    return Point(a.x + dx*fraction - offset*dy/length, a.y + dy*fraction + offset*dx/length)


def make_task(kind: Kind, seed: int, base: Trial, alternatives: dict[str, Trial]) -> Task:
    if kind == "visibility":
        answer = "VISIBLE" if base.visible else "NOT_VISIBLE"
    else:
        working = [label for label, trial in alternatives.items() if trial.visible]
        if base.visible or len(working) != 1:
            raise RejectedLayout()
        answer = working[0]
        if kind == "obstruction" and base.checks[0].blocker_id != answer:
            raise RejectedLayout()
    return Task("MS-" + token_hex(12).upper(), kind, seed, base, alternatives, answer)


def obstruction_trial(kind: Kind, seed: int, scene: Scene) -> Task:
    base = checked(scene)
    removals = {}
    if kind == "obstruction":
        for disk in scene.blockers:
            remaining = tuple(d for d in scene.blockers if d != disk)
            removals[disk.blocker_id] = checked(replace(scene, blockers=remaining))
    return make_task(kind, seed, base, removals)


def disk_pair(kind: Kind, seed: int, rng: Random, choices: list[Scene]) -> list[Task]:
    # Use the two most separated mirror settings and keep all disks fixed.
    scenes = sorted(choices, key=lambda s: s.mirror_start.y)
    scenes = [scenes[0], scenes[-1]]
    hits = [checked(scene) for scene in scenes]
    if not all(trial.visible for trial in hits):
        raise RejectedLayout()
    endpoint = rng.choice([scenes[0].camera, scenes[0].target])
    points = [on_leg(endpoint, trial.checks[0].hit, rng.uniform(.48, .72))
              for trial in hits]
    other = scenes[0].target if endpoint == scenes[0].camera else scenes[0].camera
    if kind == "visibility":
        points[1] = on_leg(other, hits[1].checks[0].hit, rng.uniform(.45, .7), rng.choice([-32, 32]))
    points.append(on_leg(other, hits[0].checks[0].hit, rng.uniform(.42, .73), rng.choice([-34, 34])))
    if any(separation(a, b) < 38 for i, a in enumerate(points) for b in points[i+1:]):
        raise RejectedLayout()
    rng.shuffle(points)
    disks = tuple(Disk(label, point, rng.uniform(10, 13)) for label, point in zip(LABELS, points))
    return [obstruction_trial(kind, seed, replace(s, blockers=disks)) for s in scenes]


def repair_pair(seed: int, rng: Random, choices: list[Scene], broken: Scene) -> list[Task]:
    trials = [checked(scene) for scene in choices]
    if not all(t.visible for t in trials):
        raise RejectedLayout()
    headings = [sight_angle(t.scene.camera, t.checks[0].hit) for t in trials]
    gap = min(abs(a-b) for i, a in enumerate(headings) for b in headings[i+1:])
    # The camera aperture is identical for both members. Only aim changes.
    result = []
    for aim in rng.sample(headings, 2):
        def aimed(scene: Scene) -> Trial:
            return checked(replace(scene, camera_heading=aim, camera_fov=gap))
        result.append(make_task("repair", seed, aimed(broken),
                                {label: aimed(scene) for label, scene in zip(LABELS, choices)}))
    return result


def generate_pair(kind: Kind, seed: int | None = None) -> list[Task]:
    seed = randbits(63) if seed is None else seed
    rng = Random(seed)
    for _ in range(120):
        choices, broken = layouts(rng)
        try:
            tasks = repair_pair(seed, rng, choices, broken) if kind == "repair" else disk_pair(kind, seed, rng, choices)
        except RejectedLayout:
            continue
        if tasks[0].answer != tasks[1].answer:
            rng.shuffle(tasks)
            return tasks
    raise GenerationExhausted("No unambiguous layout found within the attempt limit")
