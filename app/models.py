from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class SceneType(str, Enum):
    cinematic = "cinematic"
    infographic = "infographic"
    map = "map"
    chart = "chart"
    archive = "archive"


class Scene(BaseModel):
    id: int
    duration: float = Field(ge=1, le=60)
    narration: str
    scene_type: SceneType
    visual_prompt: str
    title: str = ""
    subtitle: str = ""
    overlay_text: str = ""
    source_query: str = ""
    transition: str = "fade"
    camera_motion: str = "slow_zoom_in"


class ProjectRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=500)
    script: str = Field(default="", max_length=30000)
    target_seconds: int = Field(default=45, ge=15, le=600)
    aspect_ratio: str = Field(default="16:9", pattern="^(16:9|9:16|1:1)$")
    language: str = "vi"


class Project(BaseModel):
    id: str
    status: str
    created_at: datetime | None = None
    progress: int = 0
    request: ProjectRequest
    scenes: list[Scene] = Field(default_factory=list)
    output_url: str | None = None
    error: str | None = None
