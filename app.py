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

def scrapear_datos_naviera(contenedor, carrier):
    """
    Función de enrutamiento de scraping.
    Ejecuta una lógica distinta de extracción HTML dependiendo de la naviera.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    tipo = "SIN TIPO"
    
    try:
        if carrier == "Hapag-Lloyd":
            # Aquí programaremos la extracción exacta de los nodos HTML de Hapag-Lloyd
            tipo = "PENDIENTE SCRAPING HAPAG"
            
        elif carrier == "MSC":
            # Aquí programaremos la extracción exacta de MSC
            tipo = "PENDIENTE SCRAPING MSC"
            
        elif carrier == "Maersk":
            # Aquí programaremos la extracción exacta de Maersk
            tipo = "PENDIENTE SCRAPING MAERSK"
            
        else:
            tipo = "SCRAPING NO CONFIGURADO"
            
    except Exception as e:
        tipo = f"ERROR: {str(e)}"
        
    return tipo

@app.route('/consultar', methods=['POST'])
def consultar():
    data = request.json
    contenedor = data.get("container", "").upper().strip()
    if not contenedor:
        return jsonify({"error": "No container provided"}), 400
    
    carrier_detectado = identificar_carrier(contenedor)
    
    # Llamamos a la función de scraping web en lugar de la regla temporal
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
