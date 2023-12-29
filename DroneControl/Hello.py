import argparse
import os
import socket
import sys
import time

from serial.tools.list_ports import comports

from dronekit import LocationGlobalRelative, VehicleMode
from dronekit import connect 
from flask import Flask, jsonify, render_template, request,redirect, url_for
from flask_socketio import SocketIO, emit
from pymavlink import mavutil
from socketio import Namespace
import logging



app=Flask(__name__,static_folder='static', static_url_path='/static')
logging.basicConfig(filename='app_log.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
vehicle=None
app.config['SECRET_KEY']="SapientGeeks"
socketio = SocketIO(app,cors_allowed_origins="*")
altitude = 0
yaw = 0
global cnt
cnt = 0
def get_parameters():
    global vehicle
    global altitude
    while(1):
        socketio.emit('alt', {'data': altitude})
    

def send_message():
    socketio.emit('server_message', {'data': 'Hello from Flask!'}, room=request.sid)

def ask_for_port():
    sys.stderr.write('\n--- Available ports:\n')
    ports = []
    for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
        sys.stderr.write('--- {:2}: {:20} {}\n'.format(n, port, desc))
        ports.append(port)
    while True:
        port = "drone"
        try:
            index = int(port) - 1
            if not 0 <= index < len(ports):
                sys.stderr.write('--- Invalid index!\n')
                continue
        except ValueError:
            pass
        else:
            port = ports[index]
      
        return ports
def start_client():
    s = socket.socket()
    host = socket.gethostname()
    ip_address = socket.gethostbyname(host)
    port = 5000
    print(host,ip_address)

    # Set the file size to 100 MB for download and upload
    file_size = 100 * 1024 * 1024  # 100 MB

    t1 = time.time()

    try:
        s.connect((host, port))
        print("connected")
        s.send("Hello server!".encode())
        print("data sent")
        # Receive a message to indicate the start of download measurement
        s.recv(1024)
        print(s,"hiouy")
        # Receive the file size from the server
        downloaded_file_size = int(s.recv(1024).decode())
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



# Example usage:
# def handle_update_data(data):
#    emit('update_data_response', {'alt': data['alt'], 'dir': data['dir'], 'speed': data['speed'], 'connectionSpeed': data['connectionSpeed']})
@app.route('/')
def start():
   vehicle=""
   print('Started')
   return render_template("About_page.html")
@app.route("/main1",methods=['POST','GET'])
def goto_page():
   return render_template('Goto.html')
@socketio.on('connect')
def handle_connect():
    global vehicle
    print(f'Client connected: {request.sid}')
    socketio.emit('alt', {'data': altitude})
    socketio.emit('yaw', {'data': yaw})
@app.route("/connect",methods=['POST'])
def connect_vehicle():
   if request.method=='POST':
      s1=ask_for_port()
      print("s1: ",s1)
      if(s1==[]):
         # s1="udp:192.168.2.175:14553"
         s1="tcp:172.168.4.189:5760"
      else:
         
         print(len(s1))
         s1=s1[0]
      try:
         global vehicle 
         vehicle= connect1(s1)
         print(vehicle)
      except Exception as e:
         print(f"Failed to connect: {str(e)}")

      vehicle.wait_ready('autopilot_version')
      print(vehicle.location.global_relative_frame)
      while not vehicle.gps_0.fix_type > 2:
         print('Waiting for GPS fix...')
         time.sleep(1)

      # Get satellite information
      num_satellites = vehicle.gps_0.satellites_visible
      print(f'Number of satellites: {num_satellites}')
      if(int(vehicle.location.global_relative_frame.alt)<=0):
         return render_template('takeoff.html')
      else:
         return render_template('Goto.html')
def connect1(s):
   vehicle = connect(s, wait_ready=True,baud=56700)
   # vehicle = connect(s, wait_ready=True)
   print("\nConnecting to vehicle on: %s" % s)
   print(vehicle.battery.level)
   return vehicle
@app.route("/index")
def index():
    return render_template("index.html")
@app.route("/getData",methods=['POST'])
def getData():
   global vehicle
   altitude = vehicle.location.global_relative_frame.alt
   print(altitude,vehicle.heading)
   socketio.emit('alt', {'data': altitude})
   socketio.emit('yaw', {'data': vehicle.heading})
@app.route('/main',methods=['POST'])
def arm_and_takeoff():
   global vehicle
   if(int(vehicle.location.global_relative_frame.alt)<=0):
      if request.method == 'POST':
         alt =int(request.json.get('altitude'))
         # x=dataTrans()
         x=10
         # connection_string = 'udp:127.0.0.1:14550'
         print(" Waiting for vehicle to initialise... %s "% vehicle)
         while not vehicle.is_armable:
            print(" Waiting for vehicle to initialise...")
            time.sleep(1)

         print("Arming motors")
      # Copter should arm in GUIDED mode
         vehicle.mode = VehicleMode("GUIDED")
         vehicle.armed = True

      # Confirm vehicle armed before attempting to take off
         while not vehicle.armed:
            print(" Waiting for arming...")
            time.sleep(1)

         print("Taking off!")
         vehicle.simple_takeoff(alt)
         while True:
            altitude = vehicle.location.global_relative_frame.alt
            print(" Altitude: ", vehicle.location.global_relative_frame.alt,vehicle.location.global_relative_frame)
            # Break and return from function just below target altitude.
            socketio.emit('alt', {'data': altitude})
            socketio.emit('yaw', {'data': vehicle.heading})
            if vehicle.location.global_relative_frame.alt >= alt * 0.95:
                  print("Reached target altitude")
                  socketio.emit('alt',{'data':alt})
                  break
            time.sleep(1)
         print(vehicle.battery)
         return render_template("index.html")
   else:
      alt =int(request.json.get('altitude'))
      point1 = LocationGlobalRelative(vehicle.location.global_relative_frame.lat,vehicle.location.global_relative_frame.lon,alt)
      if(vehicle.mode!="GUIDED"):
         vehicle.mode = VehicleMode("GUIDED")
      vehicle.armed = True
      while not vehicle.armed:
         print(" Waiting for arming...")
         time.sleep(1)
      print("goto!")
      vehicle.simple_goto(point1)
      while True:
         print(" Altitude: ", vehicle.location.global_relative_frame.alt,int(vehicle.location.global_relative_frame.lat*1000))
         currAlt = vehicle.location.global_relative_frame.alt
         print("Altitude: ", currAlt)
         socketio.emit('alt', {'data': currAlt})
         if currAlt >= alt * 0.95 and currAlt <= alt * 1.05:
               print(f"Reached new target altitude: {currAlt}")
               time.sleep(1)
               socketio.emit('alt', {'data': alt})
               break
         time.sleep(1)
      print("hi")
      # return render_template("index.html",alt=vehicle.location.global_relative_frame.alt,dir=vehicle.heading,speed=vehicle.airspeed,connectionSpeed=50)
@app.route('/return_to_home' ,methods=['POST'])
def return_to_home():
   global vehicle
   try:
      vehicle.mode = VehicleMode("RTL")
      while not vehicle.mode.name == 'RTL':
         pass
      while True:
         socketio.emit('alt', {'data': vehicle.location.global_relative_frame.alt})
         if(vehicle.location.global_relative_frame.alt<=0.3):
            socketio.emit('alt', {'data': 0})
            break
         time.sleep(1)
      return render_template("/")
   except Exception as e:
      if(vehicle.location.global_relative_frame.alt<=0.3):
         return render_template("/")
@app.route('/Land',methods=['POST','GET'])
def land():
   global vehicle
   try:
      vehicle.mode = VehicleMode("LAND")
      while True:
         socketio.emit('alt', {'data': vehicle.location.global_relative_frame.alt})
         if(vehicle.location.global_relative_frame.alt<=0.3):
            socketio.emit('alt', {'data': 0})
            break
         time.sleep(1)
      return render_template("takeoff.html")
   except Exception as e:
      return render_template("index.html")
@app.route("/change_yaw",methods=['GET','POST'])
def change_yaw():
   
   yaw = int(request.json.get('yaw', 0))
   while True:
    
      vehicle.channels.overrides['4'] = 1500
      if yaw - 1 <= int(vehicle.heading) <= yaw + 1:
         break
      desired_yaw = 1550
      vehicle.channels.overrides['4'] = int(desired_yaw)
      time.sleep (0.1)
      socketio.emit('yaw', {'data': vehicle.heading})
      print(vehicle.heading)
      vehicle.channels.overrides['4'] = 1500
   # x=dataTrans()
      # x=50
   time.sleep(1)
   socketio.emit('yaw', {'data': vehicle.heading})
   return render_template("index.html")
@app.route("/networkspeed", methods=['POST'])
def network_speedtest():
    speeds = start_client()
    download_speed, upload_speed = speeds
    response_data = {
        "download_speed": download_speed,
        "upload_speed": upload_speed
    }
    return jsonify(response_data)


if __name__=='__main__':
   # app.debug = True
     # Initialize the socket before running the Flask app
   # socketio.run(app, debug=True) #Charan update
   socketio.run(app, debug=True,host='0.0.0.0', port=5500)
   

