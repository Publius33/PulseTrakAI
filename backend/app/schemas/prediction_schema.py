"""
Prediction API Schema Validation for PulseTrakAI™

Pydantic models for prediction requests/responses:
- Input feature validation
- Output bounds checking
- Confidence score validation

© PUBLIUS33™ — PulseTrakAI™ — All Rights Reserved.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PredictionType(str, Enum):
    """Types of predictions."""
    ANOMALY = "anomaly"
    FORECAST = "forecast"
    RECOMMENDATION = "recommendation"


class PredictionRequestSchema(BaseModel):
    """Schema for prediction requests to /api/pulse-horizon."""
    
    metric_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Name of metric to predict"
    )
    
    features: List[float] = Field(
        ...,
        min_items=1,
        max_items=1000,
        description="Input features (max 1000 values)"
    )
    
    prediction_type: Optional[PredictionType] = Field(
        default=PredictionType.ANOMALY,
        description="Type of prediction"
    )
    
    lookback_hours: Optional[int] = Field(
        default=24,
        ge=1,
        le=8760,
        description="Historical data window in hours (1-365 days)"
    )
    
    tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Additional context"
    )
    
    class Config:
        extra = "forbid"
    
    @validator("features")
    def validate_features(cls, v):
        """Validate feature values are numeric."""
        for f in v:
            if not isinstance(f, (int, float)):
                raise ValueError("All features must be numeric")
            if f < -1e10 or f > 1e10:
                raise ValueError(f"Feature value {f} out of bounds")
        return v


class AnomalyPredictionSchema(BaseModel):
    """Schema for anomaly detection prediction response."""
    
    is_anomaly: bool = Field(
        description="Whether input is detected as anomaly"
    )
    
    anomaly_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Anomaly score (0-1, higher = more anomalous)"
    )
    
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Prediction confidence"
    )
    
    threshold: float = Field(
        ge=0.0,
        le=1.0,
        description="Decision threshold used"
    )
    
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable explanation"
    )
    
    generated_at: datetime = Field(
        description="When prediction was generated"
    )
    
    model_version: int = Field(
        description="Which model version made prediction"
    )
    
    latency_ms: float = Field(
        ge=0,
        description="Prediction latency in milliseconds"
    )


class ForecastPredictionSchema(BaseModel):
    """Schema for forecast prediction response."""
    
    forecast_values: List[float] = Field(
        ...,
        min_items=1,
        max_items=365,
        description="Forecasted values"
    )
    
    forecast_timestamps: List[datetime] = Field(
        ...,
        min_items=1,
        max_items=365,
        description="Timestamps for forecast"
    )
    
    confidence_lower: List[float] = Field(
        description="Lower confidence bound"
    )
    
    confidence_upper: List[float] = Field(
        description="Upper confidence bound"
    )
    
    mae: Optional[float] = Field(
        default=None,
        ge=0,
        description="Mean Absolute Error on validation set"
    )
    
    generated_at: datetime = Field(
        description="When forecast was generated"
    )
    
    model_version: int = Field(
        description="Which model version made forecast"
    )


class PredictionResponseSchema(BaseModel):
    """Unified prediction response."""
    
    request_id: str = Field(
        description="Unique request identifier"
    )
    
    status: str = Field(
        description="Success or error"
    )
    
    prediction: Optional[Dict] = Field(
        default=None,
        description="Prediction result (type depends on prediction_type)"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if status=error"
    )
    
    generated_at: datetime = Field(
        description="Response timestamp"
    )


class BatchPredictionRequestSchema(BaseModel):
    """Schema for batch prediction requests."""
    
    requests: List[PredictionRequestSchema] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="Up to 100 prediction requests"
    )
    
    class Config:
        extra = "forbid"
