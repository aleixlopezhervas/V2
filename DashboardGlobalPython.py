import json
import time
import math
import os
import tkinter as tk
from dronLink.Dron import Dron
import paho.mqtt.client as mqtt
import threading
import asyncio
import cv2
import numpy as np

# WebRTC
try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, MediaStreamTrack
    from aiortc.contrib.signaling import TcpSocketSignaling
    from av import VideoFrame
    import torch
    WEBRTC_AVAILABLE = True
except Exception:
    RTCPeerConnection = None
    RTCSessionDescription = None
    MediaStreamTrack = None
    TcpSocketSignaling = None
    VideoFrame = None
    torch = None
    WEBRTC_AVAILABLE = False

# Optional map widget
try:
    from tkintermapview import TkinterMapView
    MAP_AVAILABLE = True
except Exception:
    TkinterMapView = None
    MAP_AVAILABLE = False

# Map state globals
map_widget = None
drone_marker = None
heading_line = None
path_segments = []
path_points = []
_marker_icon = None
center_enabled = True

# Video/detection globals
video_receiver = None
selected_objects = []  # List of currently selected object IDs for detection

usuario = "aleix"

def restart():
    time.sleep(5)
    try:
        arm_takeOffBtn['text'] = 'Armar'
        arm_takeOffBtn['fg'] = 'black'
        arm_takeOffBtn['bg'] = 'dark orange'
        landBtn['text'] = 'Aterrizar'
        landBtn['fg'] = 'black'
        landBtn['bg'] = 'dark orange'
        RTLBtn['text'] = 'RTL'
        RTLBtn['fg'] = 'black'
        RTLBtn['bg'] = 'dark orange'
        previousBtn['fg'] = 'black'
        previousBtn['bg'] = 'dark orange'
    except Exception:
        pass


def create_fire_circle_icon(size=20):
    """Create a simple red circle PhotoImage to use as drone marker."""
    try:
        from PIL import Image, ImageDraw, ImageTk
        return_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(return_img)
        draw.ellipse((2, 2, size-3, size-3), fill=(255, 69, 0, 230))
        return ImageTk.PhotoImage(return_img)
    except Exception:
        pass
    # fallback: simple tk.PhotoImage
    img = tk.PhotoImage(width=size, height=size)
    cx = size // 2
    cy = size // 2
    r = (size - 6) // 2
    r2 = r*r
    for y in range(size):
        for x in range(size):
            dx = x - cx
            dy = y - cy
            if dx*dx + dy*dy <= r2:
                try:
                    img.put('#FF4500', (x, y))
                except Exception:
                    pass
    return img


def _perform_ui_update(telemetry_info):
    """Module-level UI updater. Runs in Tk main thread via .after()."""
    global map_widget, drone_marker, heading_line, path_points, path_segments, _marker_icon, center_enabled
    global altShowLbl, headingShowLbl, stateShowLbl

    try:
        lat = telemetry_info.get('lat')
        lon = telemetry_info.get('lon')
        alt = telemetry_info.get('alt')
        heading_val = telemetry_info.get('heading')
        state_val = telemetry_info.get('state')
    except Exception:
        return

    # update textual telemetry
    try:
        altShowLbl['text'] = '' if alt is None else round(alt, 2)
    except Exception:
        pass
    try:
        headingShowLbl['text'] = '' if heading_val is None else round(heading_val, 2)
    except Exception:
        pass
    try:
        stateShowLbl['text'] = '' if state_val is None else state_val
    except Exception:
        pass

    if not MAP_AVAILABLE or map_widget is None:
        return
    if lat is None or lon is None:
        return

    # prepare marker icon
    marker_icon = None
    try:
        if _marker_icon is None:
            _marker_icon = create_fire_circle_icon(size=20)
        marker_icon = _marker_icon
    except Exception:
        marker_icon = None

    # create or move marker
    try:
        if drone_marker is None:
            if marker_icon is not None:
                try:
                    drone_marker = map_widget.set_marker(lat, lon, text='', icon=marker_icon)
                except Exception:
                    drone_marker = map_widget.set_marker(lat, lon, text='')
                    try:
                        drone_marker.set_icon(marker_icon)
                    except Exception:
                        pass
                _marker_icon = marker_icon
            else:
                drone_marker = map_widget.set_marker(lat, lon, text='')
        else:
            try:
                drone_marker.set_position(lat, lon)
            except Exception:
                try:
                    drone_marker.delete()
                except Exception:
                    pass
                if marker_icon is not None:
                    try:
                        drone_marker = map_widget.set_marker(lat, lon, text='', icon=marker_icon)
                        _marker_icon = marker_icon
                    except Exception:
                        drone_marker = map_widget.set_marker(lat, lon, text='')
                else:
                    drone_marker = map_widget.set_marker(lat, lon, text='')
    except Exception:
        pass

    # trail
    try:
        now = time.time()
        path_points.append((lat, lon, now))
        cutoff = now - 10.0
        path_points[:] = [p for p in path_points if p[2] >= cutoff]
        try:
            for s in path_segments:
                try:
                    s.delete()
                except Exception:
                    pass
            path_segments.clear()
        except Exception:
            pass
        for i in range(len(path_points)-1):
            (lat1, lon1, t1) = path_points[i]
            (lat2, lon2, t2) = path_points[i+1]
            age = (now - t1) / 5.0
            if age < 0: age = 0
            if age > 1: age = 1
            r1,g1,b1 = (255,140,0)
            r2,g2,b2 = (255,220,180)
            r=int(r1+(r2-r1)*age)
            g=int(g1+(g2-g1)*age)
            b=int(b1+(b2-b1)*age)
            color = '#%02x%02x%02x' % (r,g,b)
            try:
                seg = map_widget.set_path([(lat1, lon1), (lat2, lon2)], color=color, width=3)
            except Exception:
                seg = map_widget.set_path([(lat1, lon1), (lat2, lon2)])
            path_segments.append(seg)
    except Exception:
        pass

    # heading
    try:
        if heading_val is not None:
            dist_m = 5.0
            theta = math.radians(float(heading_val))
            dy = dist_m * math.cos(theta)
            dx = dist_m * math.sin(theta)
            delta_lat = (dy / 111320.0)
            delta_lon = dx / (111320.0 * math.cos(math.radians(lat)) + 1e-12)
            lat2 = lat + delta_lat
            lon2 = lon + delta_lon
            try:
                if heading_line is not None:
                    heading_line.delete()
            except Exception:
                pass
            try:
                heading_line = map_widget.set_path([(lat, lon), (lat2, lon2)], color='#00FF00', width=3)
            except Exception:
                heading_line = None
    except Exception:
        pass

    # center
    try:
        if center_enabled:
            map_widget.set_position(lat, lon)
    except Exception:
        pass

    try:
        map_widget.update()
    except Exception:
        pass


def showTelemetryInfo(telemetry_info):
    """Collect telemetry and schedule UI update on the main thread."""
    try:
        snapshot = {
            'lat': telemetry_info.get('lat'),
            'lon': telemetry_info.get('lon'),
            'alt': telemetry_info.get('alt'),
            'heading': telemetry_info.get('heading'),
            'state': telemetry_info.get('state')
        }
    except Exception:
        return

    try:
        if MAP_AVAILABLE and map_widget is not None:
            map_widget.after(0, lambda: _perform_ui_update(snapshot))
        else:
            try:
                altShowLbl.after(0, lambda: _perform_ui_update(snapshot))
            except Exception:
                _perform_ui_update(snapshot)
    except Exception:
        try:
            _perform_ui_update(snapshot)
        except Exception:
            pass


# ==================== Video/Detection Classes ====================
class Detector:
    def __init__(self):
        global torch
        self.model = None
        if WEBRTC_AVAILABLE and torch is not None:
            try:
                self.model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
                self.model.eval()
            except Exception:
                self.model = None

    def detect(self, frame, objectID):
        if self.model is None:
            return False, None
        try:
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.model(img)
            for *box, conf, cls in results.xyxy[0]:
                if int(cls.item()) == objectID:
                    x1, y1, x2, y2 = map(int, box)
                    return True, [x1, y1, x2, y2]
            return False, None
        except Exception:
            return False, None


class VideoReceiver:
    # Mapeo de IDs YOLO a nombres de objetos
    OBJECT_NAMES = {
        0: 'Persona',
        1: 'Bicicleta',
        2: 'Coche',
        3: 'Moto',
        4: 'Avión',
        5: 'Autobús',
        39: 'Botella',
        41: 'Taza',
        46: 'Plátano',
        53: 'Pizza',
        74: 'Reloj'
    }
    
    def __init__(self):
        self.track = None
        self.detector = Detector()
        self.objectIDs = []  # List of object IDs to detect

    def setObjects(self, objectIDs):
        """Set list of objects to detect"""
        self.objectIDs = objectIDs

    async def handle_track(self, track):
        print("Video receiver: Handling track")
        self.track = track
        frame_count = 0
        detection_cache = {}  # Cache para mostrar detecciones más tiempo
        while True:
            try:
                frame = await asyncio.wait_for(track.recv(), timeout=5.0)
                frame_count += 1
                if isinstance(frame, VideoFrame):
                    frame = frame.to_ndarray(format='bgr24')
                elif isinstance(frame, np.ndarray):
                    pass
                else:
                    continue

                # Limpiar cache antiguo (más de 30 frames de antigüedad)
                detection_cache = {k: v for k, v in detection_cache.items() if frame_count - v['frame'] < 30}

                # Detect all selected objects (cada 15 frames)
                if self.objectIDs:
                    if frame_count % 15 == 0:
                        for objectID in self.objectIDs:
                            detectado, rectangulo = self.detector.detect(frame, objectID)
                            if detectado and rectangulo:
                                detection_cache[objectID] = {'rect': rectangulo, 'frame': frame_count}

                # Dibujar todas las detecciones cacheadas
                for objectID, detection_info in detection_cache.items():
                    x1, y1, x2, y2 = detection_info['rect']
                    # Rectángulo verde
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    # Texto con nombre del objeto
                    object_name = self.OBJECT_NAMES.get(objectID, f'ID:{objectID}')
                    cv2.putText(frame, object_name, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                cv2.imshow('Video Stream', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            except asyncio.TimeoutError:
                print('Timeout waiting for frame, continuing...')
            except Exception as e:
                print(f'Error in handle_track: {e}')
                if 'Connection' in str(e):
                    break
        print('Exiting video receiver')


async def videoReceiver_main():
    IP_server = "localhost"
    signaling = TcpSocketSignaling(IP_server, 9999)
    pc = RTCPeerConnection()

    global video_receiver
    video_receiver = VideoReceiver()

    try:
        await signaling.connect()

        @pc.on('track')
        def on_track(track):
            if isinstance(track, MediaStreamTrack):
                print(f'Receiving {track.kind} track')
                asyncio.ensure_future(video_receiver.handle_track(track))

        @pc.on('connectionstatechange')
        async def on_connectionstatechange():
            print(f'Connection state is {pc.connectionState}')

        print('Waiting for offer from sender...')
        offer = await signaling.receive()
        print('Offer received')
        await pc.setRemoteDescription(offer)
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await signaling.send(pc.localDescription)
        print('WebRTC connection established')

        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Error in video receiver: {e}")
    finally:
        await pc.close()


def videoThread():
    asyncio.run(videoReceiver_main())


def start_video():
    if WEBRTC_AVAILABLE:
        threading.Thread(target=videoThread, daemon=True).start()
    else:
        print("WebRTC not available")


def setDetectionObject(objectID):
    """Toggle object selection for detection"""
    global video_receiver, selected_objects
    if objectID in selected_objects:
        selected_objects.remove(objectID)
    else:
        selected_objects.append(objectID)
    
    # Update video receiver with new list
    if video_receiver:
        video_receiver.setObjects(selected_objects)
    
    print(f'Selected objects: {selected_objects}')


def detect_person():
    setDetectionObject(0)


def detect_bicycle():
    setDetectionObject(1)


def detect_car():
    setDetectionObject(2)


def detect_motorcycle():
    setDetectionObject(3)


def detect_airplane():
    setDetectionObject(4)


def detect_bus():
    setDetectionObject(5)


def detect_bottle():
    setDetectionObject(39)


def detect_cup():
    setDetectionObject(41)


def platano():
    setDetectionObject(46)


def clock():
    setDetectionObject(74)


def pizza():
    setDetectionObject(53)


# ==================== End Video/Detection ====================


def connect():
    global dron, speedSldr
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/connect')
    except Exception:
        pass
    try:
        connectBtn['text'] = 'Conectado'
        connectBtn['fg'] = 'white'
        connectBtn['bg'] = 'green'
        speedSldr.set(1)
    except Exception:
        pass


def takeoff():
    global dron
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/arm_takeOff')
        arm_takeOffBtn['text'] = 'Despegando...'
        arm_takeOffBtn['fg'] = 'black'
        arm_takeOffBtn['bg'] = 'yellow'
    except Exception:
        pass


def land():
    global dron
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/Land')
        landBtn['text'] = 'Aterrizando ...'
        landBtn['fg'] = 'black'
        landBtn['bg'] = 'yellow'
    except Exception:
        pass


def RTL():
    global dron
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/RTL')
        RTLBtn['text'] = 'Retornando ...'
        RTLBtn['fg'] = 'black'
        RTLBtn['bg'] = 'yellow'
    except Exception:
        pass


def go(direction, btn):
    global dron, previousBtn
    if previousBtn:
        previousBtn['fg'] = 'black'
        previousBtn['bg'] = 'dark orange'
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/go', direction)
    except Exception:
        pass
    btn['fg'] = 'white'
    btn['bg'] = 'green'
    previousBtn = btn


def startTelem():
    global dron
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/startTelemetry')
    except Exception:
        pass


def stopTelem():
    global dron, altShowLbl, headingShowLbl, stateShowLbl
    try:
        client.publish(f'{usuario}/autopilotServiceDemo/stopTelemetry')
        altShowLbl['text'] = ''
        headingShowLbl['text'] = ''
        stateShowLbl['text'] = ''
    except Exception:
        pass


def changeHeading(event):
    global dron, gradesSldr
    try:
        heading = gradesSldr.get()
        client.publish(f'{usuario}/autopilotServiceDemo/changeHeading', str(heading))
    except Exception:
        pass


def changeNavSpeed(event):
    global dron, speedSldr
    try:
        speed = speedSldr.get()
        client.publish(f'{usuario}/autopilotServiceDemo/changeNavSpeed', str(speed))
    except Exception:
        pass


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("connected OK Returned code=", rc)
    else:
        print("Bad connection Returned code=", rc)


def on_message(client, userdata, message):
    if message.topic == f'autopilotServiceDemo/{usuario}/telemetryInfo':
        try:
            telemetry_info = json.loads(message.payload)
            showTelemetryInfo(telemetry_info)
        except Exception:
            pass
    if message.topic == f'autopilotServiceDemo/{usuario}/connected':
        try:
            connectBtn['text'] = 'Conectado'
            connectBtn['fg'] = 'white'
            connectBtn['bg'] = 'green'
        except Exception:
            pass
    if message.topic == f'autopilotServiceDemo/{usuario}/flying':
        try:
            arm_takeOffBtn['text'] = 'En el aire'
            arm_takeOffBtn['fg'] = 'white'
            arm_takeOffBtn['bg'] = 'green'
        except Exception:
            pass
    if message.topic == f'autopilotServiceDemo/{usuario}/landed':
        try:
            landBtn['text'] = 'En tierra'
            landBtn['fg'] = 'white'
            landBtn['bg'] = 'green'
            restart()
        except Exception:
            pass
    if message.topic == f'autopilotServiceDemo/{usuario}/atHome':
        try:
            RTLBtn['text'] = 'En tierra'
            RTLBtn['fg'] = 'white'
            RTLBtn['bg'] = 'green'
            restart()
        except Exception:
            pass


def crear_ventana():
    global dron, client, altShowLbl, headingShowLbl, speedSldr, gradesSldr, stateShowLbl
    global connectBtn, arm_takeOffBtn, landBtn, RTLBtn, previousBtn, map_widget, _marker_icon, center_enabled

    client = mqtt.Client(f"Dashboard_{usuario}", transport="websockets")
    client.ws_set_options(path="/mqtt")

    broker_address = "dronseetac.upc.edu"
    broker_port = 8000
    client.username_pw_set("dronsEETAC", "mimara1456.")

    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(broker_address, broker_port)
    client.subscribe(f'autopilotServiceDemo/{usuario}/#')
    client.loop_start()

    dron = Dron()
    previousBtn = None

    ventana = tk.Tk()
    ventana.title("Dashboard Global con Mapa")
    ventana.geometry("1200x700")

    # left and right frames
    left_frame = tk.Frame(ventana, bd=0, relief=tk.FLAT)
    right_frame = tk.Frame(ventana, bd=0, relief=tk.FLAT, width=420, height=640)
    left_frame.grid(row=0, column=0, sticky='nsew')
    right_frame.grid(row=0, column=1, sticky='nsew')
    ventana.columnconfigure(0, weight=1)
    ventana.columnconfigure(1, weight=1)
    ventana.rowconfigure(0, weight=1)

    # LEFT FRAME CONTROLS
    connectBtn = tk.Button(left_frame, text='Conectar', bg='dark orange', command=connect)
    connectBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    arm_takeOffBtn = tk.Button(left_frame, text='Despegar', bg='dark orange', command=takeoff)
    arm_takeOffBtn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    def toggle_center():
        global center_enabled
        center_enabled = not center_enabled
        btn_centrar['text'] = 'Centrar: ON' if center_enabled else 'Centrar: OFF'

    btn_centrar = tk.Button(left_frame, text='Centrar: ON', width=12, command=toggle_center)
    btn_centrar.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    gradesSldr = tk.Scale(left_frame, label='Grados:', resolution=5, from_=0, to=360, orient=tk.HORIZONTAL)
    gradesSldr.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    gradesSldr.set(180)
    gradesSldr.bind('<ButtonRelease-1>', changeHeading)

    landBtn = tk.Button(left_frame, text='Aterrizar', bg='dark orange', command=land)
    landBtn.grid(row=4, column=0, padx=5, pady=5, sticky='ew')
    RTLBtn = tk.Button(left_frame, text='RTL', bg='dark orange', command=RTL)
    RTLBtn.grid(row=4, column=1, padx=5, pady=5, sticky='ew')

    navFrame = tk.LabelFrame(left_frame, text='Navegación', bd=0, relief=tk.FLAT)
    navFrame.grid(row=5, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    for r in range(3):
        navFrame.rowconfigure(r, weight=1)
    for c in range(3):
        navFrame.columnconfigure(c, weight=1)

    NWBtn = tk.Button(navFrame, text='NW', bg='dark orange', command=lambda: go('NorthWest', NWBtn))
    NWBtn.grid(row=0, column=0, padx=2, pady=2, sticky='nsew')
    NoBtn = tk.Button(navFrame, text='No', bg='dark orange', command=lambda: go('North', NoBtn))
    NoBtn.grid(row=0, column=1, padx=2, pady=2, sticky='nsew')
    NEBtn = tk.Button(navFrame, text='NE', bg='dark orange', command=lambda: go('NorthEast', NEBtn))
    NEBtn.grid(row=0, column=2, padx=2, pady=2, sticky='nsew')

    WeBtn = tk.Button(navFrame, text='We', bg='dark orange', command=lambda: go('West', WeBtn))
    WeBtn.grid(row=1, column=0, padx=2, pady=2, sticky='nsew')
    StopBtn = tk.Button(navFrame, text='St', bg='dark orange', command=lambda: go('Stop', StopBtn))
    StopBtn.grid(row=1, column=1, padx=2, pady=2, sticky='nsew')
    EaBtn = tk.Button(navFrame, text='Ea', bg='dark orange', command=lambda: go('East', EaBtn))
    EaBtn.grid(row=1, column=2, padx=2, pady=2, sticky='nsew')

    SWBtn = tk.Button(navFrame, text='SW', bg='dark orange', command=lambda: go('Down', SWBtn))
    SWBtn.grid(row=2, column=0, padx=2, pady=2, sticky='nsew')
    SoBtn = tk.Button(navFrame, text='So', bg='dark orange', command=lambda: go('South', SoBtn))
    SoBtn.grid(row=2, column=1, padx=2, pady=2, sticky='nsew')
    SEBtn = tk.Button(navFrame, text='SE', bg='dark orange', command=lambda: go('Up', SEBtn))
    SEBtn.grid(row=2, column=2, padx=2, pady=2, sticky='nsew')

    speedSldr = tk.Scale(left_frame, label='Velocidad (m/s):', resolution=1, from_=0, to=20, orient=tk.HORIZONTAL)
    speedSldr.grid(row=6, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    speedSldr.bind('<ButtonRelease-1>', changeNavSpeed)

    StartTelemBtn = tk.Button(left_frame, text='Empezar telemetría', bg='dark orange', command=startTelem)
    StartTelemBtn.grid(row=7, column=0, padx=5, pady=5, sticky='ew')
    StopTelemBtn = tk.Button(left_frame, text='Parar telemetría', bg='dark orange', command=stopTelem)
    StopTelemBtn.grid(row=7, column=1, padx=5, pady=5, sticky='ew')

    telemetryFrame = tk.LabelFrame(left_frame, text='Telemetría', bd=0, relief=tk.FLAT)
    telemetryFrame.grid(row=8, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    telemetryFrame.columnconfigure(0, weight=1)
    telemetryFrame.columnconfigure(1, weight=1)
    telemetryFrame.columnconfigure(2, weight=1)

    altLbl = tk.Label(telemetryFrame, text='Altitud')
    altLbl.grid(row=0, column=0, padx=5, pady=5)
    headingLbl = tk.Label(telemetryFrame, text='Heading')
    headingLbl.grid(row=0, column=1, padx=5, pady=5)
    stateLbl = tk.Label(telemetryFrame, text='Estado')
    stateLbl.grid(row=0, column=2, padx=5, pady=5)

    altShowLbl = tk.Label(telemetryFrame, text='')
    altShowLbl.grid(row=1, column=0, padx=5, pady=5)
    headingShowLbl = tk.Label(telemetryFrame, text='')
    headingShowLbl.grid(row=1, column=1, padx=5, pady=5)
    stateShowLbl = tk.Label(telemetryFrame, text='')
    stateShowLbl.grid(row=1, column=2, padx=5, pady=5)

    # Video and Detection Section
    videoFrame = tk.LabelFrame(left_frame, text='Video/Detección', bd=0, relief=tk.FLAT)
    videoFrame.grid(row=9, column=0, columnspan=2, padx=5, pady=5, sticky='ew')
    videoFrame.columnconfigure(0, weight=1)
    videoFrame.columnconfigure(1, weight=1)

    startVideoBtn = tk.Button(videoFrame, text='Recibir Vídeo', bg='dark orange', command=start_video)
    startVideoBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='ew')

    # Detection objects grid
    detectFrame = tk.Frame(videoFrame)
    detectFrame.grid(row=1, column=0, columnspan=2, sticky='ew')
    detectFrame.columnconfigure(0, weight=1)
    detectFrame.columnconfigure(1, weight=1)
    detectFrame.columnconfigure(2, weight=1)

    # Create buttons with toggle functionality
    def make_toggle_button(frame, text, objectID, row, col):
        """Create a button that toggles object selection"""
        btn_state = {'selected': False}
        def toggle_object():
            setDetectionObject(objectID)
            btn_state['selected'] = not btn_state['selected']
            btn['bg'] = 'green' if btn_state['selected'] else 'light blue'
            btn['fg'] = 'white' if btn_state['selected'] else 'black'
        
        btn = tk.Button(frame, text=text, bg='light blue', command=toggle_object)
        btn.grid(row=row, column=col, padx=2, pady=2, sticky='ew')
        return btn

    platano_btn = make_toggle_button(detectFrame, 'Plátano', 46, 0, 0)
    clock_btn = make_toggle_button(detectFrame, 'Reloj', 74, 0, 1)
    pizza_btn = make_toggle_button(detectFrame, 'Pizza', 53, 0, 2)

    detect_airplane_btn = make_toggle_button(detectFrame, 'Avión', 4, 1, 0)
    detect_car_btn = make_toggle_button(detectFrame, 'Coche', 2, 1, 1)
    detect_motorcycle_btn = make_toggle_button(detectFrame, 'Moto', 3, 1, 2)

    # RIGHT FRAME MAP
    if MAP_AVAILABLE:
        try:
            map_widget = TkinterMapView(right_frame, width=420, height=640, corner_radius=0)
            try:
                mapbox_token = os.environ.get('MAPBOX_TOKEN') or os.environ.get('MAPBOX_API_KEY')
                if mapbox_token:
                    mapbox_url = f'https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={mapbox_token}'
                    map_widget.set_tile_server(mapbox_url, max_zoom=20)
                else:
                    map_widget.set_tile_server('https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', max_zoom=19)
            except Exception:
                try:
                    esri = 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                    map_widget.set_tile_server(esri, max_zoom=19)
                except Exception:
                    pass
            map_widget.pack(fill=tk.BOTH, expand=True)
            map_widget.set_zoom(16)
            map_widget.set_position(0, 0)

            # Layers selector
            layerVar = tk.StringVar(value='Streets')
            def change_map_layer(sel):
                try:
                    lat, lon = map_widget.get_position()
                    z = map_widget.get_zoom()
                except Exception:
                    lat = 0; lon = 0; z = 16
                mapbox_token = os.environ.get('MAPBOX_TOKEN') or os.environ.get('MAPBOX_API_KEY')
                if mapbox_token:
                    streets_url = f'https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/256/{{z}}/{{x}}/{{y}}@2x?access_token={mapbox_token}'
                    streets_maxz = 20
                else:
                    streets_url = 'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png'
                    streets_maxz = 19
                candidates = {
                    'Streets': (streets_url, streets_maxz),
                    'Satellite': ('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', 19),
                }
                try:
                    url, maxz = candidates.get(sel, candidates['Streets'])
                    map_widget.set_tile_server(url, max_zoom=maxz)
                    try:
                        map_widget.set_position(lat, lon)
                        cur_z = int(z) if isinstance(z, (int, float)) else map_widget.get_zoom()
                        tmp_z = cur_z - 1 if cur_z > 0 else cur_z + 1
                        map_widget.set_zoom(tmp_z)
                        def _restore():
                            try:
                                map_widget.set_zoom(cur_z)
                                map_widget.set_position(lat, lon)
                            except Exception:
                                pass
                        map_widget.after(120, _restore)
                    except Exception:
                        pass
                except Exception:
                    pass

            layer_frame = tk.Frame(right_frame)
            layer_frame.pack(fill='x')
            tk.Label(layer_frame, text='Vista:').pack(side='left')
            tk.OptionMenu(layer_frame, layerVar, 'Streets', 'Satellite', command=change_map_layer).pack(side='left')

            # Map click handler - publish MQTT goTo command (Global mode uses MQTT, not direct dron.goto)
            def _on_map_click(data):
                try:
                    if isinstance(data, (list, tuple)):
                        lat, lon = float(data[0]), float(data[1])
                    else:
                        lat = getattr(data, 'lat', None) or getattr(data, 'latitude', None) or getattr(data, 'y', None)
                        lon = getattr(data, 'lng', None) or getattr(data, 'longitude', None) or getattr(data, 'x', None)
                        lat = float(lat)
                        lon = float(lon)
                except Exception:
                    try:
                        ex = getattr(data, 'x', None)
                        ey = getattr(data, 'y', None)
                        if ex is not None and ey is not None:
                            try:
                                latlon = map_widget.get_position(ex, ey)
                                if latlon:
                                    lat, lon = latlon
                                else:
                                    lat, lon = map_widget.convert_canvas_coords_to_decimal_coords(ex, ey)
                            except Exception:
                                lat, lon = map_widget.convert_canvas_coords_to_decimal_coords(ex, ey)
                        else:
                            return
                    except Exception:
                        return

                # Get current altitude from telemetry label
                try:
                    current_alt = None
                    try:
                        current_alt = float(altShowLbl['text'])
                    except Exception:
                        current_alt = None
                    if current_alt is None or current_alt == 0:
                        current_alt = 10.0
                except Exception:
                    current_alt = 10.0

                # Publish MQTT goTo command to AutopilotService
                try:
                    payload = json.dumps({'lat': lat, 'lon': lon, 'alt': current_alt})
                    client.publish(f'{usuario}/autopilotServiceDemo/goTo', payload)
                    # Show overlay with coordinates
                    try:
                        if hasattr(map_widget, '_coord_overlay') and map_widget._coord_overlay:
                            try:
                                map_widget._coord_overlay.destroy()
                            except Exception:
                                pass
                        overlay = tk.Label(map_widget, text=f'{lat:.6f}, {lon:.6f}', bg='white', fg='black', bd=1, relief=tk.SOLID)
                        overlay.place(relx=0.02, rely=0.02)
                        map_widget._coord_overlay = overlay
                        overlay.after(1000, lambda: (overlay.destroy(), setattr(map_widget, '_coord_overlay', None)))
                        try:
                            stateShowLbl['text'] = f'GOTO -> {round(lat,6)},{round(lon,6)}'
                        except Exception:
                            pass
                    except Exception:
                        pass
                except Exception:
                    pass

            try:
                if hasattr(map_widget, 'add_left_click_map_command'):
                    map_widget.add_left_click_map_command(_on_map_click)
                elif hasattr(map_widget, 'add_left_click_map_callback'):
                    map_widget.add_left_click_map_callback(_on_map_click)
                elif hasattr(map_widget, 'set_click_callback'):
                    map_widget.set_click_callback(lambda la, lo: _on_map_click((la, lo)))
                else:
                    cvs = getattr(map_widget, 'canvas', None) or getattr(map_widget, 'map_canvas', None)
                    if cvs:
                        def _pixel_click(evt):
                            try:
                                latlon = None
                                try:
                                    latlon = map_widget.get_position(evt.x, evt.y)
                                except Exception:
                                    try:
                                        latlon = map_widget.convert_canvas_coords_to_decimal_coords(evt.x, evt.y)
                                    except Exception:
                                        latlon = None
                                if latlon:
                                    _on_map_click(latlon)
                            except Exception:
                                pass
                        cvs.bind('<Button-1>', _pixel_click)
            except Exception:
                pass
        except Exception as e:
            tk.Label(right_frame, text=f'Error iniciando mapa: {e}').pack(fill=tk.BOTH, expand=True)
    else:
        tk.Label(right_frame, text='Instala tkintermapview:\npython -m pip install tkintermapview').pack(fill=tk.BOTH, expand=True)

    return ventana


if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()


