from pydantic import BaseModel, ValidationError
import pytest


class DemoSchema(BaseModel):
    summary: str
    recommendations: list[str]


def test_valid_schema():
    obj = DemoSchema(
        summary="Revenue increased",
        recommendations=["Increase marketing"],
    )

    assert obj.summary == "Revenue increased"


def test_missing_required_field():
    with pytest.raises(ValidationError):
        DemoSchema(
            recommendations=["Increase marketing"]
        )