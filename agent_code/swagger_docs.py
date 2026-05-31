from __future__ import annotations

from typing import Any

from flasgger import Swagger, swag_from


SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec_1",
            "route": "/apispec_1.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/apidocs/",
}

SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "ProfitPilot Flask API",
        "description": (
            "Interactive Swagger documentation for the ProfitPilot Flask backend. "
            "Versioned /api/v1 routes are tagged separately from current dashboard, "
            "chat, auth, and system routes."
        ),
        "version": "1.0.0",
    },
    "basePath": "/",
    "schemes": ["http"],
    "consumes": ["application/json"],
    "produces": ["application/json"],
    "tags": [
        {
            "name": "System",
            "description": "Health checks, metrics, and service metadata.",
        },
        {
            "name": "Auth",
            "description": "Signup and login endpoints that issue JWT bearer tokens.",
        },
        {"name": "V1", "description": "Versioned API routes under /api/v1."},
        {"name": "Chat", "description": "SSE-powered agent chat and query routes."},
        {
            "name": "Import",
            "description": "CSV, spreadsheet, and notebook transaction imports.",
        },
        {
            "name": "Dashboard",
            "description": "Authenticated dashboard analytics and filters.",
        },
    ],
    "securityDefinitions": {
        "BearerAuth": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Use a JWT bearer token, for example: Bearer <token>",
        }
    },
    "definitions": {
        "ErrorResponse": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "example": "Authorization header is required",
                },
                "error": {"type": "string", "example": "Invalid request payload"},
                "is_error": {"type": "boolean", "example": True},
            },
        },
        "UserProfile": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "example": "Asha Patel"},
                "email": {"type": "string", "example": "owner@example.com"},
            },
        },
        "AuthResponse": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                },
                "business_id": {
                    "type": "string",
                    "example": "550e8400-e29b-41d4-a716-446655440000",
                },
                "user": {"$ref": "#/definitions/UserProfile"},
            },
        },
        "SignupRequest": {
            "type": "object",
            "required": ["email", "password", "name", "business_name"],
            "properties": {
                "email": {"type": "string", "example": "owner@example.com"},
                "password": {"type": "string", "example": "secret123"},
                "name": {"type": "string", "example": "Asha Patel"},
                "business_name": {"type": "string", "example": "Pilot Store"},
                "industry": {"type": "string", "example": "Retail"},
            },
            "example": {
                "email": "owner@example.com",
                "password": "secret123",
                "name": "Asha Patel",
                "business_name": "Pilot Store",
                "industry": "Retail",
            },
        },
        "LoginRequest": {
            "type": "object",
            "required": ["email", "password"],
            "properties": {
                "email": {"type": "string", "example": "owner@example.com"},
                "password": {"type": "string", "example": "secret123"},
            },
            "example": {"email": "owner@example.com", "password": "secret123"},
        },
        "OnboardingRequest": {
            "type": "object",
            "required": ["business_name", "email"],
            "properties": {
                "business_name": {"type": "string", "example": "Pilot Store"},
                "business_category": {"type": "string", "example": "Retail"},
                "full_name": {"type": "string", "example": "Asha Patel"},
                "email": {"type": "string", "example": "owner@example.com"},
            },
            "example": {
                "business_name": "Pilot Store",
                "business_category": "Retail",
                "full_name": "Asha Patel",
                "email": "owner@example.com",
            },
        },
        "OnboardingResponse": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean", "example": True},
                "business_id": {
                    "type": "string",
                    "example": "550e8400-e29b-41d4-a716-446655440000",
                },
            },
        },
        "ChatRequest": {
            "type": "object",
            "required": ["message"],
            "properties": {
                "message": {"type": "string", "example": "Show this month revenue"},
                "conversation_id": {"type": "string", "example": "conv-2026-05-30"},
            },
            "example": {
                "message": "Show this month revenue",
                "conversation_id": "conv-2026-05-30",
            },
        },
        "ImportConfirmRequest": {
            "type": "object",
            "required": ["transactions", "hash"],
            "properties": {
                "hash": {
                    "type": "string",
                    "example": "5eb63bbbe01eeed093cb22bb8f5acdc3",
                },
                "transactions": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/TransactionInput"},
                },
            },
            "example": {
                "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
                "transactions": [
                    {
                        "date": "2026-05-20",
                        "type": "Revenue",
                        "category": "Sales",
                        "amount": 1250.0,
                        "description": "Counter sale",
                    }
                ],
            },
        },
        "TransactionInput": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "format": "date", "example": "2026-05-20"},
                "type": {
                    "type": "string",
                    "enum": ["Revenue", "Expense"],
                    "example": "Revenue",
                },
                "category": {"type": "string", "example": "Sales"},
                "amount": {"type": "number", "format": "float", "example": 1250.0},
                "description": {"type": "string", "example": "Counter sale"},
            },
        },
        "TransactionPreview": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/TransactionInput"},
                },
                "hash": {
                    "type": "string",
                    "example": "5eb63bbbe01eeed093cb22bb8f5acdc3",
                },
            },
        },
        "MessageResponse": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "example": "Successfully imported 3 transactions!",
                }
            },
        },
        "RootResponse": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "example": "healthy"},
                "service": {"type": "string", "example": "ProfitPilot Backend"},
                "version": {"type": "string", "example": "1.0.0"},
            },
        },
        "HealthResponse": {
            "type": "object",
            "properties": {"status": {"type": "string", "example": "ok"}},
        },
        "DashboardSummary": {
            "type": "object",
            "properties": {
                "total_revenue": {"type": "number", "example": 15000.0},
                "total_expenses": {"type": "number", "example": 9000.0},
                "net_profit": {"type": "number", "example": 6000.0},
                "total_transactions": {"type": "integer", "example": 48},
                "active_alerts": {"type": "integer", "example": 3},
                "revenue_change": {"type": "number", "example": 12.5},
                "expenses_change": {"type": "number", "example": -3.0},
                "net_profit_change": {"type": "number", "example": 18.4},
                "transactions_change": {"type": "number", "example": 7.2},
            },
        },
        "CategoriesResponse": {
            "type": "object",
            "properties": {
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["Sales", "Rent", "Utilities"],
                }
            },
        },
        "FinancialOverview": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["2026-04", "2026-05"],
                },
                "revenue": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [12000, 15000],
                },
                "expenses": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [8000, 9000],
                },
                "net_profit": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [4000, 6000],
                },
                "cash_balance": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [25000, 31000],
                },
            },
        },
        "ForecastResponse": {
            "type": "object",
            "properties": {
                "historical": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "example": "2026-05-01"},
                            "actual": {"type": "number", "example": 1250.0},
                        },
                    },
                },
                "forecast": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "example": "2026-05-31"},
                            "predicted": {"type": "number", "example": 1425.0},
                        },
                    },
                },
                "trend_direction": {"type": "string", "example": "up"},
                "trend_percent": {"type": "number", "example": 7.5},
                "insight": {
                    "type": "string",
                    "example": "Revenue is trending upwards based on recent data.",
                },
            },
        },
        "RevenueExpenseSeries": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["Sales", "Rent"],
                },
                "revenue": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [15000, 0],
                },
                "expenses": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [0, 5000],
                },
            },
        },
        "RecentTransactionsResponse": {
            "type": "object",
            "properties": {
                "transactions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "transaction_id": {"type": "integer", "example": 7},
                            "transaction_date": {
                                "type": "string",
                                "format": "date",
                                "example": "2026-05-20",
                            },
                            "type": {"type": "string", "example": "Revenue"},
                            "category": {"type": "string", "example": "Sales"},
                            "amount": {"type": "number", "example": 1250.5},
                            "description": {
                                "type": "string",
                                "example": "May invoice",
                            },
                        },
                    },
                }
            },
        },
        "AlertsListResponse": {
            "type": "object",
            "properties": {
                "alerts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "alert_id": {"type": "integer", "example": 3},
                            "message": {
                                "type": "string",
                                "example": "Expenses exceeded monthly threshold.",
                            },
                            "severity": {"type": "string", "example": "High"},
                            "status": {"type": "string", "example": "Active"},
                            "created_at": {
                                "type": "string",
                                "example": "2026-05-20 09:30",
                            },
                        },
                    },
                }
            },
        },
        "BusinessInfoResponse": {
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "business_id": {
                    "type": "string",
                    "example": "550e8400-e29b-41d4-a716-446655440000",
                },
                "business_name": {"type": "string", "example": "Pilot Store"},
                "industry_type": {"type": "string", "example": "Retail"},
                "owner_name": {"type": "string", "example": "Asha Patel"},
            },
        },
        "SalesTargetResponse": {
            "type": "object",
            "properties": {
                "current_revenue": {"type": "number", "example": 42000.0},
                "target_revenue": {"type": "number", "example": 100000.0},
                "percentage": {"type": "number", "example": 42.0},
            },
        },
        "SeverityChartResponse": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["High", "Low"],
                },
                "data": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "example": [2, 1],
                },
            },
        },
        "HealthScoresResponse": {
            "type": "object",
            "properties": {
                "businesses": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["Pilot Store"],
                },
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "example": "Pilot Store"},
                            "overall": {"type": "number", "example": 82.5},
                            "cash": {"type": "number", "example": 78.0},
                            "profitability": {"type": "number", "example": 88.0},
                            "growth": {"type": "number", "example": 75.0},
                            "cost_control": {"type": "number", "example": 84.0},
                            "risk": {"type": "number", "example": 20.0},
                        },
                    },
                },
            },
        },
        "TopProductsResponse": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["Notebook", "Pen"],
                },
                "stock": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "example": [120, 300],
                },
                "margin": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [35.5, 42.0],
                },
                "margin_amount": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [35.5, 4.2],
                },
                "margin_pct": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [35.5, 42.0],
                },
            },
        },
        "EmployeeStatsResponse": {
            "type": "object",
            "properties": {
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "example": ["Active", "Inactive"],
                },
                "counts": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "example": [8, 1],
                },
                "avg_salary": {
                    "type": "array",
                    "items": {"type": "number"},
                    "example": [45000.0, 0.0],
                },
            },
        },
        "WebhookOkResponse": {
            "type": "object",
            "properties": {"ok": {"type": "boolean", "example": True}},
        },
    },
}


def _json_body(schema_ref: str, description: str) -> dict[str, Any]:
    schema: dict[str, Any] = {"$ref": schema_ref}
    if schema_ref in BODY_EXAMPLES:
        schema["example"] = BODY_EXAMPLES[schema_ref]

    return {
        "name": "body",
        "in": "body",
        "required": True,
        "description": description,
        "schema": schema,
    }


def _query_param(
    name: str,
    description: str,
    default: str | int | None = None,
    enum: list[str] | None = None,
    param_type: str = "string",
) -> dict[str, Any]:
    param: dict[str, Any] = {
        "name": name,
        "in": "query",
        "required": False,
        "type": param_type,
        "description": description,
    }
    if default is not None:
        param["default"] = default
    if enum:
        param["enum"] = enum
    return param


def _response(
    description: str, schema_ref: str, example: dict[str, Any] | None = None
) -> dict[str, Any]:
    response: dict[str, Any] = {
        "description": description,
        "schema": {"$ref": schema_ref},
    }
    if example is not None:
        response["examples"] = {"application/json": example}
    return response


def _error(description: str, example: dict[str, Any]) -> dict[str, Any]:
    return _response(description, "#/definitions/ErrorResponse", example)


BAD_REQUEST = _error("Invalid or missing request data.", {"error": "Missing fields"})
UNAUTHORIZED = _error(
    "JWT bearer token is missing, malformed, or expired.",
    {"message": "Authorization header is required"},
)
NOT_FOUND = _error("Requested resource was not found.", {"error": "No business found"})
CONFLICT = _error(
    "Request conflicts with an existing resource.", {"message": "User already exists"}
)
INTERNAL_ERROR = _error(
    "Unexpected server error.", {"message": "Internal server error"}
)

PERIOD_PARAMETER = _query_param(
    "period",
    "Dashboard reporting period.",
    default="this_month",
    enum=["this_month", "last_month", "last_7_days", "last_30_days", "all"],
)
LIMIT_PARAMETER = _query_param(
    "limit",
    "Maximum number of records to return.",
    default=20,
    param_type="integer",
)
SEARCH_PARAMETER = _query_param(
    "search",
    "Optional text search over description or category.",
    default="invoice",
)
CATEGORY_PARAMETER = _query_param(
    "category",
    "Optional category filter.",
    default="Sales",
)

PROTECTED = [{"BearerAuth": []}]

BODY_EXAMPLES = {
    "#/definitions/SignupRequest": {
        "email": "owner@example.com",
        "password": "secret123",
        "name": "Asha Patel",
        "business_name": "Pilot Store",
        "industry": "Retail",
    },
    "#/definitions/LoginRequest": {
        "email": "owner@example.com",
        "password": "secret123",
    },
    "#/definitions/OnboardingRequest": {
        "business_name": "Pilot Store",
        "business_category": "Retail",
        "full_name": "Asha Patel",
        "email": "owner@example.com",
    },
    "#/definitions/ChatRequest": {
        "message": "Show this month revenue",
        "conversation_id": "conv-2026-05-30",
    },
    "#/definitions/ImportConfirmRequest": {
        "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
        "transactions": [
            {
                "date": "2026-05-20",
                "type": "Revenue",
                "category": "Sales",
                "amount": 1250.0,
                "description": "Counter sale",
            }
        ],
    },
}

SPECS_BY_ENDPOINT: dict[str, list[dict[str, Any]]] = {
    "home": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["System"],
                "summary": "Backend service metadata",
                "description": "Returns basic service metadata for smoke checks.",
                "responses": {
                    "200": _response(
                        "Service metadata.",
                        "#/definitions/RootResponse",
                        {
                            "status": "healthy",
                            "service": "ProfitPilot Backend",
                            "version": "1.0.0",
                        },
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "health": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["System"],
                "summary": "Health check",
                "description": "Returns a lightweight health signal for uptime checks.",
                "responses": {
                    "200": _response(
                        "Health status.",
                        "#/definitions/HealthResponse",
                        {"status": "ok"},
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "metrics": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["System"],
                "summary": "Prometheus metrics",
                "description": "Exposes Prometheus-formatted process and request metrics.",
                "produces": ["text/plain"],
                "responses": {
                    "200": {
                        "description": "Prometheus metrics text.",
                        "examples": {
                            "text/plain": 'python_info{implementation="CPython"} 1.0\n'
                        },
                    },
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "auth_signup": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["Auth"],
                "summary": "Create an owner account and business",
                "description": "Creates a business, creates its first user, and returns a JWT token.",
                "parameters": [
                    _json_body("#/definitions/SignupRequest", "Signup payload.")
                ],
                "responses": {
                    "201": _response(
                        "Account created.",
                        "#/definitions/AuthResponse",
                        {
                            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "business_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user": {
                                "name": "Asha Patel",
                                "email": "owner@example.com",
                            },
                        },
                    ),
                    "400": BAD_REQUEST,
                    "409": CONFLICT,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "auth_login": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["Auth"],
                "summary": "Log in with email and password",
                "description": "Validates owner credentials and returns a JWT bearer token.",
                "parameters": [
                    _json_body("#/definitions/LoginRequest", "Login credentials.")
                ],
                "responses": {
                    "200": _response(
                        "Authenticated session.",
                        "#/definitions/AuthResponse",
                        {
                            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "business_id": "550e8400-e29b-41d4-a716-446655440000",
                            "user": {
                                "name": "Asha Patel",
                                "email": "owner@example.com",
                            },
                        },
                    ),
                    "400": _error(
                        "Email or password was omitted.",
                        {"message": "Email and password required"},
                    ),
                    "401": _error(
                        "Credentials are invalid.",
                        {"message": "Invalid email or password"},
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "onboarding": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1"],
                "summary": "Create onboarding business record",
                "description": "Versioned onboarding endpoint used by the landing page signup flow.",
                "parameters": [
                    _json_body(
                        "#/definitions/OnboardingRequest", "Business onboarding data."
                    )
                ],
                "responses": {
                    "201": _response(
                        "Business created.",
                        "#/definitions/OnboardingResponse",
                        {
                            "success": True,
                            "business_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    ),
                    "400": BAD_REQUEST,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "whatsapp_verify": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["V1"],
                "summary": "Verify WhatsApp webhook",
                "description": "Handles the Meta webhook verification challenge for WhatsApp integration.",
                "produces": ["text/plain"],
                "parameters": [
                    _query_param(
                        "hub.verify_token",
                        "Verification token configured in WHATSAPP_VERIFY_TOKEN.",
                        default="verify-token",
                    ),
                    _query_param(
                        "hub.challenge",
                        "Challenge string Meta expects the backend to echo.",
                        default="123456789",
                    ),
                ],
                "responses": {
                    "200": {
                        "description": "Challenge accepted and echoed.",
                        "examples": {"text/plain": "123456789"},
                    },
                    "403": {
                        "description": "Verification token did not match.",
                        "examples": {"text/plain": "failed"},
                    },
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "whatsapp_events": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1"],
                "summary": "Receive WhatsApp webhook events",
                "description": "Receives WhatsApp webhook event payloads.",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "required": True,
                        "description": "Meta WhatsApp webhook event payload.",
                        "schema": {
                            "type": "object",
                            "example": {
                                "object": "whatsapp_business_account",
                                "entry": [],
                            },
                        },
                    }
                ],
                "responses": {
                    "200": _response(
                        "Webhook accepted.",
                        "#/definitions/WebhookOkResponse",
                        {"ok": True},
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "telegram_webhook": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1"],
                "summary": "Receive Telegram webhook updates",
                "description": "Receives Telegram updates and replies to text messages through the bot API.",
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "required": True,
                        "description": "Telegram update payload.",
                        "schema": {
                            "type": "object",
                            "example": {
                                "message": {
                                    "chat": {"id": 123456},
                                    "text": "How are sales today?",
                                }
                            },
                        },
                    }
                ],
                "responses": {
                    "200": _response(
                        "Webhook accepted.",
                        "#/definitions/WebhookOkResponse",
                        {"ok": True},
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "query_agent": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1", "Chat"],
                "summary": "Stream an agent response by query parameters",
                "description": "Streams LangGraph agent output as server-sent events for the dashboard proxy.",
                "produces": ["text/event-stream"],
                "parameters": [
                    _query_param(
                        "input-query",
                        "Natural-language question for the agent.",
                        default="What were sales last week?",
                    ),
                    _query_param(
                        "thread-id",
                        "Conversation or thread identifier.",
                        default="dashboard-thread-1",
                    ),
                    _query_param(
                        "business-id",
                        "Business identifier used by the agent data tools.",
                        default="550e8400-e29b-41d4-a716-446655440000",
                    ),
                ],
                "responses": {
                    "200": {
                        "description": "SSE stream of JSON events prefixed with data:.",
                        "examples": {
                            "text/event-stream": 'data: {"type":"token","content":"Revenue is up"}\n\n'
                        },
                    },
                    "400": _error(
                        "Required query parameters were omitted.",
                        {"is_error": True, "error": "input query is required"},
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_chat_send": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["Chat"],
                "summary": "Stream an authenticated chat response",
                "description": "Accepts a chat message and streams agent output as server-sent events.",
                "security": PROTECTED,
                "produces": ["text/event-stream"],
                "parameters": [
                    _json_body("#/definitions/ChatRequest", "Chat message payload.")
                ],
                "responses": {
                    "200": {
                        "description": "SSE stream of JSON events prefixed with data:.",
                        "examples": {
                            "text/event-stream": 'data: {"type":"token","content":"This month revenue is"}\n\n'
                        },
                    },
                    "400": BAD_REQUEST,
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "import_transactions": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1", "Import"],
                "summary": "Import transactions from CSV or XLSX",
                "description": "Uploads a CSV or XLSX file and inserts parsed transactions for the authenticated business.",
                "security": PROTECTED,
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {
                        "name": "file",
                        "in": "formData",
                        "type": "file",
                        "required": True,
                        "description": "CSV or XLSX file with date, type, category, amount, and description columns.",
                    }
                ],
                "responses": {
                    "201": _response(
                        "Transactions imported.",
                        "#/definitions/MessageResponse",
                        {"message": "Successfully imported 3 transactions!"},
                    ),
                    "400": BAD_REQUEST,
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "import_notebook": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1", "Import"],
                "summary": "Preview transactions from a notebook image",
                "description": "Uploads a notebook page image and returns extracted transactions for review before saving.",
                "security": PROTECTED,
                "consumes": ["multipart/form-data"],
                "parameters": [
                    {
                        "name": "file",
                        "in": "formData",
                        "type": "file",
                        "required": True,
                        "description": "Notebook image file such as JPG, PNG, or WEBP.",
                    }
                ],
                "responses": {
                    "200": _response(
                        "Extracted transaction preview.",
                        "#/definitions/TransactionPreview",
                        {
                            "transactions": [
                                {
                                    "date": "2026-05-20",
                                    "type": "Revenue",
                                    "category": "Sales",
                                    "amount": 1250.0,
                                    "description": "Counter sale",
                                }
                            ],
                            "hash": "5eb63bbbe01eeed093cb22bb8f5acdc3",
                        },
                    ),
                    "400": BAD_REQUEST,
                    "401": UNAUTHORIZED,
                    "409": _error(
                        "The notebook page was already imported.",
                        {"error": "This notebook page has already been imported."},
                    ),
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "confirm_notebook": [
        {
            "methods": ["POST"],
            "spec": {
                "tags": ["V1", "Import"],
                "summary": "Confirm notebook transaction import",
                "description": "Saves reviewed notebook transactions for the authenticated business.",
                "security": PROTECTED,
                "parameters": [
                    _json_body(
                        "#/definitions/ImportConfirmRequest",
                        "Reviewed transactions and source hash.",
                    )
                ],
                "responses": {
                    "201": _response(
                        "Transactions saved.",
                        "#/definitions/MessageResponse",
                        {"message": "Successfully saved 1 transactions!"},
                    ),
                    "400": BAD_REQUEST,
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_dashboard_summary": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get dashboard summary metrics",
                "description": "Returns revenue, expense, profit, transaction, alert, and period-change metrics.",
                "security": PROTECTED,
                "parameters": [PERIOD_PARAMETER],
                "responses": {
                    "200": _response(
                        "Dashboard summary metrics.",
                        "#/definitions/DashboardSummary",
                        {
                            "total_revenue": 15000.0,
                            "total_expenses": 9000.0,
                            "net_profit": 6000.0,
                            "total_transactions": 48,
                            "active_alerts": 3,
                            "revenue_change": 12.5,
                            "expenses_change": -3.0,
                            "net_profit_change": 18.4,
                            "transactions_change": 7.2,
                        },
                    ),
                    "400": BAD_REQUEST,
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_categories": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "List transaction categories",
                "description": "Returns distinct transaction categories for dashboard filters.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Available categories.",
                        "#/definitions/CategoriesResponse",
                        {"categories": ["Sales", "Rent", "Utilities"]},
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_financial_overview": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get monthly financial overview",
                "description": "Returns the last 12 months of revenue, expense, profit, and cash-balance series.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Financial overview time series.",
                        "#/definitions/FinancialOverview",
                        {
                            "labels": ["2026-04", "2026-05"],
                            "revenue": [12000, 15000],
                            "expenses": [8000, 9000],
                            "net_profit": [4000, 6000],
                            "cash_balance": [25000, 31000],
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "404": NOT_FOUND,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_forecast": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get revenue forecast",
                "description": "Returns recent revenue history, a 30-day projection, and a trend insight.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Forecast and trend data.",
                        "#/definitions/ForecastResponse",
                        {
                            "historical": [{"date": "2026-05-01", "actual": 1250.0}],
                            "forecast": [{"date": "2026-05-31", "predicted": 1425.0}],
                            "trend_direction": "up",
                            "trend_percent": 7.5,
                            "insight": "Revenue is trending upwards based on recent data.",
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "404": NOT_FOUND,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_revenue_vs_expense": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get revenue versus expense chart",
                "description": "Groups revenue and expense totals by category for the selected period.",
                "security": PROTECTED,
                "parameters": [PERIOD_PARAMETER],
                "responses": {
                    "200": _response(
                        "Revenue and expense category series.",
                        "#/definitions/RevenueExpenseSeries",
                        {
                            "labels": ["Sales", "Rent"],
                            "revenue": [15000, 0],
                            "expenses": [0, 5000],
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_sales_trend": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get sales trend chart",
                "description": "Returns daily revenue and expense series for the selected period.",
                "security": PROTECTED,
                "parameters": [PERIOD_PARAMETER],
                "responses": {
                    "200": _response(
                        "Daily revenue and expense series.",
                        "#/definitions/RevenueExpenseSeries",
                        {
                            "labels": ["2026-05-20", "2026-05-21"],
                            "revenue": [1250, 980],
                            "expenses": [450, 300],
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_recent_transactions": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "List recent dashboard transactions",
                "description": "Returns recent transactions with optional limit, text search, and category filters.",
                "security": PROTECTED,
                "parameters": [LIMIT_PARAMETER, SEARCH_PARAMETER, CATEGORY_PARAMETER],
                "responses": {
                    "200": _response(
                        "Recent transactions.",
                        "#/definitions/RecentTransactionsResponse",
                        {
                            "transactions": [
                                {
                                    "transaction_id": 7,
                                    "transaction_date": "2026-05-20",
                                    "type": "Revenue",
                                    "category": "Sales",
                                    "amount": 1250.5,
                                    "description": "May invoice",
                                }
                            ]
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_export_dashboard_csv": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Export dashboard transactions as CSV",
                "description": "Downloads filtered transactions as CSV using either a bearer token or email lookup.",
                "produces": ["text/csv"],
                "parameters": [
                    PERIOD_PARAMETER,
                    _query_param(
                        "email",
                        "Optional owner email fallback when no Authorization header is supplied.",
                        default="owner@example.com",
                    ),
                    {
                        "name": "Authorization",
                        "in": "header",
                        "required": False,
                        "type": "string",
                        "description": "Optional JWT bearer token, for example: Bearer <token>.",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "CSV file download.",
                        "examples": {
                            "text/csv": "transaction_id,transaction_date,type,category,amount,description\n"
                            "7,2026-05-20,Revenue,Sales,1250.50,May invoice\n"
                        },
                    },
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_alerts_list": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "List active dashboard alerts",
                "description": "Returns recent alerts for the authenticated business.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Dashboard alerts.",
                        "#/definitions/AlertsListResponse",
                        {
                            "alerts": [
                                {
                                    "alert_id": 3,
                                    "message": "Expenses exceeded monthly threshold.",
                                    "severity": "High",
                                    "status": "Active",
                                    "created_at": "2026-05-20 09:30",
                                }
                            ]
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "get_business_info": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get business profile",
                "description": "Returns the authenticated business record used by dashboard settings.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Business profile.",
                        "#/definitions/BusinessInfoResponse",
                        {
                            "business_id": "550e8400-e29b-41d4-a716-446655440000",
                            "business_name": "Pilot Store",
                            "industry_type": "Retail",
                            "owner_name": "Asha Patel",
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "404": NOT_FOUND,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_sales_target": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get monthly sales target progress",
                "description": "Returns current revenue, target revenue, and completion percentage.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Sales target progress.",
                        "#/definitions/SalesTargetResponse",
                        {
                            "current_revenue": 42000.0,
                            "target_revenue": 100000.0,
                            "percentage": 42.0,
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_alerts_by_severity": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get active alerts grouped by severity",
                "description": "Returns chart labels and counts for active alert severities.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Alert severity chart.",
                        "#/definitions/SeverityChartResponse",
                        {"labels": ["High", "Low"], "data": [2, 1]},
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_health_scores": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get business health scores",
                "description": "Returns the latest business health score breakdowns.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Health score breakdowns.",
                        "#/definitions/HealthScoresResponse",
                        {
                            "businesses": ["Pilot Store"],
                            "scores": [
                                {
                                    "name": "Pilot Store",
                                    "overall": 82.5,
                                    "cash": 78.0,
                                    "profitability": 88.0,
                                    "growth": 75.0,
                                    "cost_control": 84.0,
                                    "risk": 20.0,
                                }
                            ],
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_top_products": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get top products by stock",
                "description": "Returns product stock and margin arrays for dashboard product charts.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Top product chart data.",
                        "#/definitions/TopProductsResponse",
                        {
                            "labels": ["Notebook", "Pen"],
                            "stock": [120, 300],
                            "margin": [35.5, 42.0],
                            "margin_amount": [35.5, 4.2],
                            "margin_pct": [35.5, 42.0],
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
    "api_employee_stats": [
        {
            "methods": ["GET"],
            "spec": {
                "tags": ["Dashboard"],
                "summary": "Get employee status statistics",
                "description": "Returns employee counts and average salaries grouped by status.",
                "security": PROTECTED,
                "responses": {
                    "200": _response(
                        "Employee status statistics.",
                        "#/definitions/EmployeeStatsResponse",
                        {
                            "labels": ["Active", "Inactive"],
                            "counts": [8, 1],
                            "avg_salary": [45000.0, 0.0],
                        },
                    ),
                    "401": UNAUTHORIZED,
                    "500": INTERNAL_ERROR,
                },
            },
        }
    ],
}


def register_swagger_docs(app: Any) -> Swagger:
    """Attach Swagger specs to registered Flask views and enable Swagger UI."""

    for endpoint, entries in SPECS_BY_ENDPOINT.items():
        view = app.view_functions.get(endpoint)
        if view is None:
            continue

        for entry in entries:
            view = swag_from(entry["spec"], methods=entry["methods"])(view)
        app.view_functions[endpoint] = view

    return Swagger(app, config=SWAGGER_CONFIG, template=SWAGGER_TEMPLATE)
