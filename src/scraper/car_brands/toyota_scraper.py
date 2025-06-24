# src/scraper/car_brands/toyota_scraper.py

from bs4 import BeautifulSoup
from datetime import datetime
import re
import asyncio
from .base_scraper import BaseScraper

class ToyotaScraper(BaseScraper):
    def __init__(self):
        super().__init__('toyota')
        self.base_url = 'https://www.toyota.com.co'
        
        # Lista Maestra de Modelos (Slugs)
        self.model_slugs = [
            'yaris', 'corolla', 'corolla-cross', 'yaris-cross',
            'land-cruiser-prado', 'land-cruiser-300', 'hilux', 'tundra', "fortuner"
        ]
        
    async def scrape(self, page) -> list:
        """
        Orquestador principal para Toyota:
        1. Construye la URL para cada modelo de la lista maestra.
        2. Visita cada URL y extrae la información detallada.
        """
        print(f"Iniciando scraping para Toyota usando {len(self.model_slugs)} modelos de la lista maestra...")
        
        all_final_models = []
        for slug in self.model_slugs:
            model_url = f"{self.base_url}/vehiculo/{slug}"
            try:
                detailed_models = await self.scrape_model_details(page, model_url)
                if detailed_models:
                    all_final_models.extend(detailed_models)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error extrayendo detalles de {model_url}: {str(e)}")
                continue
        
        print(f"Scraping completado para Toyota. Total de versiones encontradas: {len(all_final_models)}")
        return all_final_models

    async def scrape_model_details(self, page, model_url: str) -> list:
        """
        Extrae los datos del pop-up de precios usando la estructura HTML real.
        """
        print(f"  -> Extrayendo detalles desde: {model_url}")
        await page.goto(model_url, timeout=60000)
        
        try:
            price_button_selector = "#preciobtn"
            await page.wait_for_selector(price_button_selector, timeout=15000)
            await page.locator(price_button_selector).click()
            
            popup_container_selector = ".padre"
            await page.wait_for_selector(popup_container_selector, timeout=10000)
            print("     ... Pop-up de precios abierto y cargado.")
        except Exception as e:
            print(f"     - No se pudo abrir o encontrar el pop-up de precios en {model_url}. Saltando. (Razón: {e})")
            return []

        html = await page.content()
        soup = BeautifulSoup(html, 'lxml')
        
        popup_container = soup.find('div', class_='padre')
        if not popup_container:
            print("     - Error: No se encontró el contenedor del pop-up en el HTML.")
            return []

        model_name_in_popup = popup_container.find('p', class_='p_1').get_text(strip=True)
        pdf_link_tag = soup.find('a', class_='bt_red', text='Ficha técnica')
        pdf_url = pdf_link_tag['href'] if pdf_link_tag else 'No encontrado'
        
        version_name_elements = popup_container.select('.nombre_vihecle')
        year_elements = popup_container.select('.año_2022 .modelo_text')
        price_elements = popup_container.select('.cop .modelo_text')

        if not (len(version_name_elements) == len(year_elements) == len(price_elements) and len(version_name_elements) > 0):
            print(f"     - ADVERTENCIA: Inconsistencia o ausencia de datos en {model_name_in_popup}.")
            return []

        extracted_versions = []
        for version_el, year_el, price_el in zip(version_name_elements, year_elements, price_elements):
            try:
                version_name = version_el.get_text(strip=True)
                year_model = year_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True)
                price = int(re.sub(r'[^\d]', '', price_text)) if price_text else 0

                if not version_name or price == 0: continue

                extracted_versions.append({
                    'marca': 'Toyota',
                    'modelo': model_name_in_popup,
                    'version': version_name,
                    'precio': price,
                    'anio_modelo': year_model,
                    'tipo': self.classify_vehicle(model_name_in_popup),
                    'url_ficha_tecnica': pdf_url,
                    'url_fuente': model_url,
                    'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"      - Error procesando una fila de datos de {model_name_in_popup}: {str(e)}")
        
        print(f"     ... Encontradas {len(extracted_versions)} versiones para {model_name_in_popup}.")
        return extracted_versions

    def classify_vehicle(self, model_name: str) -> str:
        name = model_name.lower()
        if 'hilux' in name or 'land cruiser' in name:
            return 'Pick-Up'
        elif any(x in name for x in ['prado', 'fortuner', 'rav4', 'corolla cross', 'yaris cross', '4runner', 'sequoia']):
            return 'SUV'
        elif 'hiace' in name:
            return 'Van'
        else:
            return 'Automóvil'