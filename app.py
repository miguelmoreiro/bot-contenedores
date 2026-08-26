from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

PREFIJOS_NAVIERAS = {
    "MED": "MSC", "MSCU": "MSC", "MSBU": "MSC", "MSGU": "MSC", "MSNU": "MSC", "MSMU": "MSC",
    "MAEU": "Maersk", "MSKU": "Maersk", "MRKU": "Maersk", "SEAU": "Maersk", "SUDU": "Hamburg Sud",
    "CMAU": "CMA CGM", "APLU": "CMA CGM", "CNCU": "CMA CGM", "CGMU": "CMA CGM",
    "HLCU": "Hapag-Lloyd", "HLXU": "Hapag-Lloyd", "UACU": "Hapag-Lloyd", "HLBU": "Hapag-Lloyd",
    "ONEY": "ONE", "NYKU": "ONE", "MOLU": "ONE", "KKTU": "ONE",
    "EMCU": "Evergreen", "EISU": "Evergreen", "EGHU": "Evergreen", "EGLU": "Evergreen",
    "HMMU": "HMM", "HDMU": "HMM",
    "YMLU": "Yang Ming",
    "ZIMU": "ZIM", "ZCSU": "ZIM",
    "WHLU": "Wan Hai",
    "HASU": "Heung-A Line", "HLHU": "Heung-A Line", "HALU": "Heung-A Line",
    "TRHU": "Triton International", "TGHU": "Textainer", "TEMU": "Textainer",
    "CLHU": "Textainer", "SEGU": "Seaco", "CAIU": "CAI International",
    "TCLU": "Triton International"
}

def identificar_carrier(contenedor):
    contenedor = contenedor.upper().strip()
    if len(contenedor) < 4:
        return "DESCONOCIDO"
    prefijo_4 = contenedor[:4]
    prefijo_3 = contenedor[:3]
    return PREFIJOS_NAVIERAS.get(prefijo_4, PREFIJOS_NAVIERAS.get(prefijo_3, "OTRA / LEASING"))

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
    
    # Banderas para reducir el uso de memoria RAM en servidores en la nube
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
            
            # Espera a que la tabla de resultados esté presente
            page.wait_for_selector("table", timeout=10000)
            page.wait_for_timeout(2000)
            
            texto_web = page.evaluate("document.body.innerText").upper()
            tipo_final = normalizar_tipo(texto_web)
            
            # Detección automática de la naviera arrendataria (Customer)
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
    
    carrier_detectado = override_carrier if (override_carrier and override_carrier.upper() != "BUSCANDO...") else identificar_carrier(contenedor)
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
        "eta": ""
    }
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
