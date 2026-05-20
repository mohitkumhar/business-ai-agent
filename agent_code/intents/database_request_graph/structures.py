from typing import Literal, Optional

from pydantic import BaseModel, Field


class DateRangeOutput(BaseModel):
    start_date: Optional[str] = Field(
        None, description="Start date YYYY-MM-DD or null"
    )
    end_date: Optional[str] = Field(
        None, description="End date YYYY-MM-DD or null"
    )
    description: str = Field(
        description="Human-readable description of the resolved range"
    )

class EntityExtractionOutput(BaseModel):
    tables: list[str] = Field(
        description="Database table names the query needs"
    )
    columns: list[str] = Field(
        default_factory=list,
        description="Specific column names referenced (if any)",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Extraction confidence"
    )
    ambiguous_tables: list[str] = Field(
        default_factory=list,
        description="Tables where intent is unclear",
    )

class SQLGenerationOutput(BaseModel):
    sql_query: str = Field(description="The generated SQL SELECT query")
    explanation: str = Field(description="What the query does")

class SQLValidationOutput(BaseModel):
    is_valid: bool = Field(description="Whether the SQL is valid and safe")
    issues: list[str] = Field(
        default_factory=list, description="Issues found"
    )
    corrected_sql: Optional[str] = Field(
        None, description="Corrected SQL if fixable"
    )

class BusinessInsightOutput(BaseModel):
    summary: str = Field(description="Executive summary")
    key_metrics: list[str] = Field(default_factory=list)
    trends: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
