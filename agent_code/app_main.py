from __future__ import annotations
from core_logic import *
from routes.dashboard import dashboard_bp
from routes.webhooks import webhook_bp
from routes.chat import chat_bp
from routes.api import api_bp

app.register_blueprint(dashboard_bp)
app.register_blueprint(webhook_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(api_bp)

# Start Server
_init_chat_db()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
    