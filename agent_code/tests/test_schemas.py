import pytest
from pydantic import ValidationError
from schemas.responses import (
    AgentResponseSchema,
    FinancialAnalysisSchema,
    DataInsightSchema,
    IntentDetectionSchema,
)

def test_agent_response_schema_valid():
    data = {
        "query_understood": "Show me revenue",
        "summary": "Revenue was $1000",
        "recommendations": ["Reduce costs", "Increase sales"],
        "risk_level": "low",
        "follow_up_questions": ["What about last month?"]
    }
    schema = AgentResponseSchema(**data)
    assert schema.query_understood == data["query_understood"]
    assert schema.summary == data["summary"]
    assert len(schema.recommendations) == 2

def test_agent_response_schema_invalid_risk():
    data = {
        "query_understood": "Show me revenue",
        "summary": "Revenue was $1000",
        "risk_level": "very high"  # Invalid literal
    }
    with pytest.raises(ValidationError):
        AgentResponseSchema(**data)

def test_financial_analysis_schema():
    data = {
        "query_understood": "Can I afford a loan?",
        "summary": "Yes, you can.",
        "runway_analysis": "Your runway is 12 months.",
        "recommendations": ["Apply for SBI loan"],
        "follow_up_questions": []
    }
    schema = FinancialAnalysisSchema(**data)
    assert schema.runway_analysis == data["runway_analysis"]

def test_intent_detection_schema():
    data = {
        "intent": ["database_request", "advisory_request"]
    }
    schema = IntentDetectionSchema(**data)
    assert schema.intent == ["database_request", "advisory_request"]

def test_data_insight_schema():
    data = {
        "summary": "Inventory is low",
        "key_metrics": ["Stock: 5"],
        "trends": ["Decreasing"],
        "recommendations": ["Reorder"],
        "risk_flags": ["Out of stock soon"]
    }
    schema = DataInsightSchema(**data)
    assert schema.summary == data["summary"]
    assert "Stock: 5" in schema.key_metrics
