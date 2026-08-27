import csv
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

def cargar_base_datos():
    base = {}
    if os.path.exists('navieras.csv'):
        with open('navieras.csv', mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                row_clean = {str(k).strip(): str(v).strip() for k, v in row.items() if k is not None}
                prefijo = row_clean.get('Container Prefix', '').upper()
                if prefijo:
                    base[prefijo] = {
                        "naviera": row_clean.get('Shipping Line', ''),
                        "link": row_clean.get('Tracking URL', '')
                    }
    return base

BASE_DATOS = cargar_base_datos()

def identificar_carrier_y_link(contenedor):
    contenedor = contenedor.upper().strip()
    if len(contenedor) < 4:
        return "DESCONOCIDO", ""
    prefijo_4 = contenedor[:4]
    prefijo_3 = contenedor[:3]
    
    datos = BASE_DATOS.get(prefijo_4) or BASE_DATOS.get(prefijo_3)
    if datos:
        return datos["naviera"], datos["link"]
    return "OTRA / LEASING", ""

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json or {}
    contenedor = data.get("container", "").upper().strip()
    override_carrier = data.get("override_carrier", "").strip()
    
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    naviera_bd, link_tracking = identificar_carrier_y_link(contenedor)
    carrier_detectado = override_carrier if (override_carrier and override_carrier.upper() != "BUSCANDO...") else naviera_bd
    
    resultado = {
        "container": contenedor,
        "carrier": carrier_detectado,
        "type": "PENDIENTE",
        "buque": "PENDIENTE",
        "eta": "",
        "tracking_link": link_tracking
    }
    return jsonify(resultado)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
