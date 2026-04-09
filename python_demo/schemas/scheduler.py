from datetime import datetime
from typing import Any, List, Optional

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
    import_source: Optional[str] = None
    import_uid: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OfficialCalendarEventSchema(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    display_mode: str
    source_year: Optional[int] = None
    event_type: str
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CourseScheduleEventSchema(BaseModel):
    id: int
    user_id: int
    title: str
    course_name: str
    course_code: Optional[str] = None
    instructor: Optional[str] = None
    description: Optional[str] = None
    week_info: Optional[str] = None
    section_text: Optional[str] = None
    weekday: Optional[int] = None
    term_label: Optional[str] = None
    raw_text: Optional[str] = None
    week_start: Optional[int] = None
    week_end: Optional[int] = None
    week_type: Optional[str] = None
    import_source: Optional[str] = None
    import_uid: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SourceImportPayloadSchema(BaseModel):
    rows: Optional[List[dict]] = None
    content: Optional[str] = None
    content_type: str = "auto"
    replace_existing: bool = True


class SourceImportResultSchema(BaseModel):
    imported_count: int
    skipped_count: int = 0
    replace_existing: bool
    preview_count: int = 0
    preview: List[dict] = Field(default_factory=list)
    skipped_rows: List[str] = Field(default_factory=list)


class ScheduleEventSchema(BaseModel):
    source: str
    source_type: Optional[str] = None
    source_id: int
    user_id: Optional[int] = None
    kind: str
    title: str
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    deadline: Optional[datetime] = None
    status: Optional[str] = None
    priority: Optional[int] = None
    location: Optional[str] = None
    display_mode: Optional[str] = None
    is_blocking: bool = True
    is_flexible: bool = False
    source_meta: dict[str, Any] = Field(default_factory=dict)


class ScheduleConflictSchema(BaseModel):
    left_event: ScheduleEventSchema
    right_event: ScheduleEventSchema
    level: str
    reason: str
    conflict_type: str = "time_overlap"
    overlap_start_time: Optional[datetime] = None
    overlap_end_time: Optional[datetime] = None
    is_blocking: bool = True


class SchedulePileupSchema(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    event_count: int
    level: str
    reason: str
    events: List[ScheduleEventSchema] = Field(default_factory=list)


class ScheduleCandidateRescheduleOptionSchema(BaseModel):
    action: str
    target_event_id: int
    suggested_start_time: datetime
    suggested_end_time: datetime
    reason: str
    blocked_by_event_ids: List[int] = Field(default_factory=list)
    rank: int = 1
    confidence: str = "medium"


class ScheduleCandidateFocusBlockSchema(BaseModel):
    suggested_start_time: datetime
    suggested_end_time: datetime
    intended_for_event_ids: List[int] = Field(default_factory=list)
    reason: str
    rank: int = 1
    confidence: str = "medium"


class ScheduleCandidateSplitSegmentSchema(BaseModel):
    suggested_start_time: datetime
    suggested_end_time: datetime


class ScheduleCandidateSplitOptionSchema(BaseModel):
    action: str
    target_event_id: int
    segments: List[ScheduleCandidateSplitSegmentSchema] = Field(default_factory=list)
    total_duration_minutes: int
    reason: str
    rank: int = 1
    confidence: str = "medium"


class ScheduleSuggestionSchema(BaseModel):
    type: str
    message: str
    level: str = "info"
    related_events: List[ScheduleEventSchema] = Field(default_factory=list)
    suggested_start_time: Optional[datetime] = None
    suggested_end_time: Optional[datetime] = None
    suggested_deadline: Optional[datetime] = None
    candidate_reschedule_options: List[ScheduleCandidateRescheduleOptionSchema] = Field(default_factory=list)
    candidate_focus_blocks: List[ScheduleCandidateFocusBlockSchema] = Field(default_factory=list)
    candidate_split_options: List[ScheduleCandidateSplitOptionSchema] = Field(default_factory=list)


class ScheduleAiContextSchema(BaseModel):
    schedule_risk_summary: str = ""
    top_conflicts: List[dict[str, Any]] = Field(default_factory=list)
    top_pileups: List[dict[str, Any]] = Field(default_factory=list)
    top_candidate_actions: List[dict[str, Any]] = Field(default_factory=list)


class ScheduleAnalysisSummarySchema(BaseModel):
    """
    V1 summary is derived only from explicit timeline fields already present in storage.
    It does not estimate task duration or infer hidden availability.
    """
    total_events: int = 0
    blocking_event_count: int = 0
    flexible_event_count: int = 0
    deadline_only_count: int = 0
    conflict_count: int = 0
    pileup_count: int = 0
    suggestion_count: int = 0
    risk_level: str = "low"


class ScheduleAggregateData(BaseModel):
    todos: List[TodoReturnSchema] = Field(default_factory=list)
    official_events: List[OfficialCalendarEventSchema] = Field(default_factory=list)
    schedule_events: List[ScheduleEventSchema] = Field(default_factory=list)
    conflicts: List[ScheduleConflictSchema] = Field(default_factory=list)
    pileups: List[SchedulePileupSchema] = Field(default_factory=list)
    suggestions: List[ScheduleSuggestionSchema] = Field(default_factory=list)
    summary: ScheduleAnalysisSummarySchema = Field(default_factory=ScheduleAnalysisSummarySchema)
    ai_context: ScheduleAiContextSchema = Field(default_factory=ScheduleAiContextSchema)
