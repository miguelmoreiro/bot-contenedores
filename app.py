from flask import Flask, request, jsonify
from playwright.sync_api import sync_playwright

app = Flask(__name__)

PREFIJOS_NAVIERAS = {
    "MED": "MSC", "MSCU": "MSC", "MSBU": "MSC", "MSGU": "MSC", "MSMU": "MSC", "MSNU": "MSC",
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

def realizar_scraping_navegador(url):
    """
    Abre un navegador invisible, carga la página esperando a que termine 
    el JavaScript y devuelve el texto de la web.
    """
    resultado = "SIN DATOS"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            # Va a la URL y espera a que la red se quede quieta (JS cargado)
            page.goto(url, wait_until="networkidle", timeout=15000)
            
            # Extraemos todo el texto visible de la web
            texto_web = page.evaluate("document.body.innerText").upper()
            
            # Lógica simple de detección para confirmar que superamos la barrera
            if "20" in texto_web or "40" in texto_web or "DRY" in texto_web:
                resultado = "NAVEGADOR OK: DATOS VISIBLES"
            else:
                resultado = "NAVEGADOR OK: PARSEO PENDIENTE"
                
            browser.close()
    except Exception as e:
        resultado = f"ERROR NAVEGADOR: {str(e)}"
        
    return resultado

def scrapear_datos_naviera(contenedor, carrier):
    carrier_upper = carrier.upper()
    url = ""
    
    if "MAERSK" in carrier_upper:
        url = f"https://www.maersk.com/tracking/{contenedor}"
    elif "MSC" in carrier_upper:
        url = f"https://www.msc.com/en/track-a-shipment?trackingNumber={contenedor}"
    elif "CMA" in carrier_upper:
        url = f"https://www.cma-cgm.com/ebusiness/tracking/search?reference={contenedor}"
    elif "HAPAG" in carrier_upper:
        url = f"https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html?container={contenedor}"
    elif "TRITON" in carrier_upper:
        url = f"https://www.tritoncontainer.com/CustomerTools/UnitInquiry?UnitNumbers={contenedor}"
    else:
        return "SCRAPING NO CONFIGURADO"
        
    return realizar_scraping_navegador(url)

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json
    contenedor = data.get("container", "").upper().strip()
    override_carrier = data.get("override_carrier", "").strip()
    
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    if override_carrier and override_carrier.upper() != "BUSCANDO...":
        carrier_final = override_carrier
    else:
        carrier_final = identificar_carrier(contenedor)
        
    tipo_contenedor = scrapear_datos_naviera(contenedor, carrier_final)
    
    resultado = {
        "container": contenedor,
        "carrier": carrier_final,
        "type": tipo_contenedor,
        "buque": "PENDIENTE",
        "eta": ""
    }
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
