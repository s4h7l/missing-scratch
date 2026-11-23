from backend.core.factory import Trial

def describe(trial: Trial) -> dict:
    scene = trial.scene

    def xy(point):
        return [point.x, point.y]

    return {
        "scene": {
            "camera": xy(scene.camera), "target": xy(scene.target),
            "mirror": [xy(scene.mirror_start), xy(scene.mirror_end)],
            "reflective_normal": xy(scene.reflective_normal),
            "camera_heading": scene.camera_heading, "camera_fov": scene.camera_fov,
            "blockers": [{"id": b.blocker_id, "center": xy(b.center), "radius": b.radius}
                         for b in scene.blockers],
        },
        "solver_checks": [
            {"solver": name, "visible": c.visible, "reason": c.reason,
             "hit": xy(c.hit) if c.hit else None, "blocker_id": c.blocker_id}
            for name, c in zip(("virtual_image", "stationary_path"), trial.checks)
        ],
    }


