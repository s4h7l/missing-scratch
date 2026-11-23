"""Prepare separate public and gated artifacts for one database transaction."""

from backend.services.datasets import difficulty
from hashlib import sha256
from backend.core.factory import QUESTIONS, Task, Trial
from backend.services.render import render_task


from .description import describe

def prepare(task: Task, pair_id: str | None):
    image = render_task(task)
    evidence = describe(task.base)
    evidence["alternatives"] = {label: describe(trial) for label, trial in task.alternatives.items()}
    evidence["input_sha256"] = sha256(image).hexdigest()
    evidence["reveal_image_url"] = f"/api/tasks/{task.task_id}/reveal/image"
    public = {
        "task_id": task.task_id, "kind": task.kind, "question": QUESTIONS[task.kind],
        "image_url": f"/api/tasks/{task.task_id}/image", "options": list(task.options),
        "difficulty": difficulty(task), "pair_id": pair_id,
    }
    private = {"answer": task.answer, "seed": task.seed, "evidence": evidence}
    return public, private, image, render_task(task, reveal=True)
