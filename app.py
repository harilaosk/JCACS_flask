from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_socketio import SocketIO
import serial
import time
import json
import os

# File paths for caching
CACHE_FILE = 'cache.json'

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)

# Arduino serial connection configuration
SERIAL_PORT = 'COM3'  # Update to match your Arduino's port
BAUD_RATE = 115200

# Initialize global variables
arduino = None
# Load cached data
def load_cache():
    global sequence, activities
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            data = json.load(f)
            sequence = data.get('sequence', [])
            activities = data.get('activities', {})
    else:
        sequence = []  # Holds the sequence of commands (each command is a dict with 'command' and 'count')
        activities = {}  # Holds defined activities
# Save data to cache
def save_cache():
    with open(CACHE_FILE, 'w') as f:
        json.dump({'sequence': sequence, 'activities': activities}, f)

# Load cache on startup
load_cache()

# Connect to Arduino
def connect_to_arduino():
    global arduino
    if arduino is None or not arduino.is_open:
        try:
            arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
            time.sleep(2)  # Allow Arduino time to initialize
        except serial.SerialException as e:
            print(f"Error: {e}")
            arduino = None

# Send a command to Arduino
def send_command(command):
    global arduino
    connect_to_arduino()
    if arduino:
        arduino.write(f"{command}\n".encode('utf-8'))
        time.sleep(0.1)
        response = arduino.readline().decode('utf-8').strip()
        return response
    return "Arduino not connected"

@app.route('/')
def index():
    return render_template('index.html', sequence=sequence, activities=activities)

@app.route('/add_command', methods=['POST'])
def add_command():
    # Get command parameters from the form
    command = request.form.get('command')
    count = request.form.get('count', 1)  # Default count to 1 if not specified
    sequence.append({'command': command, 'count': int(count)})
    save_cache()
    return redirect(url_for('index'))

@app.route('/delete_command/<int:index>', methods=['POST'])
def delete_command(index):
    if 0 <= index < len(sequence):
        sequence.pop(index)
        save_cache()
    return redirect(url_for('index'))

@app.route('/update_count/<int:index>', methods=['POST'])
def update_count(index):
    if 0 <= index < len(sequence):
        new_count = request.form.get('count', 1)
        sequence[index]['count'] = int(new_count)
    return redirect(url_for('index'))

@app.route('/run_sequence', methods=['POST'])
def run_sequence():
    for item in sequence:
        command = item['command']  # Ignore the count when sending to Arduino
        response = send_command(command)
        print(f"Sent: {command}, Response: {response}")
    return redirect(url_for('index'))

@app.route('/manual_control', methods=['POST'])
def manual_control():
    direction = request.form.get('direction')
    steps = request.form.get('steps', 1)
    command = f"MANUAL {direction} {steps}"
    response = send_command(command)
    return jsonify({"response": response})

@app.route('/clear_sequence', methods=['POST'])
def clear_sequence():
    sequence.clear()
    save_cache()
    return redirect(url_for('index'))

@app.route('/activities')
def activities_page():
    return render_template('activities.html', activities=activities)

@app.route('/add_activity', methods=['POST'])
def add_activity():
    activity_name = request.form.get('activity_name')
    min_force = request.form.get('min_force')
    max_force = request.form.get('max_force')
    hold_time_min = request.form.get('hold_time_min')
    hold_time_max = request.form.get('hold_time_max')
    start_angle = request.form.get('start_angle')
    end_angle = request.form.get('end_angle')

    # Store the activity as a dictionary
    activities[activity_name] = {
        "MIN_TARGET_FORCE": min_force,
        "MAX_TARGET_FORCE": max_force,
        "HOLD_TIME_MIN": hold_time_min,
        "HOLD_TIME_MAX": hold_time_max,
        "StartAngle": start_angle,
        "EndAngle": end_angle
    }
    save_cache()
    return redirect(url_for('activities_page'))

@app.route('/update_activity', methods=['POST'])
def update_activity():
    activity_name = request.form.get('activity_name')
    key = request.form.get('key')
    value = request.form.get('value')

    if activity_name in activities and key in activities[activity_name]:
        activities[activity_name][key] = value
        save_cache()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid activity or key"}), 400

@app.route('/delete_activity/<string:activity_name>', methods=['POST'])
def delete_activity(activity_name):
    if activity_name in activities:
        del activities[activity_name]
        save_cache()
    return redirect(url_for('activities_page'))

@app.route('/add_activity_to_sequence/<string:activity_name>', methods=['POST'])
def add_activity_to_sequence(activity_name):
    if activity_name in activities:
        activity = activities[activity_name]
        command = f"{activity['MIN_TARGET_FORCE']} {activity['MAX_TARGET_FORCE']} {activity['HOLD_TIME_MIN']} {activity['HOLD_TIME_MAX']} {activity['StartAngle']} {activity['EndAngle']}"
        sequence.append({'command': command, 'count': 1})  # Default count to 1
    return redirect(url_for('index'))

@app.route('/manual_control_page')
def manual_control_page():
    return render_template('manual_control.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)