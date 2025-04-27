from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from flask_socketio import SocketIO
import serial
import time
import json
import os
import csv
import serial.tools.list_ports

LOG_FILE = 'run_log.txt'

# File paths for caching
CACHE_FILE = 'cache.json'

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = "secret_key"
socketio = SocketIO(app)

# Arduino serial connection configuration
SERIAL_PORT = 'COM6'  # Update to match your Arduino's port
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
@app.route('/sequence')
def sequence_page():
    return render_template('index.html', sequence=sequence, activities=activities)
def format_activity(activity):
    return {key: int(float(value)) for key, value in activity.items()}
    #return {key: int(float(value)) if float(value) == int(float(value)) else float(value) for key, value in activity.items()}
@app.route('/add_command', methods=['POST'])
def add_command():
    # Get command parameters from the form
    command = request.form.get('command')
    activity = 'Custom Defined'
    count = request.form.get('count', 1)  # Default count to 1 if not specified
    sequence.append({'activity_name': activity, 'command': command, 'count': int(count)})
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
        try:
            sequence[index]['count'] = int(new_count)
            save_cache()
            # return redirect(url_for('index'))
            return jsonify({"success": True})
        except ValueError:
            return jsonify({"success": False, "error": "Invalid count value"}), 400
    return jsonify({"success": False, "error": "Invalid sequence index"}), 400

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
    activity_name = request.form.get('activity_name').strip()
    try:
        min_force = float(request.form.get('min_force').strip())
        max_force = float(request.form.get('max_force').strip())
        hold_time_min = float(request.form.get('hold_time_min').strip())
        hold_time_max = float(request.form.get('hold_time_max').strip())
        start_angle = float(request.form.get('start_angle').strip())
        end_angle = float(request.form.get('end_angle').strip())
    except ValueError:
        return "All values must be valid numbers", 400

    # Store the activity as a dictionary
    activities[activity_name] = {
        "MIN_TARGET_FORCE": min_force,
        "MAX_TARGET_FORCE": max_force,
        "HOLD_TIME_MIN": hold_time_min,
        "HOLD_TIME_MAX": hold_time_max,
        "StartAngle": start_angle,
        "EndAngle": end_angle
    }
    activities[activity_name] = format_activity(activities[activity_name])  # Format the activity
    save_cache()
    return redirect(url_for('activities_page'))

@app.route('/update_activity', methods=['POST'])
def update_activity():
    activity_name = request.form.get('activity_name').strip()
    key = request.form.get('key').strip()
    value = request.form.get('value').strip()

    if activity_name in activities and key in activities[activity_name]:
        try:
            value = float(value)
        except ValueError:
            return jsonify({"success": False, "error": "Value must be a valid number"}), 400
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

@app.route('/delete_activities', methods=['POST'])
def delete_activities():
    data = request.get_json()  # Parse JSON payload
    selected_activities = data.get('activities', [])
    if not selected_activities:
        return jsonify({"error": "No activities selected"}), 400

    # Delete the selected activities
    for activity_name in selected_activities:
        if activity_name in activities:
            del activities[activity_name]

    save_cache()  # Save changes to the cache
    return jsonify({"success": True, "message": "Selected activities deleted successfully"})

@app.route('/add_activity_to_sequence/<string:activity_name>', methods=['POST'])
def add_activity_to_sequence(activity_name):
    if activity_name in activities:
        activity = format_activity(activities[activity_name])
        command = f"{activity['MIN_TARGET_FORCE']} {activity['MAX_TARGET_FORCE']} {activity['HOLD_TIME_MIN']} {activity['HOLD_TIME_MAX']} {activity['StartAngle']} {activity['EndAngle']}"
        sequence.append({'command': command, 'count': 1, 'activity_name': activity_name})  # Include activity_name
    save_cache()
    return redirect(url_for('index'))

@app.route('/export_activities', methods=['POST'])
def export_activities():
    data = request.get_json()  # Parse JSON payload
    selected_activities = data.get('selected_activities', [])
    if not selected_activities:
        return "No activities selected", 400

    # Create CSV data
    csv_data = [["Activity Name", "MIN_TARGET_FORCE", "MAX_TARGET_FORCE", "HOLD_TIME_MIN", "HOLD_TIME_MAX", "StartAngle", "EndAngle"]]
    for name in selected_activities:
        if name in activities:
            activity = format_activity(activities[name])
            csv_data.append([name] + list(activity.values()))

    # Generate CSV response using csv.writer
    def generate_csv():
        from io import StringIO
        output = StringIO()
        writer = csv.writer(output)
        writer.writerows(csv_data)
        return output.getvalue()

    return Response(generate_csv(), mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=activities.csv"})

@app.route('/import_activities', methods=['POST'])
def import_activities():
    file = request.files.get('file')
    if not file or not file.filename.endswith('.csv'):
        return "Invalid file", 400

    # Decode the file stream to text mode
    file_stream = file.stream.read().decode('utf-8').splitlines()
    csv_reader = csv.reader(file_stream)
    next(csv_reader)  # Skip header row

    for row in csv_reader:
        if len(row) == 7:
            name, min_force, max_force, hold_time_min, hold_time_max, start_angle, end_angle = row
            activities[name] = {
                "MIN_TARGET_FORCE": min_force,
                "MAX_TARGET_FORCE": max_force,
                "HOLD_TIME_MIN": hold_time_min,
                "HOLD_TIME_MAX": hold_time_max,
                "StartAngle": start_angle,
                "EndAngle": end_angle
            }
            activities[name] = format_activity(activities[name])
    save_cache()
    return redirect(url_for('activities_page'))

@app.route('/update_sequence_item/<int:index>', methods=['POST'])
def update_sequence_item(index):
    """Update a sequence item to the latest version of the linked activity."""
    global sequence  # Ensure the global sequence is used
    if 0 <= index < len(sequence):
        activity_name = sequence[index].get('activity_name')
        if activity_name and activity_name in activities:
            activity = format_activity(activities[activity_name])
            command = f"{activity['MIN_TARGET_FORCE']} {activity['MAX_TARGET_FORCE']} {activity['HOLD_TIME_MIN']} {activity['HOLD_TIME_MAX']} {activity['StartAngle']} {activity['EndAngle']}"
            sequence[index]['command'] = command
            save_cache()
            return jsonify({"success": True, "command": command, "activity_name": activity_name})
    return jsonify({"success": False, "error": "Invalid sequence index or activity"}), 400

@app.route('/reorder_sequence', methods=['POST'])
def reorder_sequence():
    """Reorder the sequence based on the provided order."""
    global sequence  # Ensure the global sequence is used
    new_order = request.get_json().get('new_order', [])
    if len(new_order) == len(sequence) and all(isinstance(i, int) and 0 <= i < len(sequence) for i in new_order):
        sequence = [sequence[i] for i in new_order]
        save_cache()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid order"}), 400

@app.route('/manual_control_page')
def manual_control_page():
    return render_template('manual_control.html')

@app.route('/debug_activities', methods=['GET'])
def debug_activities():
    return jsonify(activities)

@app.route('/debug_sequences', methods=['GET'])
def debug_sequences():
    return jsonify(sequence)

from flask_socketio import emit

@app.route('/run_cycles')
def run_cycles_page():
    return render_template('run_cycles.html')

@socketio.on('start_run')
def start_run():
    global sequence
    connect_to_arduino()
    if not arduino:
        emit('log', {'message': 'Arduino not connected'})
        return
    total_cycles = sum(item['count'] for item in sequence)
    completed_cycles = 0

    for item in sequence:
        command = item['command']
        if 'activity_name' in item:
            activity = item['activity_name']
        else:
            actvity = command
        count = item['count']
        current_count = 0
        status1 = True
        emit('log', {'message': activity})
        emit('update_progress', {
            'activity': activity,
            'total_cycles': total_cycles,
            'remaining_cycles': total_cycles - completed_cycles,
        })

        line = 0

        # while current_count < count:
        send_command(command)
        while line != "###":
            line = arduino.readline().decode('utf-8').strip()
        while status1: #current_count < count: # was True
            if arduino.in_waiting > 0:
                line = arduino.readline().decode('utf-8').strip()
                emit('log', {'message': line})

                if "Cycle count:" in line:
                    current_count = int(line.split(":")[1].strip())
                    completed_cycles += 1
                    emit('update_progress', {
                        'current_count': current_count,
                        'remaining_cycles': total_cycles - completed_cycles,
                    })

                    # emit('update_count', {'activity': activity, 'count': current_count})
                    if current_count >= count: # was >=
                        status1 = False
                        current_count = 0
                        emit('log', {'message': ''})
                        break
                if "Min force during ramp down:" in line or "Max force during ramp up:" in line:
                    force = float(line.split(":")[1].strip())
                    emit('update_progress', {'force': force})
                if "RoM down:" in line or "RoM up:" in line:
                    rom = int(line.split(":")[1].strip())
                    emit('update_progress', {'rom': rom})
    emit('log', {'message': 'Sequence completed'})

# Check for available serial ports
@app.route('/list_ports', methods=['GET'])
def list_ports():
    """List available COM ports."""
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return jsonify({"ports": ports})

@app.route('/set_port', methods=['POST'])
def set_port():
    """Set the selected COM port."""
    global SERIAL_PORT, arduino
    port = request.json.get('port')
    if port:
        SERIAL_PORT = port
        if arduino and arduino.is_open:
            arduino.close()  # Close the current port
        return jsonify({"success": True, "port": SERIAL_PORT})
    return jsonify({"success": False, "error": "Invalid port"}), 400

@app.route('/reopen_port', methods=['POST'])
def reopen_port():
    """Reopen the selected COM port."""
    global arduino
    try:
        connect_to_arduino()
        if arduino and arduino.is_open:
            return jsonify({"success": True, "message": f"Port {SERIAL_PORT} reopened successfully"})
        return jsonify({"success": False, "error": "Failed to open port"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/close_port', methods=['POST'])
def close_port():
    """Close the current COM port."""
    global arduino
    if arduino and arduino.is_open:
        arduino.close()
        return jsonify({"success": True, "message": f"Port {SERIAL_PORT} closed successfully"})
    return jsonify({"success": False, "error": "Port is not open"})

###
# @app.route('/clear_log', methods=['POST'])
# def clear_log():
#     """Clear the log file."""
#     try:
#         if os.path.exists(LOG_FILE):
#             open(LOG_FILE, 'w').close()  # Clear the file
#         return jsonify({"success": True})
#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500
#
# @app.route('/export_log', methods=['GET'])
# def export_log():
#     """Export the log file."""
#     try:
#         if os.path.exists(LOG_FILE):
#             return Response(
#                 open(LOG_FILE, 'r').read(),
#                 mimetype='text/plain',
#                 headers={"Content-Disposition": "attachment;filename=run_log.txt"}
#             )
#         return jsonify({"success": False, "error": "Log file not found"}), 404
#     except Exception as e:
#         return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)