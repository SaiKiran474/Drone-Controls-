import argparse
import os
import socket
import sys
import time

from dronekit import LocationGlobalRelative, VehicleMode
from dronekit import connect as dronekit_connect
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit
from pymavlink import mavutil
from socketio import Namespace

app = Flask(__name__)
app.config['SECRET_KEY']="SapientGeeks"
socketio = SocketIO(app,cors_allowed_origins="*")

vehicle = None
altitude = 0
yaw = 0
global cnt
cnt = 0
def get_parameters():
    global vehicle
    global altitude
    while(1):
        socketio.emit('parameters', {'data': altitude})
    

def send_message():
    socketio.emit('server_message', {'data': 'Hello from Flask!'}, room=request.sid)

@socketio.on('connect')
def handle_connect():
    global vehicle
    print(f'Client connected: {request.sid}')
    socketio.emit('parameters', {'data': altitude})
    socketio.emit('yaw1_dis', {'data': yaw})

    # get_parameters()
    # socketio.emit('parameters', {'data': 0})
    # while vehicle is not None:
    # get_parameters()


def condition_yaw_at_current_location(heading, relative=False):
    global vehicle
    if relative:
        is_relative = 1  # yaw relative to the direction of travel
    else:
        is_relative = 0  # yaw is an absolute angle

    # create the CONDITION_YAW command using command_long_encode()
    msg = vehicle.message_factory.command_long_encode(
        0, 0,  # target system, target component
        mavutil.mavlink.MAV_CMD_CONDITION_YAW,  # command
        0,  # confirmation
        heading,  # param 1, yaw in degrees
        0,  # param 2, yaw speed deg/s
        1,  # param 3, direction -1 ccw, 1 cw
        is_relative,  # param 4, relative offset 1, absolute angle 0
        0, 0, 0)  # param 5 ~ 7 not used

    # Send command to vehicle
    vehicle.send_mavlink(msg)

    timeout=10
    start_time = time.time()
    while time.time() - start_time < timeout:
        newyaw = vehicle.heading
        print("yaw : ",newyaw)
        socketio.emit('yaw1_dis',{'data': newyaw})
        time.sleep(1)


# Function to connect to the drone
def connect_to_drone():
    global vehicle
    parser = argparse.ArgumentParser()
    parser.add_argument('--connect', default='127.0.0.1:14550')
    args = parser.parse_args()
    
    print('Connecting to vehicle on: %s' % args.connect)
    # vehicle = dronekit_connect(args.connect)
    vehicle = dronekit_connect("tcp:127.0.0.1:5770", wait_ready=True)
    print(vehicle)
    # connection_string = 'COM4'
    # vehicle = dronekit_connect(connection_string,baud=57600, wait_ready=True)


# Function to arm and take off
def arm_and_takeoff(aTargetAltitude):
    global vehicle
    print("Basic pre-arm checks")
    
    while not vehicle.is_armable:
        print("Waiting for vehicle to initialise...")
        time.sleep(1)
    
    print("Arming motors")
    vehicle.mode = VehicleMode("GUIDED")
    vehicle.armed = True
    
    while not vehicle.armed:
        print("Waiting for arming...")
        time.sleep(1)
    
    print("Taking off!")
    vehicle.simple_takeoff(aTargetAltitude)
    
    while True:
        altitude = vehicle.location.global_relative_frame.alt
        # print("Altitude: ", vehicle.location.global_relative_frame.alt)
        print("Altitude: ", altitude)
        socketio.emit('parameters', {'data': altitude})
        if vehicle.location.global_relative_frame.alt >= aTargetAltitude * 0.95:
            print("Reached target altitude")
            socketio.emit('parameters',{'data':aTargetAltitude})
            break
        time.sleep(1)

    current_location = vehicle.location.global_relative_frame
    current_altitude = current_location.alt
    # Hold the altitude by adjusting the target altitude
    target_location = LocationGlobalRelative(
        current_location.lat,
        current_location.lon,
        current_altitude
    )
    vehicle.simple_goto(target_location)


# Function to change altitude
def change_altitude(changealtitude):
    inc = False
    curr = vehicle.location.global_relative_frame.alt
    if curr <= changealtitude:
        inc = True
    print(f"Changing altitude to {changealtitude}")
    vehicle.simple_goto(LocationGlobalRelative(
        vehicle.location.global_relative_frame.lat,
        vehicle.location.global_relative_frame.lon,
        changealtitude,
    ))
    while True:
        newaltitude = vehicle.location.global_relative_frame.alt
        print("Altitude: ", newaltitude)
        socketio.emit('parameters', {'data': newaltitude})
        if newaltitude >= changealtitude * 0.95 and inc:
            print(f"Reached new target altitude: {newaltitude}")
            socketio.emit('parameters', {'data': changealtitude})
            break
        elif newaltitude <= (changealtitude + 0.5) and inc == False:
            print(f"Reached new target altitude: {newaltitude}")
            socketio.emit('parameters', {'data': changealtitude})
            break
        time.sleep(1)


def start_client():
    s = socket.socket()
    host = socket.gethostname()
    port = 5000
    print(host)

    # Set the file size to 100 MB for download and upload
    file_size = 100 * 1024 * 1024  # 100 MB

    t1 = time.time()

    try:
        s.connect((host, port))
        s.send("Hello server!".encode())

        # Receive a message to indicate the start of download measurement
        s.recv(1024)

        # Receive the file size from the server
        downloaded_file_size = int(s.recv(1024).decode())
        print(downloaded_file_size)
        print('Received File Size:', downloaded_file_size)

        s.send("start_upload".encode())  # Send acknowledgment to start upload

        with open('received_file.txt', 'wb') as f:
            received_size = 0
            while received_size < downloaded_file_size:
                data = s.recv(1024)
                f.write(data)
                received_size += len(data)

        t2 = time.time()

        throughput_kbps = (downloaded_file_size / 1024) / (t2 - t1)
        throughput_mbps = throughput_kbps / 1000
        print('Download Throughput:', round(throughput_mbps, 3), 'Mbps')

        # Send a confirmation to the server
        s.send("Download complete".encode())
        sys.stdout.flush()  # Flush the output buffer

        # Receive a message to indicate the start of upload measurement
        s.recv(1024)

        # Send the file to the server
        s.sendall(str(file_size).encode())  # Send the file size to the server
        ack = s.recv(1024)  # Wait for server acknowledgment

        if ack.decode() == 'start_upload':
            with open('upload.txt', 'rb') as f:
                while True:
                    l = f.read(1024)
                    if not l:
                        break
                    s.sendall(l)

        print('Done sending upload')
        sys.stdout.flush()  # Flush the output buffer
        s.recv(1024)  # Wait for the server confirmation

        t3 = time.time()

        upload_throughput_kbps = (file_size / 1024) / (t3 - t2)
        upload_throughput_mbps = upload_throughput_kbps / 1000
        print('Upload Throughput:', round(upload_throughput_mbps, 3), 'Mbps')

    except Exception as e:
        print('Error:', str(e))

    finally:
        if s.fileno() != -1:  # Check if the socket is valid
            s.close()
            print('Connection closed')
    return [round(throughput_mbps, 3),round(upload_throughput_mbps, 3)]







# Define the home route
@app.route("/", methods=['GET'])
def home():
    return render_template('index.html')

# Define the route to connect to the drone
@app.route("/drone_connect", methods=['POST'])
def connect():
    connect_to_drone()
    response_data = {"message": "Drone connected"}
    return jsonify(response_data)

# Define the route to take off
@app.route("/takeoff", methods=['POST'])
def take_off():
    global cnt
    altitude = int(request.json.get('altitude'))
    if cnt==0:
        cnt =1
        arm_and_takeoff(altitude)
        print("Take off complete")
    else:
        change_altitude(altitude)
    # Send the current altitude in the response
    response_data = {"message": f"Taking off to {altitude} meters", "altitude": altitude}
    return jsonify(response_data)


# Define the route to land
@app.route("/land", methods=['POST'])
def landing():
    global cnt
    print("Now let's land")
    vehicle.mode = VehicleMode("LAND")
    while True:
        altitude = vehicle.location.global_relative_frame.alt
        print("Altitude: ", altitude)
        socketio.emit('parameters', {'data': altitude})
        if altitude < 0.5*0.95:
            socketio.emit('parameters',{'data':0})
            break
        time.sleep(1)
    cnt = 0
    response_data = {"message": "Now let's land"}
    vehicle.close()
    return jsonify(response_data)


@app.route("/RTL", methods=['POST'])
def return_tolaunch():
    global vehicle
    global cnt
    print("Returning to launch")
    vehicle.mode = VehicleMode("RTL")

    while True:
        altitude = vehicle.location.global_relative_frame.alt
        print("Altitude: ", altitude)
        socketio.emit('parameters', {'data': altitude})
        if altitude < 0.5 * 0.95:
            socketio.emit('parameters', {'data': 0})
            break
        time.sleep(1)
    cnt = 0
    print("RTL complete")
    response_data = {"message": "Returning to launch"}
    return jsonify(response_data)

@app.route("/yaw", methods=['POST'])
def yaw_moment():
    yaw = int(request.json.get('yaw'))
    headingval=vehicle.heading
    socketio.emit('yaw1_dis', {'data':headingval})
    condition_yaw_at_current_location(yaw)
    time.sleep(5)
    response_data = {"message": "Done!"}
    return jsonify(response_data)


@app.route("/networkspeed", methods=['POST'])
def network_speedtest():
    speeds = start_client()
    download_speed, upload_speed = speeds
    response_data = {
        "download_speed": download_speed,
        "upload_speed": upload_speed
    }
    return jsonify(response_data)


if __name__ == '__main__':
    # socketio.run(app, debug=True,host="172.168.3.130",port=5000)
    socketio.run(app, debug=True,host='0.0.0.0', port=5000)
