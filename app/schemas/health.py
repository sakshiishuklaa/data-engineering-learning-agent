"""Schemas for system health reporting."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    environment: str
