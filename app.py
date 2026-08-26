from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

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
    "CLHU": "Textainer", "SEGU": "Seaco", "CAIU": "CAI International"
}

def identificar_carrier(contenedor):
    contenedor = contenedor.upper().strip()
    if len(contenedor) < 4:
        return "DESCONOCIDO"
    prefijo_4 = contenedor[:4]
    prefijo_3 = contenedor[:3]
    return PREFIJOS_NAVIERAS.get(prefijo_4, PREFIJOS_NAVIERAS.get(prefijo_3, "OTRA / LEASING"))

def extraer_maersk(contenedor, headers):
    try:
        url = f"https://www.maersk.com/tracking/{contenedor}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Las webs modernas cargan el HTML vacío y luego inyectan los datos con JS.
            # Buscamos patrones básicos en el DOM inicial.
            html_text = soup.text.upper()
            if "20" in html_text or "40" in html_text:
                return "DOM INICIAL CARGADO"
            return "DATOS OCULTOS POR JS"
        return f"BLOQUEO HTTP {response.status_code}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def extraer_msc(contenedor, headers):
    try:
        url = f"https://www.msc.com/en/track-a-shipment?trackingNumber={contenedor}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            html_text = soup.text.upper()
            return "DATOS OCULTOS POR JS"
        return f"BLOQUEO HTTP {response.status_code}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def extraer_cma(contenedor, headers):
    try:
        url = f"https://www.cma-cgm.com/ebusiness/tracking/search?reference={contenedor}"
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            html_text = soup.text.upper()
            return "DATOS OCULTOS POR JS"
        return f"BLOQUEO HTTP {response.status_code}"
    except Exception as e:
        return f"ERROR: {str(e)}"

def scrapear_datos_naviera(contenedor, carrier):
    # Simulamos ser un navegador real para evitar bloqueos inmediatos
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    if carrier == "Maersk":
        return extraer_maersk(contenedor, headers)
    elif carrier == "MSC":
        return extraer_msc(contenedor, headers)
    elif carrier == "CMA CGM":
        return extraer_cma(contenedor, headers)
    else:
        return "SCRAPING NO CONFIGURADO"

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json
    contenedor = data.get("container", "").upper().strip()
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    carrier_detectado = identificar_carrier(contenedor)
    tipo_contenedor = scrapear_datos_naviera(contenedor, carrier_detectado)
    
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
