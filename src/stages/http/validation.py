# -*- coding: iso8859-15 -*-
from datetime import date
from typing import Any, List, Optional
from pydantic import BaseModel, Field, conint


class StageInput(BaseModel):
    id: Optional[int] = Field(None, description="ID of the stage")
    fileLocation: Optional[str] = Field(None, description="Location of the file")
    status: str = Field(..., description="Status of the stage")
    visibility: Optional[bool] = Field(None, description="Visibility of the stage")
    cover: Optional[str] = Field(None, description="Cover image URL")
    name: str = Field(..., description="Name of the stage")
    description: Optional[str] = Field(None, description="Description of the stage")
    playerAccess: Optional[str] = Field(None, description="Player access information")
    config: Optional[str] = Field(None, description="Configuration of the stage")
    owner: Optional[str] = None


class UpdateStageInput(BaseModel):
    id: Optional[int] = Field(None, description="ID of the stage")
    fileLocation: Optional[str] = Field(None, description="Location of the file")
    status: Optional[str] = Field(None, description="Status of the stage")
    visibility: Optional[bool] = Field(None, description="Visibility of the stage")
    cover: Optional[str] = Field(None, description="Cover image URL")
    name: Optional[str] = Field(None, description="Name of the stage")
    description: Optional[str] = Field(None, description="Description of the stage")
    playerAccess: Optional[str] = Field(None, description="Player access information")
    config: Optional[str] = Field(None, description="Configuration of the stage")
    owner: Optional[str] = None


class DuplicateStageInput(BaseModel):
    id: int = Field(..., description="ID of the stage")
    name: str = Field(..., description="Name of the stage")


class AssignMediaInput(BaseModel):
    id: int = Field(..., description="ID of the stage")
    mediaIds: Optional[list[int]] = Field([], description="List of media IDs")


class UploadMediaInput(BaseModel):
    name: str = Field(..., description="Name of the media")
    base64: str = Field(..., description="Base64 encoded media")
    mediaType: str = Field(..., description="Type of the media")
    filename: str = Field(..., description="Name of the file")


class UpdateMediaInput(BaseModel):
    id: int = Field(..., description="ID of the media")
    name: str = Field(..., description="Name of the media")
    mediaType: Optional[str] = Field(None, description="Type of the media")
    description: Optional[str] = Field(None, description="Description of the media")
    fileLocation: Optional[str] = Field(None, description="Location of the file")
    base64: Optional[str] = Field(None, description="Base64 encoded media")
    copyrightLevel: Optional[int] = Field(None, description="Copyright level")
    playerAccess: Optional[str] = Field(None, description="Player access information")
    uploadedFrames: Optional[list[str]] = Field(
        [], description="List of uploaded frames"
    )


class AssignStagesInput(BaseModel):
    id: int = Field(..., description="ID of the stage")
    stageIds: Optional[list[int]] = Field([], description="List of stage IDs")


class SceneInput(BaseModel):
    name: Optional[str] = Field(None, description="Name of the scene")
    preview: str = Field(..., description="Preview of the scene")
    payload: str = Field(..., description="Payload of the scene")
    stageId: int = Field(..., description="ID of the stage")


class PerformanceInput(BaseModel):
    id: int = Field(..., description="ID of the performance")
    name: str = Field(..., description="Name of the performance")
    description: Optional[str] = Field(
        None, description="Description of the performance"
    )


class RecordInput(BaseModel):
    stageId: int = Field(..., description="ID of the stage")
    name: str = Field(..., description="Name of the performance")
    description: Optional[str] = Field(
        None, description="Description of the performance"
    )


class DuplicatePerformanceInput(BaseModel):
    sourceId: int = Field(..., description="ID of the performance to copy")
    name: str = Field(..., description="Name for the new performance")
    description: Optional[str] = Field(
        None, description="Description for the new performance"
    )


class EventInput(BaseModel):
    topic: str = Field(..., description="Event MQTT topic")
    mqttTimestamp: float = Field(..., description="Event timestamp")
    payload: Optional[Any] = Field(default=None, description="Event payload (JSON)")


class SavePerformanceInput(BaseModel):
    """Save a performance with the given events. Replace existing if performanceId set, else create new (requires stageId)."""
    performanceId: Optional[int] = Field(None, description="If set, replace this performance's events and update name/description")
    stageId: Optional[int] = Field(None, description="Required when creating new performance (no performanceId)")
    name: str = Field(..., description="Performance name")
    description: Optional[str] = Field(None, description="Performance description")
    events: List[EventInput] = Field(..., description="Events to save (e.g. compressed replay events)")


class CreatePerformanceWithEventsInput(BaseModel):
    """Create a new performance with the given events (e.g. compressed replay)."""
    stageId: int = Field(..., description="Stage to attach the performance to")
    name: str = Field(..., description="Performance name")
    description: Optional[str] = Field(None, description="Performance description")
    events: List[EventInput] = Field(..., description="Events to save")


class SearchStageInput(BaseModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    page: Optional[conint(ge=1)] = Field(
        1, description="Page number, must be greater than or equal to 1"
    )
    limit: Optional[conint(ge=1)] = Field(
        10, description="Number of items per page, must be greater than or equal to 1"
    )
    sort: Optional[List[str]] = Field(
        None,
        description="Sort options, must be one of 'OWNER_ID_ASC', 'OWNER_ID_DESC', 'NAME_ASC', 'NAME_DESC', 'CREATED_ON_ASC', 'CREATED_ON_DESC'",
    )
    name: Optional[str] = Field(None, description="Name filter")
    owners: Optional[List[str]] = Field(None, description="List of owners")
    createdBetween: Optional[List[date]] = Field(
        None, description="List of two dates representing the created date range"
    )
    access: Optional[List[str]] = Field(None, description="List of access")


class StageStreamInput(BaseModel):
    fileLocation: Optional[str] = Field(None, description="Location of the file")
    performanceId: Optional[int] = Field(None, description="ID of the performance")
    cursor: Optional[int] = Field(None, description="Cursor for pagination")
