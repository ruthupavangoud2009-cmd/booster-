import os
import logging
from threading import Thread
from flask import Flask

# Disable verbose Flask startup/request logs in console
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask(__name__)

@app.route('/')
def home():
    return "<h1>Booster Discord Bot is Online 24/7!</h1><p>Status: Healthy</p>"

@app.route('/healthz')
def health():
    return {"status": "ok", "service": "booster-bot"}, 200

def run():
    # Render binds the port specified in $PORT, default to 8080 locally
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    """Starts the Flask web server in a background daemon thread for Render health checks."""
    t = Thread(target=run, daemon=True)
    t.start()
    print(f" [+] Web server started on port {os.environ.get('PORT', 8080)} for Render 24/7 keep-alive.")
