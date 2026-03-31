import secrets
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import threading

app = Flask(__name__)

# FIX 9a: Randomised secret key — never hardcode 'secret!' in a public repo
app.config["SECRET_KEY"] = secrets.token_hex(32)

# FIX 9b: Restrict CORS to localhost only — no external site can talk to this socket
socketio = SocketIO(
    app,
    cors_allowed_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    async_mode="threading",
)

latest_leaderboard_data = []
recent_events = []


@socketio.on("connect")
def on_connect():
    """Send latest state when a client first connects."""
    if latest_leaderboard_data:
        socketio.emit("leaderboard_update", latest_leaderboard_data, to=request.sid)
    for ev in recent_events[-50:]:
        socketio.emit("new_event", ev, to=request.sid)


@app.route("/")
def index():
    return render_template("index.html")


def emit_leaderboard(leaderboard_data):
    """
    Called by the tournament engine to push updated rankings to the UI.
    Receives list of dicts: [{agent_id, strategy_type, score, elo}]
    """
    global latest_leaderboard_data
    latest_leaderboard_data = leaderboard_data
    socketio.emit("leaderboard_update", leaderboard_data)


def emit_event(event_msg: str):
    """Called to broadcast important events to the UI."""
    global recent_events
    import datetime
    pack = {
        "message": event_msg,
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
    }
    recent_events.append(pack)
    if len(recent_events) > 50:
        recent_events.pop(0)
    socketio.emit("new_event", pack)


def start_server(port=5000):
    """Starts the Flask-SocketIO server on all interfaces."""
    socketio.run(
        app,
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False,
        allow_unsafe_werkzeug=True,
    )


def start_server_thread(port=5000):
    t = threading.Thread(target=start_server, args=(port,))
    t.daemon = True
    t.start()
    return t
