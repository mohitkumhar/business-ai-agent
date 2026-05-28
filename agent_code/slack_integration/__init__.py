"""Slack Events API, Block Kit replies, demo-channel posting with DM fallback, and assignee DMs."""

from slack_integration.smart_assigner import (
    should_notify_assignee,
    pick_assignee_slack_id,
    parse_business_envelope,
)

try:
    from slack_integration.slack_handler import SlackDelivery
except ModuleNotFoundError as exc:
    if exc.name != "slack_sdk":
        raise
    SlackDelivery = None

__all__ = [
    "SlackDelivery",
    "should_notify_assignee",
    "pick_assignee_slack_id",
    "parse_business_envelope",
]
