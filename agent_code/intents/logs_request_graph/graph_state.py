from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class LogsRequestGraphState(TypedDict):
    # input
    user_query: str
    messages: Annotated[list, add_messages]

    # parse_logs_query
    log_query: str                  # LogQL expression
    lookback_minutes: int
    limit: int
    time_range_description: str
    search_keywords: list[str]

    # fetch_logs
    raw_logs: str                   # newline-joined log lines (plain text)
    fetch_error: str
    has_results: bool
    log_line_count: int

    # analyze_logs
    logs_analysis: str              # JSON string of LogsAnalysisOutput

    # format_response
    formatted_response: str
