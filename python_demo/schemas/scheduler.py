from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class TodoCreateSchema(BaseModel):
    title: str
    content: Optional[str] = None
    status: str = "pending"
    priority: int = 2
    deadline: datetime


class TodoUpdateSchema(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    deadline: Optional[datetime] = None


class TodoStatusUpdateSchema(BaseModel):
    status: str


class TodoReturnSchema(BaseModel):
    id: int
    user_id: int
    title: str
    content: Optional[str] = None
    status: str
    priority: int
    deadline: datetime
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
