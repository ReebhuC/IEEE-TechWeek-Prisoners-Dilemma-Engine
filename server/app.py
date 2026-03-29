# We skip eventlet monkey patch here to prevent issues when running from plain python script
# if socketio needs async it handles it via threading mode normally
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
# using threading mode explicitly makes it easier to integrate without eventlet patches
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

latest_leaderboard_data = []
recent_events = []

@socketio.on('connect')
def on_connect():
    """Send latest state when a client connects."""
    if latest_leaderboard_data:
        socketio.emit("leaderboard_update", latest_leaderboard_data, to=request.sid)
    for ev in recent_events[-50:]:
        socketio.emit("new_event", {"message": ev}, to=request.sid)

@app.route("/")
def index():
    return render_template("index.html")

def emit_leaderboard(leaderboard_data):
    """
    Called periodically by the tournament engine to update UI.
    Receives list of dicts: [{agent_id, strategy_type, score, elo}]
    """
    global latest_leaderboard_data
    latest_leaderboard_data = leaderboard_data
    socketio.emit("leaderboard_update", leaderboard_data)

def emit_event(event_msg: str):
    """Called to broadcast important events to the UI."""
    global recent_events
    recent_events.append(event_msg)
    if len(recent_events) > 50:
        recent_events.pop(0)
    socketio.emit("new_event", {"message": event_msg})

def start_server(port=5000):
    """Starts the Flask server. Can be run in a daemon thread."""
    socketio.run(app, host="0.0.0.0", port=port, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)

def start_server_thread(port=5000):
    t = threading.Thread(target=start_server, args=(port,))
    t.daemon = True
    t.start()
    return t
