import csv
import os
import re
from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

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

def scrapear_datos(contenedor, carrier_detectado):
    carrier_final = carrier_detectado
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
        context = browser.new_context()
        page = context.new_page()
        
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] else route.continue_())
        
        try:
            carrier_upper = carrier_detectado.upper()
            texto_web = ""
            
            if "TRITON" in carrier_upper:
                url = f"https://www.tritoncontainer.com/CustomerTools/UnitInquiry?UnitNumbers={contenedor}"
                page.goto(url, wait_until="networkidle", timeout=25000)
                
                try:
                    page.locator("button", has_text=re.compile(r"search", re.IGNORECASE)).first.click(timeout=3000)
                except:
                    pass
                
                # Esperamos explícitamente a que el contenedor o la palabra "Showing" aparezca en el texto renderizado
                try:
                    page.wait_for_function(f"document.body.innerText.includes('{contenedor}') || document.body.innerText.includes('Showing')", timeout=15000)
                except:
                    page.wait_for_timeout(8000)
                
                # Volvemos a innerText para evitar cortes por etiquetas HTML
                texto_web = page.evaluate("document.body.innerText || ''").upper()
                for frame in page.frames:
                    try: texto_web += " " + frame.evaluate("document.body.innerText || ''").upper()
                    except: pass
                
                texto_web = re.sub(r'\s+', ' ', texto_web)
                
                if "HAPAG" in texto_web: carrier_final = "Hapag-Lloyd"
                elif "MAERSK" in texto_web: carrier_final = "Maersk"
                elif "MSC" in texto_web or "MED SHIPPING" in texto_web or "MEDITERRANEAN" in texto_web: carrier_final = "MSC"
                elif "CMA" in texto_web: carrier_final = "CMA CGM"
                elif re.search(r'\bONE\b', texto_web) or "OCEAN NETWORK EXPRESS" in texto_web: carrier_final = "ONE"

            elif "TEXTAINER" in carrier_upper:
                url = "https://tex.textainer.com/Equipment/StatusAndSpecificationsInquiry"
                page.goto(url, wait_until="networkidle", timeout=25000)
                
                page.evaluate(f'''
                    let el = Array.from(document.querySelectorAll("textarea, input[type='text']")).find(e => e.offsetParent !== null);
                    if(el) el.value = "{contenedor}";
                    let btn = Array.from(document.querySelectorAll("input[type='submit'], button")).find(e => e.offsetParent !== null);
                    if(btn) btn.click();
                ''')
                
                try:
                    page.wait_for_function(f"document.body.innerText.includes('{contenedor}') || document.body.innerText.includes('Status')", timeout=15000)
                except:
                    page.wait_for_timeout(10000)
                
                texto_web = page.evaluate("document.body.innerText || ''").upper()
                for frame in page.frames:
                    try: texto_web += " " + frame.evaluate("document.body.innerText || ''").upper()
                    except: pass
                
                texto_web = re.sub(r'\s+', ' ', texto_web)
                
                if "HAPAG" in texto_web: carrier_final = "Hapag-Lloyd"
                elif "MAERSK" in texto_web: carrier_final = "Maersk"
                elif "MSC" in texto_web or "MED SHIPPING" in texto_web or "MEDITERRANEAN" in texto_web: carrier_final = "MSC"
                elif "CMA" in texto_web: carrier_final = "CMA CGM"
                elif re.search(r'\bONE\b', texto_web) or "OCEAN NETWORK EXPRESS" in texto_web: carrier_final = "ONE"
                    
            elif "MAERSK" in carrier_upper:
                url = f"https://www.maersk.com/tracking/{contenedor}"
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(5000)
                texto_web = page.evaluate("document.body.innerText || ''").upper()
                
            elif "MSC" in carrier_upper:
                url = f"https://www.msc.com/en/track-a-shipment?trackingNumber={contenedor}"
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(5000)
                texto_web = page.evaluate("document.body.innerText || ''").upper()
                
            elif "CMA" in carrier_upper:
                url = f"https://www.cma-cgm.com/ebusiness/tracking/search?reference={contenedor}"
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(5000)
                texto_web = page.evaluate("document.body.innerText || ''").upper()
                
            elif "HAPAG" in carrier_upper:
                url = f"https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html?container={contenedor}"
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(5000)
                texto_web = page.evaluate("document.body.innerText || ''").upper()
                
            else:
                tipo_final = "SCRAPING NO CONFIGURADO PARA ESTA NAVIERA"
                texto_web = ""

            if texto_web:
                tipo_final = normalizar_tipo(texto_web)
                
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str:
                tipo_final = "BLOQUEO ANTI-ROBOT O TIEMPO AGOTADO"
            else:
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
    
    naviera_bd, link_tracking = identificar_carrier_y_link(contenedor)
    
    carrier_detectado_original = override_carrier if (override_carrier and override_carrier.upper() != "BUSCANDO...") else naviera_bd
    
    if carrier_detectado_original != "DESCONOCIDO":
        carrier_detectado_final, tipo_contenedor = scrapear_datos(contenedor, carrier_detectado_original)
        
        if carrier_detectado_original.upper() != carrier_detectado_final.upper() and override_carrier == "":
            nuevo_link = obtener_link_por_naviera(carrier_detectado_final)
            if nuevo_link:
                link_tracking = nuevo_link
    else:
        carrier_detectado_final = carrier_detectado_original
        tipo_contenedor = "NO SE PUDO DETERMINAR NAVIERA"
    
    resultado = {
        "container": contenedor,
        "carrier": carrier_detectado_final,
        "type": tipo_contenedor,
        "buque": "PENDIENTE",
        "eta": "",
        "tracking_link": link_tracking
    }
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
