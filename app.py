import csv
import os
import re
import requests
from bs4 import BeautifulSoup
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
        naviera = datos["naviera"]
        link_base = datos["link"]
        
        if "MAERSK" in naviera.upper():
            link_tracking = f"https://www.maersk.com/tracking/{contenedor}?newDesign=true"
        else:
            link_tracking = link_base
            
        return naviera, link_tracking
        
    return "OTRA / LEASING", "https://tools.tritoncontainer.com/tritoncontainer/unitStatus/list"

def normalizar_tipo(texto):
    t = texto.upper()
    if "40" in t and ("HC" in t or "HQ" in t or "HIGH" in t or "CUBE" in t):
        return "40'HQ"
    if "40" in t and ("OT" in t or "OPEN" in t):
        return "40'OT"
    if "40" in t:
        return "40'DC"
    if "20" in t:
        return "20'DC"
    if "REEFER" in t or "RF" in t:
        return "REEFER"
    return "40'DC"

def scrapear_maersk(contenedor):
    tipo = "PENDIENTE"
    buque = "PENDIENTE"
    eta = ""
    
    url = f"https://www.maersk.com/tracking/{contenedor}?newDesign=true"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            texto_completo = response.text
            
            # Buscar Tipo de Contenedor
            match_tipo = re.search(r'(40\'\s*Dry\s*High|20\'\s*Dry|40\'\s*DC|20\'\s*DC|40\'\s*HC|40\s*Dry\s*High)', texto_completo, re.IGNORECASE)
            if match_tipo:
                tipo = normalizar_tipo(match_tipo.group(0))
            
            # Buscar Nombre del Buque
            match_buque = re.search(r'([A-Z\s]+\/\s*\d+[A-Z]*)', texto_completo)
            if match_buque:
                buque = match_buque.group(0).strip()
                
            # Buscar ETA / Fecha de llegada
            match_eta = re.search(r'(\d{2}\s+[A-Za-z]{3}\s+\d{4})', texto_completo)
            if match_eta:
                eta = match_eta.group(0)
    except Exception:
        tipo = "ERROR SCRAPING"
        
    return tipo, buque, eta

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json or {}
    contenedor = data.get("container", "").upper().strip()
    override_carrier = data.get("override_carrier", "").strip()
    
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    naviera_bd, link_tracking = identificar_carrier_y_link(contenedor)
    carrier_detectado = override_carrier if (override_carrier and override_carrier.upper() != "BUSCANDO...") else naviera_bd
    
    tipo_contenedor = "PENDIENTE"
    buque = "PENDIENTE"
    eta = ""
    
    if "MAERSK" in carrier_detectado.upper():
        tipo_contenedor, buque, eta = scrapear_maersk(contenedor)
    
    resultado = {
        "container": contenedor,
        "carrier": carrier_detectado,
        "type": tipo_contenedor,
        "buque": buque,
        "eta": eta,
        "tracking_link": link_tracking
    }
    return jsonify(resultado)
