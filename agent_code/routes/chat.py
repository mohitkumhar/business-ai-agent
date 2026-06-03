from flask import Blueprint, jsonify, request, Response, stream_with_context, g
from core_logic import *

chat_bp = Blueprint('chat_bp', __name__)

@chat_bp.route("/api/chat/send", methods=["POST"])
def api_chat_send():
    data = request.json
    conv_id = data.get("conversation_id")
    msg = data.get("message")
    # Wrap iter_query_sse in SSE Response
    return Response(stream_with_context(iter_query_sse(msg, conv_id)), mimetype="text/event-stream")

# Start Server
_init_chat_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    