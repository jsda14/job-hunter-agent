from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, model_validator


class SourcePlatform(str, Enum):
    LEVER = "lever"
    GREENHOUSE = "greenhouse"
    ASHBY = "ashby"


class JobRaw(BaseModel):
    id: str
    platform: SourcePlatform
    external_id: str
    title: str = Field(min_length=3)
    company: str = Field(min_length=2)
    url: HttpUrl
    location: str
    raw_description: str = Field(min_length=1)
    posted_at: Optional[datetime] = None


class JobEvaluation(BaseModel):
    job_id: str
    fit_score: float = Field(ge=0.0, le=100.0)
    salary_match: bool
    requires_spoken_english: bool
    tech_stack_detected: list[str] = Field(default_factory=list)
    pros: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    is_actionable: bool
    tailored_pitch: Optional[str] = None

    @model_validator(mode="after")
    def validate_spoken_english_actionable(self) -> "JobEvaluation":
        if self.requires_spoken_english and self.is_actionable:
            raise ValueError("Spoken English jobs cannot be actionable")
        return self
