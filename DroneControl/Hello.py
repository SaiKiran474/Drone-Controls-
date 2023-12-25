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
app=Flask(__name__,static_folder='static', static_url_path='/static')
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
        socketio.emit('parameters', {'data': altitude})
    

def send_message():
    socketio.emit('server_message', {'data': 'Hello from Flask!'}, room=request.sid)

def ask_for_port():
    """\
    Show a list of ports and ask the user for a choice. To make selection
    easier on systems with long device names, also allow the input of an
    index.
    """
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
   return render_template('About_page.html')
@app.route("/main1")
def goto_page():
   return render_template('Goto.html',lat=vehicle.location.global_relative_frame.lat,long=vehicle.location.global_relative_frame.lon)
@socketio.on('connect')
def handle_connect():
    global vehicle
    print(f'Client connected: {request.sid}')
    socketio.emit('parameters', {'data': altitude})
    socketio.emit('yaw1_dis', {'data': yaw})
@app.route("/connect",methods=['POST'])
def connect_vehicle():
   if request.method=='POST':
      # user = request.form['nm']
      # s1=listEBBports()
      # print("s1: ",s1)
      # print("s2:",findPort())
      s1=ask_for_port()
      print("s1: ",s1)
      if(s1==[]):
         s1="tcp:127.0.0.1:5760"
      else:
         s1=s1[0]
      print(s1)
      try:
         global vehicle 
         vehicle= connect1(s1)
         print(vehicle)
      except Exception as e:
         print(f"Failed to connect: {str(e)}")

      vehicle.wait_ready('autopilot_version')
      print(vehicle.location.global_relative_frame)
      if(int(vehicle.location.global_relative_frame.alt)==0):
         return render_template('takeoff.html',lat=vehicle.location.global_relative_frame.lat,long=vehicle.location.global_relative_frame.lon)
      else:
         return render_template('Goto.html',lat=vehicle.location.global_relative_frame.lat,long=vehicle.location.global_relative_frame.lon)
def connect1(s):
   # vehicle = connect(s, wait_ready=True,baud=56700,heartbeat_timeout=100,timeout=100)
   vehicle = connect(s, wait_ready=True)
   print("\nConnecting to vehicle on: %s" % s)
   vehicle.wait_ready('autopilot_version')
   print(vehicle.battery,vehicle.heading)
   return vehicle
@app.route("/index")
def index():
    return render_template("index.html")
@app.route('/main',methods=['POST'])
def arm_and_takeoff():
   global vehicle
   if(int(vehicle.location.global_relative_frame.alt)==0):
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
            socketio.emit('parameters', {'data': altitude})
            if vehicle.location.global_relative_frame.alt >= alt * 0.95:
                  print("Reached target altitude")
                  socketio.emit('parameters',{'data':alt})
                  break
            time.sleep(1)
            # render_template("index.html",alt=vehicle.location.global_relative_frame.alt,dir=vehicle.heading,speed=vehicle.airspeed,connectionSpeed=x)
         print(vehicle.battery,vehicle.heading)
         # render_template("index.html",alt=vehicle.location.global_relative_frame.alt,dir=vehicle.heading,speed=vehicle.airspeed,connectionSpeed=x)
         return render_template("index.html")
   else:
      long=float(request.form['long'])
      lat=float(request.form['lat'])
      alt=float(request.form['alt'])
      point1 = LocationGlobalRelative(lat,long,alt)
      point1.yaw=0.0
      if(vehicle.mode!="GUIDED"):
         vehicle.mode = VehicleMode("GUIDED")
      vehicle.armed = True
      while not vehicle.armed:
         print(" Waiting for arming...")
         time.sleep(1)
      if curr <= changealtitude:
        inc = True
      print("goto!")
      vehicle.simple_goto(point1)
      while True:
         print(" Altitude: ", vehicle.location.global_relative_frame.alt,int(vehicle.location.global_relative_frame.lat*1000) ,int(lat*1000), int(vehicle.location.global_relative_frame.lon*1000) ,int(1000*long))
      # Break and return from function just below target altitude.
         if int(vehicle.location.global_relative_frame.lat*1000) ==int(lat*1000) and int(vehicle.location.global_relative_frame.lon*1000) ==int(1000*long):
            newaltitude = vehicle.location.global_relative_frame.alt
            print("Altitude: ", newaltitude)
            socketio.emit('parameters', {'data': newaltitude})
            if newaltitude >= alt * 0.95 and inc:
                  print(f"Reached new target altitude: {newaltitude}")
                  socketio.emit('parameters', {'data': alt})
                  break
            elif newaltitude <= (alt + 0.5) and inc == False:
                  print(f"Reached new target altitude: {newaltitude}")
                  socketio.emit('parameters', {'data': alt})
                  break
            time.sleep(1)
         time.sleep(1)
      # x=dataTrans()
         # x=50
      # return render_template("index.html",alt=vehicle.location.global_relative_frame.alt,dir=vehicle.heading,speed=vehicle.airspeed,connectionSpeed=50)
@app.route('/return_to_home')
def return_to_home():
   global vehicle
   try:
      vehicle.mode = VehicleMode("RTL")
      while not vehicle.mode.name == 'RTL':
         pass
      socketio.emit('parameters', {'data': 0})
      return render_template("About_page.html", message="Returning to Home (RTL)...")
   except Exception as e:
      # Handle any exceptions that might occur during the process
      return render_template("index.html", error=f"Error: {str(e)}")
@app.route('/Land')
def land():
   global vehicle
   try:
      vehicle.mode = VehicleMode("LAND")
      while not vehicle.mode.name == 'LAND':
         pass
      return render_template("takeoff.html", message="Returning to Home (RTL)...")
   except Exception as e:
      # Handle any exceptions that might occur during the process
      return render_template("index.html", error=f"Error: {str(e)}")
@app.route("/change_yaw",methods=['GET'])
def change_yaw():
   yaw = int(request.args['heading'])
   while True:
    
      vehicle.channels.overrides['4'] = 1500
      if yaw - 3 <= int(vehicle.heading) <= yaw + 3:
         break
      desired_yaw = 1549
      vehicle.channels.overrides['4'] = int(desired_yaw)
      time.sleep (1)
      print(vehicle.heading)
      vehicle.channels.overrides['4'] = 1500
   # x=dataTrans()
      # x=50
   return render_template("index.html",alt=vehicle.location.global_relative_frame.alt,dir=vehicle.heading,speed=vehicle.airspeed,connectionSpeed=50)
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
   

