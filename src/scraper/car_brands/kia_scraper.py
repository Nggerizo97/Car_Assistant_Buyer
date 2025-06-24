# src/scraper/car_brands/kia_scraper.py

from bs4 import BeautifulSoup
from datetime import datetime
import re
import asyncio
from playwright.async_api import Page, TimeoutError

class KiaScraper:
    def __init__(self):
        self.brand = 'kia'
        self.base_url = 'https://www.kia.com.co'
        self.detail_page_urls = [
            '/nuestros-vehiculos/ev3', '/nuestros-vehiculos/picanto',
            '/nuestros-vehiculos/carro-soluto', '/nuestros-vehiculos/k3',
            '/nuestros-vehiculos/k4', '/nuestros-vehiculos/k3-cross',
            '/nuestros-vehiculos/hibrido-kia-stonic', '/nuestros-vehiculos/suv-sonet',
            '/nuestros-vehiculos/hibrido-niro', '/nuestros-vehiculos/seltos-2',
            '/nuestros-vehiculos/suv-sportage', '/nuestros-vehiculos/nueva-sorento',
            '/nuestros-vehiculos/suv-carnival', '/nuestros-vehiculos/ev6',
            '/nuestros-vehiculos/ev5', '/nuestros-vehiculos/ev9'
        ]
        
    async def scrape(self, page: Page) -> list:
        print(f"Iniciando scraping para Kia usando {len(self.detail_page_urls)} URLs de la lista maestra...")
        
        all_final_models = []
        for partial_url in self.detail_page_urls:
            model_url = f"{self.base_url}{partial_url}"
            try:
                detailed_models = await self._scrape_detail_page(page, model_url)
                if detailed_models:
                    all_final_models.extend(detailed_models)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Error mayor procesando la URL {model_url}: {e.__class__.__name__}: {e}")
                if "closed" in str(e).lower():
                    print("El navegador se ha cerrado, deteniendo el scraper de Kia.")
                    break
        
        print(f"Scraping completado para Kia. Total de versiones encontradas: {len(all_final_models)}")
        return all_final_models

    async def _scrape_detail_page(self, page: Page, model_url: str) -> list:
        model_name_from_url = model_url.split('/')[-1].replace('-', ' ').title()
        print(f"  -> Extrayendo detalles para '{model_name_from_url}' desde: {model_url}")
        
        await page.goto(model_url, timeout=60000, wait_until='domcontentloaded')
        
        try:
            await page.locator('[aria-label*="Cerrar" i], #onetrust-accept-btn-handler').first.click(timeout=7000)
            print("     ... Pop-up o banner cerrado.")
            await page.wait_for_timeout(500)
        except (TimeoutError, Exception):
            print("     ... No se encontró pop-up o banner, continuando.")

        version_slider_selector = ".swiper-slide"
        try:
            await page.wait_for_selector(version_slider_selector, timeout=20000)
        except TimeoutError:
            print(f"     - No se encontró la sección de versiones para '{model_name_from_url}'.")
            return []
            
        version_tabs = await page.locator(version_slider_selector).all()
        print(f"     ... Encontradas {len(version_tabs)} versiones para interactuar.")
        
        extracted_versions = []
        model_name_on_page = (await page.locator("h1, h2").first.inner_text()).strip()

        for i in range(len(version_tabs)):
            try:
                current_tab = page.locator(version_slider_selector).nth(i)
                await current_tab.click(timeout=10000)
                await page.wait_for_timeout(750) # Aumentamos la pausa a 750ms para más seguridad

                html = await page.content()
                soup = BeautifulSoup(html, 'lxml')
                
                active_slide = soup.find('div', class_='swiper-slide-active')
                if not active_slide:
                    all_slides = soup.select('.swiper-slide')
                    active_slide = all_slides[i] if i < len(all_slides) else None
                
                if not active_slide: continue

                # --- LÓGICA DE EXTRACCIÓN POSICIONAL (A PRUEBA DE BALAS) ---
                header = active_slide.find('div', class_='bg-midnight-black')
                if not header: continue
                
                p_tags = header.find_all('p', limit=2) # Buscamos máximo 2 párrafos
                
                # Verificación de seguridad: debemos tener exactamente 2 párrafos
                if len(p_tags) < 2: continue

                version_name = p_tags[0].get_text(strip=True)
                price_text = p_tags[1].get_text(strip=True)
                price = int(re.sub(r'[^\d]', '', price_text))
                
                if not version_name or price == 0: continue

                features = [li.get_text(strip=True) for li in active_slide.select("div.prose li")]
                
                extracted_versions.append({
                    'marca': 'Kia', 'modelo': model_name_on_page,
                    'version': version_name, 'precio': price,
                    'caracteristicas': " | ".join(features),
                    'url_fuente': model_url,
                    'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"      - Error procesando la versión #{i+1} de {model_name_from_url}: {e.__class__.__name__}")
                continue

        print(f"     ... Extracción finalizada. {len(extracted_versions)} versiones válidas encontradas.")
        return extracted_versions