"""Draw the input and reveal PNGs from exactly the scenes used by the solvers."""

from io import BytesIO
from math import cos, sin, sqrt
from PIL import Image, ImageDraw, ImageFont

from backend.core.factory import Task, Trial

WIDTH, HEIGHT = 700, 440
INK, BLUE, RAY = "#142a3a", "#1776a1", "#b43d08"


def panel(trial: Trial, title: str, reveal: bool) -> Image.Image:
    scene = trial.scene
    image = Image.new("RGB", (WIDTH, HEIGHT), "#fbfcfd")
    draw = ImageDraw.Draw(image)
    label, small = ImageFont.load_default(size=23), ImageFont.load_default(size=15)
    draw.text((18, 12), title, font=label, fill=INK)
    draw.text((18, HEIGHT-31), "Blue = reflective face     Green edges = camera field of view",
              fill=INK, font=small)
    cx, cy = scene.camera.x, scene.camera.y
    for boundary in (-0.5, 0.5):
        angle = scene.camera_heading + boundary * scene.camera_fov
        draw.line((cx, cy, cx + 188*cos(angle), cy + 188*sin(angle)), fill="#47866d", width=2)

    a, b = scene.mirror_start, scene.mirror_end
    nx, ny = scene.reflective_normal.x, scene.reflective_normal.y
    draw.line((a.x-3*nx, a.y-3*ny, b.x-3*nx, b.y-3*ny), fill="#657582", width=5)
    draw.line((a.x, a.y, b.x, b.y), fill=BLUE, width=3)
    check = trial.checks[0]
    tx, ty = scene.target.x, scene.target.y
    if reveal and check.hit and check.reason in {"clear", "blocked"}:
        points = [(cx, cy), (check.hit.x, check.hit.y), (tx, ty)]
        for (x, y), (end_x, end_y) in zip(points, points[1:]):
            dx, dy = end_x-x, end_y-y
            limit = 1.0
            for disk in scene.blockers:
                wx, wy = x-disk.center.x, y-disk.center.y
                a, b = dx*dx + dy*dy, wx*dx + wy*dy
                discriminant = b*b - a*(wx*wx + wy*wy - disk.radius**2)
                if discriminant >= 0:
                    entry = (-b-sqrt(discriminant))/a
                    if 0 <= entry < limit:
                        limit = entry
            draw.line((x, y, x+limit*dx, y+limit*dy), fill=RAY, width=3)
            if limit < 1:
                break
    draw.ellipse((cx-7, cy-7, cx+7, cy+7), fill=INK)
    draw.text((cx-27, cy+12), "Camera", fill=INK, font=small)
    draw.line((tx-8, ty-8, tx+8, ty+8), fill="#c02d42", width=4)
    draw.line((tx-8, ty+8, tx+8, ty-8), fill="#c02d42", width=4)
    for disk in scene.blockers:
        x, y, r = disk.center.x, disk.center.y, disk.radius
        draw.ellipse((x-r, y-r, x+r, y+r), fill=INK)
        draw.text((x, y), disk.blocker_id, font=small, fill="white", anchor="mm")
    if reveal:
        reason = (f"Blocked by {check.blocker_id}" if check.reason == "blocked"
                  else check.reason.replace("_", " ").capitalize())
        draw.text((18, 48), reason, fill=RAY, font=small)
    return image


def render_task(task: Task, reveal: bool = False) -> bytes:
    if task.kind == "repair":
        panels = [("Current setup", task.base)]
        panels.extend((f"Setting {label}", trial) for label, trial in task.alternatives.items())
        canvas = Image.new("RGB", (2*WIDTH+2, 2*HEIGHT+2), "#b8c6ca")
        for i, (title, scene) in enumerate(panels):
            canvas.paste(panel(scene, title, reveal), ((i%2)*(WIDTH+2), (i//2)*(HEIGHT+2)))
    else:
        canvas = panel(task.base, "Top view", reveal)
    buffer = BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()
