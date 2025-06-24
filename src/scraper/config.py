# src/scraper/config.py
import os
from pathlib import Path
from datetime import datetime

# Configuración general del scraper
HEADLESS = False
TIMEOUT = 45000  # 45 segundos
MAX_RETRIES = 3
DELAY_BETWEEN_REQUESTS = 2  # segundos

# User Agents para rotación
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
]

# URLs de las marcas (actualizado con todas las que proporcionaste)
BRAND_URLS = {
    'toyota': 'https://www.toyota.com.co/',
    'renault': 'https://www.renault.com.co/',
    'chevrolet': 'https://www.chevrolet.com.co/',
    'mazda': 'https://www.mazda.com.co/',
    'kia': 'https://kia.com.co/',
    'suzuki': 'https://www.suzukiautos.com.co/',
    'nissan': 'https://www.nissan.com.co/',
    'hyundai': 'https://hyundaicolombia.co/',
    'ford': 'https://www.ford.com.co/',
    'volkswagen': 'https://www.volkswagen.co/',
    'foton': 'https://www.foton.com.co/',
    'jac': 'https://jacmotors.com.co/',
    'chery': 'https://www.chery.com.co/',
    'volvo': 'https://www.volvocars.com/co/'
}

# Rutas de archivos
BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'

# Crear directorios si no existen
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

def get_output_filename(brand=None):
    """Genera nombres de archivo consistentes"""
    date_str = datetime.now().strftime("%Y%m%d_%H%M")
    if brand and brand.lower() in BRAND_URLS:
        return f"carros_{brand.lower()}_{date_str}.json"
    return f"carros_todos_{date_str}.json"