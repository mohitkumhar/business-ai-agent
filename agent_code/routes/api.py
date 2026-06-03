from flask import Blueprint, jsonify, request, Response, stream_with_context, g
from core_logic import *

api_bp = Blueprint('api_bp', __name__)

@api_bp.route("/")
def home():
    return "Intelligent AI Agent is running. Use /api/v1/query."


@api_bp.route("/metrics")
def metrics_endpoint():
    return Response(generate_latest(REGISTRY), mimetype=CONTENT_TYPE_LATEST)


@api_bp.route("/api/v1/query", methods=["POST", "GET"])
def query_agent():
    input_query = request.args.get("input-query", "")
    thread_id = request.args.get("thread-id", "")
    business_id = request.args.get("business-id", "") or ""
    if not input_query:
        return jsonify({"is_error": True, "error": "input query is required"}), 400
    if not thread_id:
        return jsonify({"is_error": True, "error": "thread-id is required"}), 400
    gen = stream_agent_sse_lines(
        input_query,
        thread_id,
        business_id,
        on_chain_intent=lambda n: AGENT_INTENT_COUNT.labels(n).inc(),
    )
    return _sse_stream_response(gen)


@api_bp.route("/api/v1/billing/analyze-all", methods=["POST"])
def billing_analyze_all():
    data = request.get_json(force=True) or {}
    question = (data.get("question") or "Analyze all business billing data").strip()
    business_id = (data.get("business_id") or "").strip() or _resolve_business_id(None)
    try:
        answer = _analyze_business_data(business_id, question)
        return jsonify({"business_id": business_id, "analysis": answer})
    except Exception as exc:
        logger.error("Analyze all failed: %s", exc, exc_info=True)
        return internal_error_response(exc)


@api_bp.route("/api/v1/employees", methods=["GET"])
def get_employees():
    repo = os.getenv("GITHUB_REPO", "mohitkumhar/intelligent-business-agent")
    try:
        res = requests.get(f"https://api.github.com/repos/{repo}/contributors", timeout=20)
        counts = get_assigned_counts()
        if res.status_code != 200:
            logger.warning("GitHub contributors API returned %s; using fallback list", res.status_code)
            return jsonify(
                {
                    "employees": [
                        {"login": "engineer_a", "avatar_url": "", "assigned_issues": counts.get("engineer_a", 0)},
                        {"login": "engineer_b", "avatar_url": "", "assigned_issues": counts.get("engineer_b", 0)},
                    ],
                    "degraded": True,
                    "reason": f"GitHub API unavailable (status {res.status_code}); showing placeholder contributors.",
                }
            )
    
       
        contributors = res.json()
        return jsonify(
            {
                "employees": [
                    {
                        "login": c.get("login", "Unknown"),
                        "avatar_url": c.get("avatar_url", ""),
                        "assigned_issues": counts.get(c.get("login", "Unknown"), 0),
                    }
                    for c in contributors
                ]
            }
        )
    except Exception as exc:
        request_id = get_request_id(getattr(g, "request_id", None))
        logger.error(
            "Employees API failed request_id=%s repo=%s: %s",
            request_id,
            repo,
            exc,
            exc_info=True,
        )
        return (
            jsonify(
                {
                    "error": SAFE_INTERNAL_ERROR_MESSAGE,
                    "code": "employees_unavailable",
                    "request_id": request_id,
                }
            ),
            500,
        )


@api_bp.route("/api/v1/escalate", methods=["POST"])
def escalate_to_slack():
    try:
        data = request.get_json() or {}
        query = data.get("query", "No specific query")
        summary = data.get("summary", "No summary provided")
        from slack_integration.slack_handler import SlackDelivery
        from slack_integration.smart_assigner import pick_assignee_slack_id

        delivery = SlackDelivery()
        if not delivery.configured():
            return jsonify({"error": "Slack is not configured"}), 500
        ch = delivery.demo_channel_id
        if not ch:
            return jsonify({"error": "No Slack channel configured"}), 500

        assignee_id = data.get("assignee_name") or pick_assignee_slack_id(user_query=query, summary=summary)
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "Web User Escalation", "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Query:*\n>{query[:500]}\n\n*Context:*\n```{summary[:2000]}```"},
            },
        ]
        if assignee_id:
            increment_assigned_count(str(assignee_id))
        delivery.client.chat_postMessage(channel=ch, text="Web Chatbot Escalation", blocks=blocks)
        return jsonify({"status": "ok"}), 200
    except Exception as exc:
        return internal_error_response(exc)


@api_bp.route("/api/v1/onboarding", methods=["POST"])
def onboarding():
    data = request.json
    business_name = data.get("business_name")
    email = data.get("email", "").lower().strip()
    if not business_name or not email: return jsonify({"error": "Missing fields"}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        bid = str(uuid.uuid4())
        cur.execute("INSERT INTO businesses (business_id, business_name, industry_type, owner_name) VALUES (%s, %s, %s, %s)", 
                   (bid, business_name, data.get("business_category"), data.get("full_name")))
        cur.execute("INSERT INTO users (business_id, name, email, password_hash) VALUES (%s, %s, %s, %s)",
                   (bid, data.get("full_name"), email, SOCIAL_LOGIN_PASSWORD_HASH))
        conn.commit()
        return jsonify({"success": True, "business_id": bid}), 201
    finally:
        conn.close()

# --- SSE Chat Logic ---
def iter_query_sse(input_query, thread_id):
    # LangGraph logic from testsparkhack branch
    yield f"data: {json.dumps({'type': 'status', 'status': 'Thinking...'})}\n\n"
    intent = intent_detection.detect_intent(input_query)
    # Stream tokens here... (Simplified for merge, use your full _stream_graph logic)
    yield f"data: {json.dumps({'type': 'token', 'content': 'AI Response placeholder...'})}\n\n"
    yield f"data: {json.dumps({'type': 'final', 'intent_str': 'database_request'})}\n\n"

