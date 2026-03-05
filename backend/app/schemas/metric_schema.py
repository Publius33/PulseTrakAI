"""
Metric API Schema Validation for PulseTrakAI™

Pydantic models for metric submission validation:
- Max payload sizes
- Numeric bounds
- Timestamp validation
- Reject unknown fields

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class MetricEventSchema(BaseModel):
    """Schema for metric events submitted to /api/metrics."""
    
    metric_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Name of the metric (e.g., cpu_usage, memory_usage)"
    )
    
    value: float = Field(
        ...,
        ge=-1e10,
        le=1e10,
        description="Numeric value for the metric"
    )
    
    source: str = Field(
        default="unknown",
        min_length=1,
        max_length=256,
        description="Source service or host"
    )
    
    timestamp: Optional[datetime] = Field(
        default=None,
        description="Event timestamp (defaults to now)"
    )
    
    tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional metadata (max 10 key-value pairs)"
    )
    
    class Config:
        extra = "forbid"  # Reject unknown fields
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    @validator("metric_name")
    def validate_metric_name(cls, v):
        """Validate metric name format."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Metric name can only contain alphanumeric, underscore, and hyphen")
        return v.lower()
    
    @validator("timestamp")
    def validate_timestamp(cls, v):
        """Ensure timestamp not in future."""
        if v and v > datetime.utcnow():
            raise ValueError("Timestamp cannot be in future")
        return v or datetime.utcnow()
    
    @validator("tags")
    def validate_tags(cls, v):
        """Limit tags to 10 key-value pairs."""
        if v and len(v) > 10:
            raise ValueError("Maximum 10 tags allowed")
        return v


class MetricsPayloadSchema(BaseModel):
    """Schema for batch metric submissions."""
    
    metrics: list = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="List of metric events (max 1000)"
    )
    
    class Config:
        extra = "forbid"


class MetricQuerySchema(BaseModel):
    """Schema for metric queries."""
    
    metric_name: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Filter by metric name"
    )
    
    source: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Filter by source"
    )
    
    start_time: Optional[datetime] = Field(
        default=None,
        description="Start of time range"
    )
    
    end_time: Optional[datetime] = Field(
        default=None,
        description="End of time range"
    )
    
    limit: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Max results to return"
    )
    
    class Config:
        extra = "forbid"
