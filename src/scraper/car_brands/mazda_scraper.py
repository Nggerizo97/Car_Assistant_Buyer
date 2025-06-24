# src/scraper/car_brands/mazda_scraper.py

from bs4 import BeautifulSoup
from datetime import datetime
import re
import asyncio
from .base_scraper import BaseScraper

class MazdaScraper(BaseScraper):
    def __init__(self):
        super().__init__('mazda')
        self.base_url = 'https://www.mazda.com.co'
        # La página principal ya contiene toda la información que necesitamos para empezar.
        self.start_url = 'https://www.mazda.com.co/'
        
    async def scrape(self, page) -> list:
        """
        Para Mazda, toda la información inicial está en una sola página.
        No necesitamos navegar a múltiples URLs de categorías.
        """
        print(f"Iniciando scraping para Mazda desde: {self.start_url}")
        
        await page.goto(self.start_url, timeout=60000)
        
        # Esperamos a que las "tarjetas" de los vehículos estén presentes en la página.
        card_selector = "div.vehiculo"
        await page.wait_for_selector(card_selector, timeout=30000)
        
        html = await page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        all_models = []
        vehicle_cards = soup.select(card_selector)
        print(f"  -> Encontradas {len(vehicle_cards)} tarjetas de vehículos en la página.")

        for card in vehicle_cards:
            try:
                model_name = card.find('h2', class_='uxTituloAutomovil').get_text(strip=True)
                price_text = card.find('p', class_='precio').get_text(strip=True)
                price = int(re.sub(r'[^\d]', '', price_text)) if price_text else 0

                # Obtenemos el link a la página de detalle
                link_tag = card.find('a', href=True)
                detail_url = f"{self.base_url}{link_tag['href']}" if link_tag else 'No encontrado'
                
                # Determinamos la categoría encontrando el 'div' padre con la clase 'categoria'
                category_div = card.find_parent('div', class_='categoria')
                # La segunda clase del div (ej. 'suvs', 'hibridos') es el tipo
                vehicle_type = category_div['class'][1].replace('-', ' ').title() if category_div and len(category_div['class']) > 1 else 'No especificado'

                if not model_name or price == 0:
                    continue

                all_models.append({
                    'marca': 'Mazda',
                    'modelo': model_name,
                    'version': 'Desde', # Indicamos que es un precio base
                    'precio': price,
                    'anio_modelo': 'N/A', # Esta info no está en la tarjeta principal
                    'tipo': vehicle_type,
                    'url_ficha_tecnica': 'N/A', # Esta info está en la página de detalle
                    'url_fuente': detail_url, # Guardamos el link para un posible scraper de Nivel 2
                    'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"      - Error procesando una tarjeta de Mazda: {e}")
        
        print(f"Scraping completado para Mazda. Total de modelos encontrados: {len(all_models)}")
        return all_models