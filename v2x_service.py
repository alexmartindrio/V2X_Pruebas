import time
import json 
import threading
from flask import Flask, jsonify, render_template_string
import boto3
 
app = Flask(__name__)
 
# ⚠️ PEGA AQUÍ LA URL REAL QUE HAS COPIADO DE AWS SQS
SQS_REGION = 'us-east-1'
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/523572554218/V2X_1'

vehicles_state = {}

def sqs_listener():
    # Comprobación básica de URL configurada
    if "TU_ACCOUNT_ID" in QUEUE_URL:
        print("❌ ERROR: Debes cambiar 'TU_ACCOUNT_ID' por tu URL real de SQS en el código.")
        return

    sqs = boto3.client('sqs', region_name=SQS_REGION)
    print("✅ Escuchando eventos de la cola SQS en AWS...")
    
    while True:
        try:
            response = sqs.receive_message(
                QueueUrl=QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=5
            )
            messages = response.get('Messages', [])
            for msg in messages:
                body = json.loads(msg['Body'])
                veh_id = body.get('source_id')
                event_type = body.get('event_type')
                payload = body.get('payload', {})
                
                vehicles_state[veh_id] = {
                    "id": veh_id,
                    "x": payload.get("x", 50),
                    "y": payload.get("y", 50),
                    "speed": payload.get("speed", 0),
                    "event_type": event_type,
                    "alert": (event_type == "sudden braking" or payload.get("speed", 0) > 100),
                    "last_update": time.strftime("%H:%M:%S")
                }
                
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=msg['ReceiptHandle']
                )
        except Exception as e:
            print(f"Error procesando SQS: {e}")
        time.sleep(0.5)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Dashboard V2X</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #1a1a24; color: white; text-align: center; margin: 0; padding: 20px; }
        #canvas-container { margin: 15px auto; display: inline-block; border: 3px solid #444; border-radius: 8px; background-color: #222230; }
        canvas { display: block; }
        .vehicle-card { display: inline-block; background: #2a2a3c; padding: 10px 15px; margin: 5px; border-radius: 6px; text-align: left; font-size: 13px; width: 150px; }
        .alert-card { border: 2px solid #ff4444; background: #4a1515; }
        .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 5px; }
        .normal { background-color: #00ff88; }
        .danger { background-color: #ff4444; }
    </style>
</head>
<body>
    <h1>🚗 Dashboard V2X-SERVICE (MVP)2.0</h1>
    <div id="canvas-container"><canvas id="map" width="600" height="400"></canvas></div>
    <h2>Vehículos en línea</h2>
    <div id="vehicles-list">Esperando datos de la SQS...</div>

    <script>
        const canvas = document.getElementById('map');
        const ctx = canvas.getContext('2d');

        function drawGrid() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.strokeStyle = "#333344";
            for (let x = 0; x < canvas.width; x += 50) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, canvas.height); ctx.stroke(); }
            for (let y = 0; y < canvas.height; y += 50) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(canvas.width, y); ctx.stroke(); }
        }

        async function updateDashboard() {
            try {
                const res = await fetch('/api/vehicles');
                const data = await res.json();
                drawGrid();
                const listDiv = document.getElementById('vehicles-list');
                listDiv.innerHTML = '';

                Object.values(data).forEach(veh => {
                    ctx.beginPath();
                    ctx.arc(veh.x, veh.y, 14, 0, 2 * Math.PI);
                    ctx.fillStyle = veh.alert ? '#ff4444' : '#00ccff';
                    ctx.fill();
                    ctx.strokeStyle = '#ffffff';
                    ctx.stroke();

                    ctx.fillStyle = '#ffffff';
                    ctx.font = '11px Arial';
                    ctx.fillText(veh.id, veh.x - 18, veh.y - 18);

                    if (veh.alert) {
                        ctx.fillStyle = '#ffff00';
                        ctx.font = '14px Arial';
                        ctx.fillText('⚠️', veh.x - 6, veh.y + 5);
                    }

                    const card = document.createElement('div');
                    card.className = `vehicle-card ${veh.alert ? 'alert-card' : ''}`;
                    card.innerHTML = `
                        <strong><span class="status-dot ${veh.alert ? 'danger' : 'normal'}"></span>${veh.id}</strong><br>
                        Vel: ${veh.speed} km/h<br>
                        Pos: (${veh.x}, ${veh.y})<br>
                        Evento: ${veh.event_type}<br>
                        <small>Hora: ${veh.last_update}</small>
                    `;
                    listDiv.appendChild(card);
                });
            } catch (err) { console.error("Error:", err); }
        }
        setInterval(updateDashboard, 1000);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/vehicles')
def get_vehicles():
    return jsonify(vehicles_state)

if __name__ == '__main__':
    t = threading.Thread(target=sqs_listener, daemon=True)
    t.start()
    app.run(host='0.0.0.0', port=5000)
