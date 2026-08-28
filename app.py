import json
import re
import requests
from bs4 import BeautifulSoup

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
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Maersk almacena los datos en un JSON estructurado dentro del HTML
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if script_tag:
                data = json.loads(script_tag.string)
                # O navegar por el JSON o buscar directamente por expresiones regulares en el texto fuente
                texto_completo = response.text
                
                # Extracción por patrones lógicos (Regex) seguros sobre el código fuente
                # Buscar Tipo de Contenedor (ej: 40' Dry High)
                match_tipo = re.search(r'(40\'\s*Dry\s*High|20\'\s*Dry|40\'\s*DC|20\'\s*DC|40\'\s*HC)', texto_completo, re.IGNORECASE)
                if match_tipo:
                    tipo = normalizar_tipo(match_tipo.group(0))
                
                # Buscar Nombre del Buque (ej: MAERSK MONTE AZUL / 633S)
                match_buque = re.search(r'([A-Z\s]+\/\s*\d+[A-Z]*)', texto_completo)
                if match_buque:
                    buque = match_buque.group(0).strip()
                    
                # Buscar ETA / Fecha de llegada (ej: 06 Sep 2026)
                match_eta = re.search(r'(\d{2}\s+[A-Za-z]{3}\s+\d{4})', texto_completo)
                if match_eta:
                    eta = match_eta.group(0)
                    
    except Exception as e:
        tipo = "ERROR SCRAPING"
        
    return tipo, buque, eta
