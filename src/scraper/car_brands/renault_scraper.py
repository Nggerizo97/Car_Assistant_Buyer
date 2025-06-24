# src/scraper/car_brands/renault_scraper.py

from bs4 import BeautifulSoup
from datetime import datetime
import re
import asyncio
from .base_scraper import BaseScraper

class RenaultScraper(BaseScraper):
    def __init__(self):
        super().__init__('renault')
        self.base_url = 'https://www.renault.com.co'
        
        # Lista Maestra de URLs de Versiones y Precios
        self.version_urls = [
        '/hibridos/arkana-e-tech/versiones-y-precios.html',   
        '/vehiculos/kardian/versiones-y-precios.html',       
        '/vehiculos/duster/versiones-y-precios.html',        
        '/utilitarios/master-chasis/versiones-y-precios.html', 
        '/utilitarios/master-panel/versiones-y-precios.html',  
        '/utilitarios/trafic-panel/versiones-y-precios.html', 
        '/hibridos/duster-e-tech/versiones-y-precios.html',
        '/vehiculos/kwid/versiones-y-precios.html',
        '/electricos/kwid-e-tech/versiones-y-precios.html',
        '/vehiculos/oroch/versiones-y-precios.html',
        '/vehiculos/stepway/versiones-y-precios.html',
        '/vehiculos/sandero/versiones-y-precios.html',
        '/vehiculos/logan/versiones-y-precios.html',
        '/electricos/kangoo-e-tech/versiones-y-precios.html'
        ]
        
    async def scrape(self, page) -> list:
        print(f"Iniciando scraping para Renault usando {len(self.version_urls)} URLs de modelos...")
        
        all_final_models = []
        for partial_url in self.version_urls:
            model_url = f"{self.base_url}{partial_url}"
            try:
                detailed_models = await self.scrape_version_page(page, model_url)
                if detailed_models:
                    all_final_models.extend(detailed_models)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error extrayendo detalles de {model_url}: {str(e)}")
                continue
        
        print(f"Scraping completado para Renault. Total de versiones encontradas: {len(all_final_models)}")
        return all_final_models

    def _get_model_name_from_url(self, url: str) -> str:
        try:
            model_slug = url.split('/')[-2]
            return model_slug.replace('-', ' ').title()
        except:
            return "Modelo Desconocido"

    async def scrape_version_page(self, page, url: str) -> list:
        print(f"  -> Extrayendo detalles desde: {url}")
        await page.goto(url, timeout=60000)
        
        # --- NUEVO: MANEJO DEL BANNER DE COOKIES ---
        try:
            # Selector común para el botón de "Aceptar todo" en banners de OneTrust.
            accept_button_selector = "#onetrust-accept-btn-handler"
            
            # Esperamos al botón por un tiempo corto (5 segundos).
            # Si no aparece, asumimos que no hay banner y continuamos.
            await page.wait_for_selector(accept_button_selector, timeout=5000)
            await page.locator(accept_button_selector).click()
            print("     ... Banner de cookies aceptado.")
            # Esperamos un instante a que la animación del banner desaparezca.
            await page.wait_for_timeout(500)
        except Exception:
            # Si el botón no se encuentra en 5 segundos, no hacemos nada y seguimos.
            print("     ... No se encontró el banner de cookies, o ya fue aceptado. Continuando.")
        
        # --- El resto del código continúa desde aquí ---
        container_selector = ".ModelGradesV2"
        await page.wait_for_selector(container_selector, timeout=30000)
        
        model_name = self._get_model_name_from_url(url)
        extracted_versions = []
        
        version_tabs = await page.locator(".ModelGradesV2__carouselItemLink").all()
        print(f"     ... Encontradas {len(version_tabs)} versiones para {model_name}.")

        for i in range(len(version_tabs)):
            try:
                current_tab = page.locator(".ModelGradesV2__carouselItemLink").nth(i)
                # Forzamos el click aunque otro elemento esté encima (como un overlay semi-transparente)
                await current_tab.click(force=True, timeout=5000)
                await page.wait_for_timeout(500) 
                
                html = await page.content()
                soup = BeautifulSoup(html, 'lxml')
                
                content_area = soup.find('div', class_='ModelGradesV2__content')
                if not content_area: continue
                    
                version_name = content_area.find('div', class_='GradeDetails__version').get_text(strip=True)
                price_text = content_area.find('span', class_='NormalizedPrice').get_text(strip=True)
                price = int(re.sub(r'[^\d]', '', price_text)) if price_text else 0
                if price == 0: continue

                engine_specs = self._get_engine_specs(content_area)

                extracted_versions.append({
                    'marca': 'Renault',
                    'modelo': model_name,
                    'version': version_name,
                    'precio': price,
                    'tipo': self.classify_vehicle(model_name),
                    'transmision': engine_specs.get('Caja de velocidades', 'No especificado'),
                    'combustible': engine_specs.get('Tipo de combustible', 'No especificado'),
                    'potencia_hp': engine_specs.get('Potencia máxima (HP)', 'No especificado'),
                    'url_fuente': url,
                    'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"      - Error procesando una versión de {model_name}: {e}")

        return extracted_versions

    def _get_engine_specs(self, soup_area: BeautifulSoup) -> dict:
        specs = {}
        engine_cards = soup_area.find_all('div', class_='GradeEnginesCard__specification')
        for card in engine_cards:
            label = card.find('p', class_='GradeEnginesCard__dataLabel')
            value = card.find('p', class_='GradeEnginesCard__dataValue')
            if label and value:
                specs[label.get_text(strip=True)] = value.get_text(strip=True)
        return specs

    def classify_vehicle(self, model_name: str) -> str:
        name = model_name.lower()
        if 'duster' in name or 'kardian' in name or 'arkana' in name:
            return 'SUV'
        if 'oroch' in name:
            return 'Pick-Up'
        if 'master' in name or 'trafic' in name or 'kangoo' in name:
            return 'Utilitario'
        else:
            return 'Automóvil'