import csv
import os
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

def cargar_base_datos():
    base = {}
    if os.path.exists('navieras.csv'):
        # utf-8-sig evita problemas con caracteres especiales y BOM de Excel
        with open('navieras.csv', mode='r', encoding='utf-8-sig') as f:
            # Fijamos el delimitador explícitamente en punto y coma
            reader = csv.DictReader(f, delimiter=';')
            for row in reader:
                # Limpiar espacios invisibles en las claves y valores
                row_clean = {str(k).strip(): str(v).strip() for k, v in row.items() if k is not None}
                
                prefijo = row_clean.get('Container Prefix', '').upper()
                if prefijo:
                    base[prefijo] = {
                        "naviera": row_clean.get('Shipping Line', ''),
                        "link": row_clean.get('Tracking URL', '')
                    }
    return base

# Carga la base de datos en memoria al iniciar el servidor
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

def normalizar_tipo(texto):
    texto_upper = texto.upper()
    if "40' DRY VAN" in texto_upper or "40' STANDARD" in texto_upper or "40'DV" in texto_upper:
        return "40'DC"
    if "20' DRY VAN" in texto_upper or "20' STANDARD" in texto_upper or "20'DV" in texto_upper:
        return "20'DC"
    if "HIGH CUBE" in texto_upper or "40' HC" in texto_upper or "40'HQ" in texto_upper:
        return "40'HQ"
    if "OPEN TOP" in texto_upper or "40' OT" in texto_upper:
        return "40'OT"
    if "REEFER" in texto_upper:
        return "REEFER"
    return "TIPO NO IDENTIFICADO"

def scrapear_triton(contenedor):
    carrier_final = "Triton International"
    tipo_final = "SIN DATOS"
    
    browser_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-zygote',
        '--single-process'
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=browser_args)
        page = browser.new_page()
        
        try:
            url = f"https://www.tritoncontainer.com/CustomerTools/UnitInquiry?UnitNumbers={contenedor}"
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            
            page.wait_for_timeout(8000)
            
            texto_web = page.evaluate("document.body.innerText").upper()
            tipo_final = normalizar_tipo(texto_web)
            
            if "HAPAG" in texto_web:
                carrier_final = "Hapag-Lloyd"
            elif "MAERSK" in texto_web:
                carrier_final = "Maersk"
            elif "MSC" in texto_web:
                carrier_final = "MSC"
            elif "CMA" in texto_web:
                carrier_final = "CMA CGM"
            elif "ONE" in texto_web:
                carrier_final = "ONE"
                
        except Exception as e:
            tipo_final = f"ERROR: {str(e)[:40]}"
        finally:
            browser.close()
            
    return carrier_final, tipo_final

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json or {}
    contenedor = data.get("container", "").upper().strip()
    override_carrier = data.get("override_carrier", "").strip()
    
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    # Extraemos naviera y link del archivo CSV
    naviera_bd, link_tracking = identificar_carrier_y_link(contenedor)
    
    carrier_detectado = override_carrier if (override_carrier and override_carrier.upper() != "BUSCANDO...") else naviera_bd
    tipo_contenedor = "PENDIENTE"
    
    if "TRITON" in carrier_detectado.upper():
        carrier_detectado, tipo_contenedor = scrapear_triton(contenedor)
    else:
        tipo_contenedor = "SCRAPING NAVIERA PENDIENTE"
    
    resultado = {
        "container": contenedor,
        "carrier": carrier_detectado,
        "type": tipo_contenedor,
        "buque": "PENDIENTE",
        "eta": "",
        "tracking_link": link_tracking
    }
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
