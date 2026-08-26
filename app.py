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

def scrapear_datos_naviera(contenedor, carrier):
    carrier_upper = carrier.upper()
    resultado = "SIN DATOS"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Lógica específica para TRITON
            if "TRITON" in carrier_upper:
                url = f"https://www.tritoncontainer.com/CustomerTools/UnitInquiry?UnitNumbers={contenedor}"
                page.goto(url, wait_until="networkidle", timeout=15000)
                
                # Le damos 4 segundos de ventaja a la página para que inyecte la tabla
                page.wait_for_timeout(4000) 
                
                # Extraemos todo el texto y lo pasamos a mayúsculas
                texto_web = page.evaluate("document.body.innerText").upper()
                browser.close()
                
                # Buscamos las coincidencias exactas en el texto extraído
                if "40' DRY VAN" in texto_web or "40' STANDARD" in texto_web:
                    return "40'DC"
                elif "20' DRY VAN" in texto_web or "20' STANDARD" in texto_web:
                    return "20'DC"
                elif "HIGH CUBE" in texto_web or "40' HC" in texto_web:
                    return "40'HQ"
                elif "OPEN TOP" in texto_web:
                    return "OT"
                elif "REEFER" in texto_web:
                    return "REEFER"
                else:
                    return "TABLA CARGADA, TIPO NO RECONOCIDO"
                    
            # Aquí sumaremos Maersk, MSC, etc. en el siguiente paso
            else:
                browser.close()
                return "SCRAPING PENDIENTE DE CONFIGURAR"
                
    except Exception as e:
        resultado = f"ERROR NAVEGADOR: {str(e)}"
        
    return resultado

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
