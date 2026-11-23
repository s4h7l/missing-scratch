from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

Short = Annotated[str, Field(min_length=1,max_length=128,pattern=r"^[\w./:@+ -]+$")]
Note = Annotated[str,Field(max_length=2000)]
Positive = Annotated[float,Field(gt=0,le=10000,allow_inf_nan=False)]
Coordinate = Annotated[float,Field(ge=-1000,le=1000,allow_inf_nan=False)]
Point = tuple[Coordinate,Coordinate]
Provider = Literal["openai","gemini","openrouter"]
Mode = Literal["vision","question-only"]
Reviewer = Literal["R1","R2"]


class Body(BaseModel):
    model_config=ConfigDict(extra="forbid",allow_inf_nan=False)


class DatasetRequest(Body):
    suite: Literal["pilot","corrected"]="pilot"
    pairs: int=Field(3,ge=1,le=100)
    seed: int|None=Field(None,ge=0,le=2**55)


class ReviewStart(Body):
    dataset_id: Short
    count:int=Field(72,ge=2,le=200,multiple_of=2)


class Entry(Body):
    code: Short
    answer: Literal["A","B","C","VISIBLE","NOT_VISIBLE"]|None
    evidence: Note=""
    ambiguity: Note=""
    confidence: int|None=Field(None,ge=1,le=5)


class Sheet(Body):
    responses: list[Entry]=Field(min_length=1,max_length=200)


class Decision(Body):
    accepted:bool
    notes:str=Field(min_length=3,max_length=5000)


class MeasuredDisk(Body):
    id:Literal["A","B","C"]
    center_mm:Point
    radius_mm:Positive


class Stage(Body):
    camera_mm:Point
    target_mm:Point
    mirror_start_mm:Point
    mirror_end_mm:Point
    camera_yaw_deg: Coordinate
    camera_fov_deg:float=Field(gt=0,lt=180)
    blockers:list[MeasuredDisk]=Field(max_length=3)


class Calibration(Body):
    task_id:Short
    observer:Short
    trial:Short
    scale_bar_mm:Positive
    mirror_width_mm:Positive
    lens_height_mm:Positive
    target_height_mm:Positive
    measurements:dict[str,Stage]=Field(min_length=1,max_length=4)


class RunStart(Body):
    dataset_id:Short
    provider:Provider
    model:Short
    mode:Mode
    max_output_tokens:int=Field(512,ge=16,le=4096)


class Evaluation(Body):
    model: Short


class ReplayEntry(BaseModel):
    task_id:Short
    image_sha256:str=Field(min_length=64,max_length=64)
    prompt_sha256:str=Field(min_length=64,max_length=64)
    status:Literal["ok","invalid","error","missing","sending","interrupted"]
    raw:str|None=Field(None,max_length=150000)
    metadata:dict=Field(default_factory=dict)


class Replay(BaseModel):
    dataset_id:Short
    manifest_sha256:str=Field(min_length=64,max_length=64)
    provider:Short
    model:Short
    mode:Mode
    settings:dict
    records:list[ReplayEntry]=Field(max_length=200)
