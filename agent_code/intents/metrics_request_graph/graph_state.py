from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class MetricsRequestGraphState(TypedDict):
    # input
    user_query: str
    messages: Annotated[list, add_messages]

    # parse_metrics_query
    metric_names: list[str]
    promql_queries: list[str]
    lookback_minutes: int
    step_seconds: int
    time_range_description: str

    # fetch_metrics
    raw_metrics: str            # JSON string of Prometheus query results
    fetch_error: str
    has_results: bool

    # analyze_metrics
    metrics_analysis: str       # JSON string of MetricsAnalysisOutput

    # format_response
    formatted_response: str
