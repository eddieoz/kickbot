from flask import Flask, render_template, request
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/trigger_alert')
def trigger_alert():
    gif_url = request.args.get('gif')
    audio_url = request.args.get('audio')
    text = request.args.get('text')
    width = request.args.get('width')
    height = request.args.get('height')
    fontFamily = request.args.get('fontFamily')
    fontSize = request.args.get('fontSize')
    borderColor = request.args.get('borderColor')
    borderWidth = request.args.get('borderWidth', '1px')  # Default to 1px if not provided
    color = request.args.get('color')
    duration = int(request.args.get('duration', 10000))  # Default to 10 seconds if not provided

    alert_data = {
        "gif": gif_url,
        "audio": audio_url,
        "text": text,
        "width": width,
        "height": height,
        "fontFamily": fontFamily,
        "fontSize": fontSize,
        "borderColor": borderColor,
        "borderWidth": borderWidth,
        "color": color,
        "duration": duration
    }
    socketio.emit('show_alert', alert_data)
    return "Alert triggered"

if __name__ == "__main__":
    socketio.run(app, debug=True)
