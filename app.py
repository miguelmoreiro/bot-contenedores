import csv
import os
from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

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

def obtener_link_por_naviera(nombre_naviera):
    for datos in BASE_DATOS.values():
        if datos["naviera"].upper() == nombre_naviera.upper():
            return datos["link"]
    return ""

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

def normalizar_tipo(texto):
    texto_upper = texto.upper()
    if "40' DRY VAN" in texto_upper or "40' STANDARD" in texto_upper or "40'DV" in texto_upper or "40 DRY" in texto_upper:
        return "40'DC"
    if "20' DRY VAN" in texto_upper or "20' STANDARD" in texto_upper or "20'DV" in texto_upper or "20 DRY" in texto_upper:
        return "20'DC"
    if "HIGH CUBE" in texto_upper or "40' HC" in texto_upper or "40'HQ" in texto_upper or "40 HIGH" in texto_upper:
        return "40'HQ"
    if "OPEN TOP" in texto_upper or "40' OT" in texto_upper or "40 OPEN" in texto_upper:
        return "40'OT"
    if "REEFER" in texto_upper:
        return "REEFER"
    return "TIPO NO IDENTIFICADO"

def consultar_web_ligera(contenedor, carrier_detectado):
    carrier_final = carrier_detectado
    tipo_final = "SIN DATOS"
    
    try:
        if "TRITON" in carrier_detectado.upper():
            # Petición HTTP directa al endpoint de Triton
            url = f"https://tools.tritoncontainer.com/tritoncontainer/unitStatus/list"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                texto_web = soup.get_text().upper()
                
                if "MSC" in texto_web or "MED SHIPPING" in texto_web:
                    carrier_final = "MSC"
                elif "ONE" in texto_web:
                    carrier_final = "ONE"
                
                tipo_final = normalizar_tipo(texto_web)
    except Exception as e:
        tipo_final = "ERROR CONSULTA"
        
    return carrier_final, tipo_final

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json or {}
    contenedor = data.get("container", "").upper().strip()
    override_carrier = data.get("override_carrier", "").strip()
    
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    naviera_bd, link_tracking = identificar_carrier_y_link(contenedor)
    carrier_detectado_original = override_carrier if (override_carrier and override_carrier.upper() != "BUSCANDO...") else nav_data = naviera_bd
    
    carrier_final, tipo_contenedor = consultar_web_ligera(contenedor, carrier_detectado_original)
    
    if carrier_detectado_original.upper() != carrier_final.upper() and override_carrier == "":
        nuevo_link = obtener_link_por_naviera(carrier_final)
        if nuevo_link:
            link_tracking = nuevo_link

    resultado = {
        "container": contenedor,
        "carrier": carrier_final,
        "type": tipo_contenedor,
        "buque": "PENDIENTE",
        "eta": "",
        "tracking_link": link_tracking
    }
    return jsonify(resultado)
