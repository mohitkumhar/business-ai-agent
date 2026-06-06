from __future__ import annotations

from typing import Any, List, Literal, Optional, Dict

from pydantic import BaseModel, Field


class AgentResponseSchema(BaseModel):
    """Base schema for standard agent responses to the user."""
    query_understood: str = Field(
        description="A concise, professional restatement of the user's request to confirm understanding."
    )
    summary: str = Field(
        description="The primary answer or insight, usually 1-3 sentences. This is the main 'result' section."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="A list of 2-5 specific, actionable business recommendations derived from the data or query."
    )
    risk_level: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="A qualitative assessment of business risk associated with the query or findings."
    )
    follow_up_questions: List[str] = Field(
        default_factory=list,
        description="1-3 suggested questions the user might want to ask next to dive deeper."
    )


class FinancialAnalysisSchema(AgentResponseSchema):
    """Schema for deep financial analysis and advisory nodes."""
    runway_analysis: Optional[str] = Field(
        default=None,
        description="1-2 sentences on business runway or affordability if financial data allows."
    )


class DataInsightSchema(BaseModel):
    """Schema used internally by nodes that generate insights from raw query results."""
    summary: str = Field(description="Concise summary of the data findings.")
    key_metrics: List[str] = Field(default_factory=list, description="Key numbers found.")
    trends: List[str] = Field(default_factory=list, description="Notable patterns.")
    recommendations: List[str] = Field(default_factory=list, description="Actionable steps.")
    risk_flags: List[str] = Field(
        default_factory=list, 
        description="Identified anomalies, missing data, or negative trends."
    )


class DateRangeSchema(BaseModel):
    """Schema for date range extraction."""
    start_date: Optional[str] = Field(None, description="Start date YYYY-MM-DD or null")
    end_date: Optional[str] = Field(None, description="End date YYYY-MM-DD or null")
    description: str = Field(description="Human-readable description of the resolved range")


class EntityExtractionSchema(BaseModel):
    """Schema for entity and table extraction."""
    tables: List[str] = Field(description="Database table names the query needs")
    columns: List[str] = Field(default_factory=list, description="Specific column names referenced")
    confidence: Literal["high", "medium", "low"] = Field(description="Extraction confidence")
    ambiguous_tables: List[str] = Field(default_factory=list, description="Tables where intent is unclear")


class SQLGenerationSchema(BaseModel):
    """Schema for SQL query generation."""
    sql_query: str = Field(description="The generated SQL SELECT query")
    explanation: str = Field(description="What the query does")


class SQLValidationSchema(BaseModel):
    """Schema for SQL validation results."""
    is_valid: bool = Field(description="Whether the SQL is valid and safe")
    issues: List[str] = Field(default_factory=list, description="Issues found")
    corrected_sql: Optional[str] = Field(None, description="Corrected SQL if fixable")


class IntentDetectionSchema(BaseModel):
    """Schema for intent detection ordering."""
    intent: List[
        Literal[
            "greeting_request",
            "database_request",
            "advisory_request",
            "hybrid_request",
            "out_of_scope_request",
            "general_information_request",
            "logs_request",
            "metrics_request",
        ]
    ] = Field(
        description=(
            "Ordered intents: usually ONE. For compound questions, order data → general → advisory. "
            "Casual hellos are greeting_request, NEVER out_of_scope."
        )
    )


class WebSearchSchema(BaseModel):
    """Schema for determining if a web search is needed."""
    is_web_search_required: Literal["yes", "no"] = Field(
        description="Is Web search is required to answer the asked question by user"
    )


class LogsQueryParseSchema(BaseModel):
    """Schema for parsing log queries."""
    log_query: str = Field(description="Loki LogQL expression")
    lookback_minutes: int = Field(default=60)
    limit: int = Field(default=100)
    time_range_description: str
    search_keywords: List[str] = Field(default_factory=list)


class LogsAnalysisSchema(BaseModel):
    """Schema for log analysis results."""
    summary: str
    error_count: int
    warning_count: int
    key_events: List[str] = Field(default_factory=list)
    recurring_patterns: List[str] = Field(default_factory=list)
    anomalies: List[str] = Field(default_factory=list)
    health_assessment: Literal["healthy", "degraded", "critical", "unknown"]
    recommended_actions: List[str] = Field(default_factory=list)


class MetricsQueryParseSchema(BaseModel):
    """Schema for parsing metrics queries."""
    metric_names: List[str] = Field(description="Prometheus metric names")
    promql_queries: List[str] = Field(description="PromQL expressions")
    lookback_minutes: int = Field(default=60)
    step_seconds: int = Field(default=15)
    time_range_description: str


class MetricsAnalysisSchema(BaseModel):
    """Schema for metrics analysis results."""
    summary: str
    current_values: Dict[str, str] = Field(default_factory=dict)
    trends: List[str] = Field(default_factory=list)
    anomalies: List[str] = Field(default_factory=list)
    health_assessment: Literal["healthy", "degraded", "critical", "unknown"]
    recommended_actions: List[str] = Field(default_factory=list)
