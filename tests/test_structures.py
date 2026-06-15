from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent_code.intents.database_request_graph.structures import (
    DateRangeOutput,
    EntityExtractionOutput,
    SQLGenerationOutput,
    SQLValidationOutput,
    BusinessInsightOutput,
)


# ── Tests for DateRangeOutput ───────────────────────────────────────

def test_daterange_output_valid_all_fields():
    """Validates instantiation when all fields are provided."""
    model = DateRangeOutput(
        start_date="2026-01-01",
        end_date="2026-01-31",
        description="January 2026"
    )
    assert model.start_date == "2026-01-01"
    assert model.end_date == "2026-01-31"
    assert model.description == "January 2026"


def test_daterange_output_valid_minimal():
    """Validates instantiation when only the required field description is provided."""
    model = DateRangeOutput(description="No specific range")
    assert model.start_date is None
    assert model.end_date is None
    assert model.description == "No specific range"


def test_daterange_output_missing_required():
    """Verifies ValidationError is raised when description is missing."""
    with pytest.raises(ValidationError):
        # description is a required field (no default value)
        DateRangeOutput(start_date="2026-01-01")


def test_daterange_output_empty_dates():
    """Tests that empty strings are accepted for dates."""
    model = DateRangeOutput(
        start_date="",
        end_date="",
        description="Empty dates description"
    )
    assert model.start_date == ""
    assert model.end_date == ""
    assert model.description == "Empty dates description"


def test_daterange_output_serialization():
    """Tests dict/json serialization and deserialization."""
    data = {
        "start_date": "2026-06-01",
        "end_date": "2026-06-07",
        "description": "First week of June"
    }
    model = DateRangeOutput(**data)
    
    # Dump to dict
    model_dict = model.model_dump()
    assert model_dict == data
    
    # Dump to json
    model_json = model.model_dump_json()
    assert '"start_date":"2026-06-01"' in model_json
    assert '"description":"First week of June"' in model_json
    
    # Validate from dict
    validated = DateRangeOutput.model_validate(model_dict)
    assert validated.start_date == "2026-06-01"
    assert validated.description == "First week of June"


# ── Tests for EntityExtractionOutput ────────────────────────────────

def test_entity_extraction_output_valid_all_fields():
    """Validates all fields are correctly stored."""
    model = EntityExtractionOutput(
        tables=["users", "orders"],
        columns=["id", "created_at", "total"],
        confidence="high",
        ambiguous_tables=["profiles"]
    )
    assert model.tables == ["users", "orders"]
    assert model.columns == ["id", "created_at", "total"]
    assert model.confidence == "high"
    assert model.ambiguous_tables == ["profiles"]


def test_entity_extraction_output_valid_minimal():
    """Validates default values for columns and ambiguous_tables when not supplied."""
    model = EntityExtractionOutput(
        tables=["users"],
        confidence="medium"
    )
    assert model.tables == ["users"]
    assert model.columns == []
    assert model.confidence == "medium"
    assert model.ambiguous_tables == []


def test_entity_extraction_output_missing_required():
    """Verifies validation errors on missing tables or confidence."""
    with pytest.raises(ValidationError):
        # tables is missing
        EntityExtractionOutput(confidence="low")
        
    with pytest.raises(ValidationError):
        # confidence is missing
        EntityExtractionOutput(tables=["users"])


def test_entity_extraction_output_invalid_confidence():
    """Verifies that confidence must belong to ('high', 'medium', 'low')."""
    with pytest.raises(ValidationError):
        EntityExtractionOutput(tables=["users"], confidence="very_high")

    with pytest.raises(ValidationError):
        EntityExtractionOutput(tables=["users"], confidence="")


def test_entity_extraction_output_serialization():
    """Tests serialization and deserialization."""
    model = EntityExtractionOutput(
        tables=["users"],
        columns=["name"],
        confidence="low"
    )
    dumped = model.model_dump()
    assert dumped["tables"] == ["users"]
    assert dumped["columns"] == ["name"]
    assert dumped["confidence"] == "low"
    assert dumped["ambiguous_tables"] == []
    
    validated = EntityExtractionOutput.model_validate(dumped)
    assert validated.tables == ["users"]
    assert validated.confidence == "low"


# ── Tests for SQLGenerationOutput ───────────────────────────────────

def test_sql_generation_output_valid():
    """Validates correct instantiation."""
    query = "SELECT name FROM users WHERE id = 1;"
    explanation = "Retrieve name of user with id 1."
    model = SQLGenerationOutput(sql_query=query, explanation=explanation)
    assert model.sql_query == query
    assert model.explanation == explanation


def test_sql_generation_output_missing_required():
    """Verifies that missing sql_query or explanation raises validation error."""
    with pytest.raises(ValidationError):
        SQLGenerationOutput(sql_query="SELECT 1;")
        
    with pytest.raises(ValidationError):
        SQLGenerationOutput(explanation="Select one")


def test_sql_generation_output_serialization():
    """Tests serialization and deserialization."""
    model = SQLGenerationOutput(sql_query="SELECT 1;", explanation="Simple select")
    dumped = model.model_dump()
    assert dumped == {"sql_query": "SELECT 1;", "explanation": "Simple select"}
    
    validated = SQLGenerationOutput.model_validate(dumped)
    assert validated.sql_query == "SELECT 1;"


# ── Tests for SQLValidationOutput ───────────────────────────────────

def test_sql_validation_output_valid_all_fields():
    """Validates instantiation with all fields."""
    model = SQLValidationOutput(
        is_valid=False,
        issues=["SQL injection pattern detected"],
        corrected_sql="SELECT * FROM users;"
    )
    assert model.is_valid is False
    assert model.issues == ["SQL injection pattern detected"]
    assert model.corrected_sql == "SELECT * FROM users;"


def test_sql_validation_output_valid_minimal():
    """Validates defaults for issues and corrected_sql."""
    model = SQLValidationOutput(is_valid=True)
    assert model.is_valid is True
    assert model.issues == []
    assert model.corrected_sql is None


def test_sql_validation_output_missing_required():
    """Verifies that is_valid is required."""
    with pytest.raises(ValidationError):
        SQLValidationOutput(issues=[])


def test_sql_validation_output_serialization():
    """Tests serialization and deserialization."""
    model = SQLValidationOutput(is_valid=True)
    dumped = model.model_dump()
    assert dumped == {"is_valid": True, "issues": [], "corrected_sql": None}
    
    validated = SQLValidationOutput.model_validate(dumped)
    assert validated.is_valid is True


# ── Tests for BusinessInsightOutput ─────────────────────────────────

def test_business_insight_output_valid_all_fields():
    """Validates instantiation with all fields."""
    model = BusinessInsightOutput(
        summary="Growth is strong",
        key_metrics=["MRR: $10k"],
        trends=["Upward trend in sales"],
        recommendations=["Increase ad spend"],
        risk_flags=["High churn in Tier 2"]
    )
    assert model.summary == "Growth is strong"
    assert model.key_metrics == ["MRR: $10k"]
    assert model.trends == ["Upward trend in sales"]
    assert model.recommendations == ["Increase ad spend"]
    assert model.risk_flags == ["High churn in Tier 2"]


def test_business_insight_output_valid_minimal():
    """Validates defaults for lists when not supplied."""
    model = BusinessInsightOutput(summary="Minimal summary")
    assert model.summary == "Minimal summary"
    assert model.key_metrics == []
    assert model.trends == []
    assert model.recommendations == []
    assert model.risk_flags == []


def test_business_insight_output_missing_required():
    """Verifies that summary is required."""
    with pytest.raises(ValidationError):
        BusinessInsightOutput(key_metrics=[])


def test_business_insight_output_serialization():
    """Tests serialization and deserialization."""
    model = BusinessInsightOutput(summary="Test summary", key_metrics=["metric"])
    dumped = model.model_dump()
    assert dumped["summary"] == "Test summary"
    assert dumped["key_metrics"] == ["metric"]
    assert dumped["trends"] == []
    
    validated = BusinessInsightOutput.model_validate(dumped)
    assert validated.summary == "Test summary"
    assert validated.key_metrics == ["metric"]
