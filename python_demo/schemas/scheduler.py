from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


def validate_todo_time_combination(
    deadline: Optional[datetime],
    start_time: Optional[datetime],
    end_time: Optional[datetime]
) -> str | None:
    if end_time is not None and start_time is None:
        return "结束时间不能单独存在，请先提供开始时间"
    if start_time is not None and end_time is not None and end_time < start_time:
        return "结束时间不能早于开始时间"
    if deadline is None and start_time is None and end_time is None:
        return "请至少提供 deadline 或 start_time/end_time"
    return None


def is_range_todo_payload(
    start_time: Optional[datetime],
    end_time: Optional[datetime]
) -> bool:
    return start_time is not None and end_time is not None


def has_datetime_range_overlap(
    a_start: Optional[datetime],
    a_end: Optional[datetime],
    b_start: Optional[datetime],
    b_end: Optional[datetime]
) -> bool:
    if not (a_start and a_end and b_start and b_end):
        return False
    return a_start < b_end and b_start < a_end


class TodoCreateSchema(BaseModel):
    title: str
    content: Optional[str] = None
    status: str = "pending"
    priority: int = 2
    deadline: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def get_time_validation_error(self) -> str | None:
        return validate_todo_time_combination(
            deadline=self.deadline,
            start_time=self.start_time,
            end_time=self.end_time,
        )


class TodoUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_update_dict(self) -> dict:
        return self.model_dump(exclude_unset=True)


class TodoStatusUpdateSchema(BaseModel):
    status: str


class TodoReturnSchema(BaseModel):
    id: int
    user_id: int
    title: str
    content: Optional[str] = None
    status: str
    priority: int
    deadline: Optional[datetime] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfficialCalendarEventSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    event_type: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleEventSchema(BaseModel):
    source_type: str
    source_id: int
    user_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    location: Optional[str] = None


class ScheduleConflictSchema(BaseModel):
    left_event: ScheduleEventSchema
    right_event: ScheduleEventSchema
    level: str
    reason: str


class ScheduleAggregateData(BaseModel):
    todos: List[TodoReturnSchema]
    official_events: List[OfficialCalendarEventSchema]
    schedule_events: List[ScheduleEventSchema]
    conflicts: List[ScheduleConflictSchema]
    suggestions: List[str] = Field(default_factory=list)
