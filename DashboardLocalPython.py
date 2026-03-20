##########  INSTALAR ##########
# pymavlink
###############################

import tkinter as tk
from tkinter import simpledialog, messagebox
from dronLink.Dron import Dron

# Optional map support using tkintermapview. If not installed, we show an instruction.
try:
    from tkintermapview import TkinterMapView
    MAP_AVAILABLE = True
except Exception:
    TkinterMapView = None
    MAP_AVAILABLE = False

# Globals for map and drone marker
map_widget = None
drone_marker = None
path_points = []
path_obj = None
map_centered = False



def showTelemetryInfo (telemetry_info):
    global heading, altitude, groundSpeed, state
    global altShowLbl, headingShowLbl, stateShowLbl, speedShowLbl
    altShowLbl['text'] = round (telemetry_info['alt'],2)
    headingShowLbl['text'] =  round(telemetry_info['heading'],2)
    stateShowLbl['text'] = telemetry_info['state']
    speedShowLbl['text'] = round(telemetry_info['groundSpeed'],2)

    # If telemetry contains lat/lon and map is available, update the marker
    try:
        lat = telemetry_info.get('lat') if isinstance(telemetry_info, dict) else None
        lon = telemetry_info.get('lon') if isinstance(telemetry_info, dict) else None
        global map_widget, drone_marker, path_points, path_obj, map_centered
        if MAP_AVAILABLE and map_widget is not None and lat is not None and lon is not None:
            # Update or create marker
            if drone_marker is None:
                drone_marker = map_widget.set_marker(lat, lon, text='Drone')
            else:
                try:
                    drone_marker.set_position(lat, lon)
                except Exception:
                    try:
                        drone_marker.delete()
                    except Exception:
                        pass
                    drone_marker = map_widget.set_marker(lat, lon, text='Drone')

            # Append to path and update a polyline
            try:
                point = (lat, lon)
                path_points.append(point)
                # Keep the path reasonably sized
                if len(path_points) > 500:
                    path_points = path_points[-500:]
                if path_obj is None:
                    path_obj = map_widget.set_path(path_points)
                else:
                    # update by recreating path (tkintermapview doesn't have simple update API)
                    try:
                        path_obj.delete()
                    except Exception:
                        pass
                    path_obj = map_widget.set_path(path_points)
            except Exception:
                pass

            # Center map the first time we get a fix
            if not map_centered:
                try:
                    map_widget.set_position(lat, lon)
                    map_centered = True
                except Exception:
                    pass
    except Exception:
        # keep UI resilient
        pass


def connect ():
    global dron, speedSldr
    # connect to MAVProxy TCP output (use 5770 for local dashboard)
    connection_string = 'tcp:127.0.0.1:5763'
    baud = 115200
    dron.connect(connection_string,baud)
    # cambiamos el color del boton
    connectBtn['text'] = 'Conectado'
    connectBtn['fg'] = 'white'
    connectBtn['bg'] = 'green'
    # fijamos la velocidad por defecto en el slider
    speedSldr.set(1)

def arm ():
    global dron
    dron.arm()
    armBtn['text'] = 'Armado'
    armBtn['fg'] = 'white'
    armBtn['bg'] = 'green'

def inTheAir ():
    # ya ha alcanzado la altura de despegue
    takeOffBtn['text'] = 'En el aire'
    takeOffBtn['fg'] = 'white'
    takeOffBtn['bg'] = 'green'


def takeoff ():
    global dron
    # Pedir la altitud deseada
    altitude = simpledialog.askfloat(
        "Altitud de despegue",
        "Introduce la altitud en metros:\n(Rango: 1-100m)",
        minvalue=1.0,
        maxvalue=100.0
    )

    # Si el usuario cancela el diálogo, no hacemos nada
    if altitude is None:
        return

    # Primero intentamos armar el dron
    try:
        dron.arm()
        armBtn['text'] = 'Armado'
        armBtn['fg'] = 'white'
        armBtn['bg'] = 'green'
    except Exception as e:
        # Mostrar advertencia si el arming falla, pero seguimos intentando el despegue
        try:
            message = str(e)
        except Exception:
            message = 'Error al armar.'
        # No usar messagebox en callbacks que puedan ser llamados desde hilos; aquí es UI thread
        from tkinter import messagebox
        messagebox.showwarning('Armar fallo', f'No se pudo armar el dron: {message}')

    # Realizar el despegue a la altitud indicada (no bloqueante)
    alt_int = int(altitude)
    try:
        dron.takeOff(alt_int, blocking=False, callback=inTheAir)
        takeOffBtn['text'] = 'Despegando...'
        takeOffBtn['fg'] = 'black'
        takeOffBtn['bg'] = 'yellow'
    except Exception as e:
        from tkinter import messagebox
        messagebox.showerror('Takeoff fallo', f'No se pudo iniciar el despegue: {e}')

def onLanded():
    landBtn['text'] = 'En tierra'
    landBtn['fg'] = 'white'
    landBtn['bg'] = 'green'

def onRTLCompleted():
    RTLBtn['text'] = 'En tierra'
    RTLBtn['fg'] = 'white'
    RTLBtn['bg'] = 'green'

def land ():
    global dron
    # llamada no bloqueante con callback
    dron.Land(blocking=False, callback=onLanded)
    landBtn['text'] = 'Aterrizando...'
    landBtn['fg'] = 'black'
    landBtn['bg'] = 'yellow'

def RTL():
    global dron
    # llamada no bloqueante con callback
    dron.RTL(blocking=False, callback=onRTLCompleted)
    dron.RTL()
    RTLBtn['text'] = 'Volviendo...'
    RTLBtn['fg'] = 'black'
    RTLBtn['bg'] = 'yellow'

def go (direction, btn):
    global dron, previousBtn
    # cambio el color del anterior boton clicado (si lo hay)
    if previousBtn:
        previousBtn['fg'] = 'black'
        previousBtn['bg'] = 'dark orange'

    # navegamos en la dirección indicada
    dron.go (direction)
    # pongo en verde el boton clicado
    btn['fg'] = 'white'
    btn['bg'] = 'green'
    # tomo nota de que este es el último botón clicado
    previousBtn = btn


def startTelem():
    global dron
    # pedimos datos de telemetría que se procesarán en showTelemetryInfo a medida que vayan llegando
    dron.send_telemetry_info(showTelemetryInfo)

def stopTelem():
    global dron
    dron.stop_sending_telemetry_info()

def changeHeading (event):
    global dron
    global gradesSldr
    # cambiamos el heading según se haya seleccionado en el slider
    dron.changeHeading(int (gradesSldr.get()))

def changeAltitude (event):
    global dron
    global altitudeSldr
    # cambiamos la altitud según se haya seleccionado en el slider
    dron.change_altitude(int (altitudeSldr.get()))

def changeNavSpeed (event):
    global dron
    global speedSldr
    # cambiamos la velocidad de navagación según se haya seleccionado en el slider
    dron.changeNavSpeed(float (speedSldr.get()))



def crear_ventana():
    global dron
    global  altShowLbl, headingShowLbl,  speedSldr, gradesSldr, stateShowLbl, speedShowLbl, altitudeSldr
    global connectBtn, armBtn, takeOffBtn, landBtn, RTLBtn
    global previousBtn # aqui guardaré el ultimo boton de navegación clicado

    dron = Dron()

    previousBtn = None

    ventana = tk.Tk()
    ventana.title("Dashboard con conexión directa")

    # Create left frame for controls and right frame for map
    left_frame = tk.Frame(ventana)
    right_frame = tk.Frame(ventana, width=400, height=600)
    left_frame.grid(row=0, column=0, rowspan=10, sticky=tk.N + tk.S + tk.E + tk.W)
    right_frame.grid(row=0, column=1, rowspan=10, sticky=tk.N + tk.S + tk.E + tk.W)
    ventana.columnconfigure(0, weight=3)
    ventana.columnconfigure(1, weight=1)

    # Disponemos los botones, indicando qué función ejecutar cuando se clica cada uno de ellos
    # Los tres primeros ocupan las dos columnas de la fila en la que se colocan
    connectBtn = tk.Button(left_frame, text="Conectar", bg="dark orange", command = connect)
    connectBtn.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    armBtn = tk.Button(left_frame, text="Armar", bg="dark orange", command=arm)
    armBtn.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    takeOffBtn = tk.Button(left_frame, text="Despegar", bg="dark orange", command=takeoff)
    takeOffBtn.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Slider para seleccionar el heading
    gradesSldr = tk.Scale(left_frame, label="Grados:", resolution=5, from_=0, to=360, tickinterval=45,
                              orient=tk.HORIZONTAL)
    gradesSldr.grid(row=3, column=0, columnspan=2,padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    gradesSldr.set(180)
    gradesSldr.bind("<ButtonRelease-1>", changeHeading)

    # Slider para seleccionar la altitud
    altitudeSldr = tk.Scale(left_frame, label="Altitud (m):", resolution=1, from_=0, to=100, tickinterval=10,
                              orient=tk.HORIZONTAL)
    altitudeSldr.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    altitudeSldr.bind("<ButtonRelease-1>", changeAltitude)

    # los dos siguientes están en la misma fila están en la misma fila
    landBtn = tk.Button(left_frame, text="aterrizar", bg="dark orange", command=land)
    landBtn.grid(row=5, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    RTLBtn = tk.Button(left_frame, text="RTL", bg="dark orange", command=RTL)
    RTLBtn.grid(row=5, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # este es el frame para la navegación. Pequeña matriz de 3 x 3 botones
    # con el valor de padx hacemos que se introduzca un espacio en blanco a la derecha,
    navFrame = tk.LabelFrame (left_frame, text = "Navegación")
    navFrame.grid(row=6, column=0, columnspan = 2, padx=50, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    navFrame.rowconfigure(0, weight=1)
    navFrame.rowconfigure(1, weight=1)
    navFrame.rowconfigure(2, weight=1)
    navFrame.columnconfigure(0, weight=1)
    navFrame.columnconfigure(1, weight=1)
    navFrame.columnconfigure(2, weight=1)

    # al clicar en cualquiera de los botones se activa la función go a la que se le pasa la dirección
    # en la que hay que navegar y el boton clicado, para que la función le cambie el color
    NWBtn = tk.Button(navFrame, text="NW", bg="dark orange",
                        command= lambda: go("NorthWest", NWBtn))
    NWBtn.grid(row=0, column=0, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    NoBtn = tk.Button(navFrame, text="No", bg="dark orange",
                        command= lambda: go("North", NoBtn))
    NoBtn.grid(row=0, column=1, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    NEBtn = tk.Button(navFrame, text="NE", bg="dark orange",
                        command= lambda: go("NorthEast", NEBtn))
    NEBtn.grid(row=0, column=2, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    WeBtn = tk.Button(navFrame, text="We", bg="dark orange",
                        command=lambda: go("West", WeBtn))
    WeBtn.grid(row=1, column=0, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    StopBtn = tk.Button(navFrame, text="St", bg="dark orange",
                        command=lambda: go("Stop", StopBtn))
    StopBtn.grid(row=1, column=1, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    EaBtn = tk.Button(navFrame, text="Ea", bg="dark orange",
                        command=lambda: go("East", EaBtn))
    EaBtn.grid(row=1, column=2, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)


    SWBtn = tk.Button(navFrame, text="SW", bg="dark orange",
                        #command=lambda: go("SouthWest", SWBtn))
                        command = lambda: go("Down", SWBtn))
    SWBtn.grid(row=2, column=0, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    SoBtn = tk.Button(navFrame, text="So", bg="dark orange",
                        command=lambda: go("South", SoBtn))
    SoBtn.grid(row=2, column=1, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)

    SEBtn = tk.Button(navFrame, text="SE", bg="dark orange",
                        #command=lambda: go("SouthEast", SEBtn))
                        command = lambda: go("Up", SEBtn))
    SEBtn.grid(row=2, column=2, padx=2, pady=2, sticky=tk.N + tk.S + tk.E + tk.W)


    # slider para elegir la velocidad de navegación
    speedSldr = tk.Scale(left_frame, label="Velocidad (m/s):", resolution=1, from_=0, to=20, tickinterval=5,
                          orient=tk.HORIZONTAL)
    speedSldr.grid(row=7, column=0, columnspan=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)
    speedSldr.bind("<ButtonRelease-1>", changeNavSpeed)

    # botones para pedir/parar datos de telemetría
    StartTelemBtn = tk.Button(left_frame, text="Empezar a enviar telemetría", bg="dark orange", command=startTelem)
    StartTelemBtn.grid(row=8, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    StopTelemBtn = tk.Button(left_frame, text="Parar de enviar telemetría", bg="dark orange", command=stopTelem)
    StopTelemBtn.grid(row=8, column=1, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Este es el frame para mostrar los datos de telemetría
    # Contiene etiquetas para informar de qué datos son y los valores. Solo nos interesan 3 datos de telemetría
    telemetryFrame = tk.LabelFrame(left_frame, text="Telemetría")
    telemetryFrame.grid(row=9, column=0, columnspan=2, padx=10, pady=10, sticky=tk.N + tk.S + tk.E + tk.W)

    telemetryFrame.rowconfigure(0, weight=1)
    telemetryFrame.rowconfigure(1, weight=1)

    telemetryFrame.columnconfigure(0, weight=1)
    telemetryFrame.columnconfigure(1, weight=1)
    telemetryFrame.columnconfigure(2, weight=1)
    telemetryFrame.columnconfigure(3, weight=1)

    # etiquetas informativas
    altLbl = tk.Label(telemetryFrame, text='Altitud')
    altLbl.grid(row=0, column=0,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    headingLbl = tk.Label(telemetryFrame, text='Heading')
    headingLbl.grid(row=0, column=1,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    stateLbl = tk.Label(telemetryFrame, text='Estado')
    stateLbl.grid(row=0, column=2,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    speedLbl = tk.Label(telemetryFrame, text='Velocidad (m/s)')
    speedLbl.grid(row=0, column=3,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # etiquetas para colocar aqui los datos cuando se reciben
    altShowLbl = tk.Label(telemetryFrame, text='')
    altShowLbl.grid(row=1, column=0, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    headingShowLbl = tk.Label(telemetryFrame, text='',)
    headingShowLbl.grid(row=1, column=1,  padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    stateShowLbl = tk.Label(telemetryFrame, text='', )
    stateShowLbl.grid(row=1, column=2, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    speedShowLbl = tk.Label(telemetryFrame, text='')
    speedShowLbl.grid(row=1, column=3, padx=5, pady=5, sticky=tk.N + tk.S + tk.E + tk.W)

    # Initialize map in right_frame
    global map_widget, drone_marker
    if MAP_AVAILABLE:
        try:
            map_widget = TkinterMapView(right_frame, width=400, height=600, corner_radius=0)
            map_widget.pack(fill=tk.BOTH, expand=True)
            map_widget.set_zoom(15)
            drone_marker = None
        except Exception as e:
            tk.Label(right_frame, text=f'Error iniciando mapa: {e}').pack(fill=tk.BOTH, expand=True)
    else:
        tk.Label(right_frame, text='Instala tkintermapview:\npython -m pip install tkintermapview').pack(fill=tk.BOTH, expand=True)

    return ventana

if __name__ == "__main__":
    ventana = crear_ventana()
    ventana.mainloop()
