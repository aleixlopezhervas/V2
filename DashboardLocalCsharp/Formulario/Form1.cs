using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using MQTTnet;
using MQTTnet.Client;
using System.Text.Json; // Para procesar la telemetría

namespace Formulario
{
    public partial class Form1 : Form
    {
        // 1. Instancia global de nuestro cliente MQTT
        private IMqttClient mqttClient;
        private string origen = "elies"; // El nombre de tu app

        private double currentLatDeg = double.NaN;
        private double currentLonDeg = double.NaN;

        public Form1()
        {
            InitializeComponent();
            CheckForIllegalCrossThreadCalls = false;

            Font letraGrande = new Font("Arial", 14);
            Font letraPequeña = new Font("Arial", 12);

            // Botones de navegación
            button9.Text = "NW"; button9.Tag = "NorthWest"; button9.Click += navButton_Click; button9.Font = letraGrande;
            button10.Text = "N"; button10.Tag = "North"; button10.Click += navButton_Click; button10.Font = letraGrande;
            button11.Text = "NE"; button11.Tag = "NorthEast"; button11.Click += navButton_Click; button11.Font = letraGrande;
            button12.Text = "W"; button12.Tag = "West"; button12.Click += navButton_Click; button12.Font = letraGrande;
            button13.Text = "Stop"; button13.Tag = "Stop"; button13.Click += navButton_Click; button13.Font = letraPequeña;
            button14.Text = "E"; button14.Tag = "East"; button14.Click += navButton_Click; button14.Font = letraGrande;
            button15.Text = "SW"; button15.Tag = "SouthWest"; button15.Click += navButton_Click; button15.Font = letraGrande;
            button16.Text = "S"; button16.Tag = "South"; button16.Click += navButton_Click; button16.Font = letraGrande;
            button17.Text = "SE"; button17.Tag = "SouthEast"; button17.Click += navButton_Click; button17.Font = letraGrande;
        }

        private async void Form1_Load(object sender, EventArgs e)
        {
            // 2. Configurar y conectar MQTTnet al iniciar el formulario
            var mqttFactory = new MqttFactory();
            mqttClient = mqttFactory.CreateMqttClient();

            // Configuramos conexión por WebSockets (puerto 8000)
            var mqttClientOptions = new MqttClientOptionsBuilder()
                .WithWebSocketServer("broker.hivemq.com:8000/mqtt")
                .Build();

            // Configurar qué hacer cuando se recibe un mensaje
            mqttClient.ApplicationMessageReceivedAsync += MqttClient_ApplicationMessageReceivedAsync;

            try
            {
                await mqttClient.ConnectAsync(mqttClientOptions);

                // Suscribirse a los tópicos de respuesta desde Python
                var subscribeOptions = mqttFactory.CreateSubscribeOptionsBuilder()
                    .WithTopicFilter(f => f.WithTopic($"autopilotServiceDemo/{origen}/#"))
                    .Build();

                await mqttClient.SubscribeAsync(subscribeOptions);
                Console.WriteLine("Conectado a MQTT y suscrito con éxito.");
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error conectando al broker MQTT: " + ex.Message);
            }
        }

        // =========================================================
        // ENVÍO DE MENSAJES AL DRON (PUBLICADORES)
        // =========================================================

        private async void PublicarMensaje(string comando, string payload = "")
        {
            if (mqttClient == null || !mqttClient.IsConnected) return;

            string topic = $"{origen}/autopilotServiceDemo/{comando}";
            var message = new MqttApplicationMessageBuilder()
                .WithTopic(topic)
                .WithPayload(payload)
                .Build();

            await mqttClient.PublishAsync(message);
        }

        private void but_connect_Click(object sender, EventArgs e)
        {
            PublicarMensaje("connect");
            but_connect.BackColor = Color.Yellow; // Cambia a verde cuando Python confirme
        }

        private void but_takeoff_Click(object sender, EventArgs e)
        {
            int alturaSeleccionada = AlturatrackBar.Value;
            if (alturaSeleccionada != 0)
            {
                PublicarMensaje("arm_takeOff", alturaSeleccionada.ToString());
                despegarBtn.BackColor = Color.Yellow;
            }
            else
            {
                MessageBox.Show("Selecciona una altura de despegue mayor que 0");
            }
        }

        private void navButton_Click(object sender, EventArgs e)
        {
            Button b = (Button)sender;
            string tag = b.Tag.ToString();
            PublicarMensaje("go", tag);
        }

        private void aterrizarBtn_Click(object sender, EventArgs e)
        {
            PublicarMensaje("Land");
            button7.BackColor = Color.Yellow;
        }

        private void RTLBtn_Click(object sender, EventArgs e)
        {
            PublicarMensaje("RTL");
            button6.BackColor = Color.Yellow;
        }

        private void enviarTelemetriaBtn_Click(object sender, EventArgs e)
        {
            PublicarMensaje("startTelemetry");
        }

        private void detenerTelemetriaBtn_Click(object sender, EventArgs e)
        {
            PublicarMensaje("stopTelemetry");
        }

        private void headingTrackBar_MouseUp(object sender, MouseEventArgs e)
        {
            PublicarMensaje("changeHeading", headingTrackBar.Value.ToString());
        }

        private void velocidadTrackBar_MouseUp(object sender, MouseEventArgs e)
        {
            PublicarMensaje("changeNavSpeed", velocidadTrackBar.Value.ToString());
        }

        private void Alt_changeTrackBar_MouseUp(object sender, MouseEventArgs e)
        {
            // Nota: He modificado esto porque en Python no tienes un "IrAlPunto". 
            // He creado el comando "changeAltitude" que deberás añadir a tu script de Python.
            PublicarMensaje("changeAltitude", Alt_changeTrackBar.Value.ToString());
        }

        // =========================================================
        // EVENTOS DE INTERFAZ (UI LABELS Y SCROLLS)
        // =========================================================

        private void headingTrackBar_Scroll(object sender, EventArgs e) => headingLbl.Text = headingTrackBar.Value.ToString();
        private void velocidadTrackBar_Scroll(object sender, EventArgs e) => velocidadLbl.Text = velocidadTrackBar.Value.ToString();
        private void AlturatrackBar_Scroll(object sender, EventArgs e) => AlturaLbl.Text = AlturatrackBar.Value.ToString();
        private void Alt_changeTrackBar_Scroll(object sender, EventArgs e) => AltChangeLbl.Text = Alt_changeTrackBar.Value.ToString();
        private void AlturaLbl_Click(object sender, EventArgs e) { }
        private void AltChangeLbl_Click(object sender, EventArgs e) { }

        // =========================================================
        // RECEPCIÓN DE MENSAJES DESDE EL DRON (SUSCRIPTORES)
        // =========================================================

        private Task MqttClient_ApplicationMessageReceivedAsync(MqttApplicationMessageReceivedEventArgs e)
        {
            string topic = e.ApplicationMessage.Topic;
            string payload = Encoding.UTF8.GetString(e.ApplicationMessage.Payload ?? Array.Empty<byte>());

            // Utilizamos Invoke para evitar el error de "Cross-Thread" al actualizar la UI
            this.Invoke((MethodInvoker)delegate
            {
                // Extraemos el final del tópico (ej: "connected", "telemetryInfo", etc.)
                string ev = topic.Split('/').Last();

                switch (ev)
                {
                    case "connected":
                        but_connect.BackColor = Color.Green;
                        but_connect.ForeColor = Color.White;
                        break;

                    case "flying": // Evento cuando termina de despegar
                        despegarBtn.BackColor = Color.Green;
                        despegarBtn.ForeColor = Color.White;
                        despegarBtn.Text = "Volando";
                        break;

                    case "landed": // Evento cuando aterriza
                        button7.BackColor = Color.Green;
                        break;

                    case "atHome": // Evento de RTL
                        button6.BackColor = Color.Green;
                        break;

                    case "telemetryInfo":
                        ProcesarTelemetriaJson(payload);
                        break;
                }
            });

            return Task.CompletedTask;
        }

        private void ProcesarTelemetriaJson(string jsonPayload)
        {
            // Este método asume que Python envía la telemetría como JSON
            // Deberás ajustarlo si la estructura JSON que envía Python es diferente.
            try
            {
                using (JsonDocument doc = JsonDocument.Parse(jsonPayload))
                {
                    var root = doc.RootElement;

                    // Asegúrate de que los nombres coincidan con los que envía Python (ej. "lat", "lon", "heading")
                    if (root.TryGetProperty("lat", out JsonElement latEl)) currentLatDeg = latEl.GetDouble();
                    if (root.TryGetProperty("lon", out JsonElement lonEl)) currentLonDeg = lonEl.GetDouble();

                    if (root.TryGetProperty("alt", out JsonElement altEl)) altitudLbl.Text = altEl.GetDouble().ToString();
                    if (root.TryGetProperty("heading", out JsonElement headEl)) headLbl.Text = headEl.GetDouble().ToString();
                    if (root.TryGetProperty("battery", out JsonElement batEl)) BatteryLbl.Text = batEl.GetDouble().ToString("F0") + " %";

                    latitudLbl.Text = currentLatDeg.ToString();
                    longitudLbl.Text = currentLonDeg.ToString();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine("Error parseando telemetría: " + ex.Message);
            }
        }
    }
}