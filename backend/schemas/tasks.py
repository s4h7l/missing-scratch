from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from backend.core.factory import Answer, Kind


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Kind = "visibility"


class PublicTask(BaseModel):
    task_id: str
    kind: Kind
    question: str
    image_url: str
    difficulty: Literal["EASY","MEDIUM","HARD"]
    options: list[Answer] = Field(min_length=2, max_length=3)
    pair_id: str | None = None


class PublicPair(BaseModel):
    pair_id: str
    tasks: list[PublicTask] = Field(min_length=2, max_length=2)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prediction: Answer


class PredictResponse(BaseModel):
    task_id: str
    status: Literal["recorded"]


class RevealResponse(BaseModel):
    task_id: str
    ground_truth: Answer
    prediction: Answer
    correct: bool
    evidence: dict
