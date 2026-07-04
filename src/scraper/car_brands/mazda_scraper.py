# src/scraper/car_brands/mazda_scraper.py

import json
import re
import asyncio
from datetime import datetime
from playwright.async_api import Page
from .base_scraper import BaseScraper, parse_html


class MazdaScraper(BaseScraper):
    def __init__(self):
        super().__init__('mazda')
        self.base_url = 'https://www.mazda.com.co'
        self.start_url = 'https://www.mazda.com.co/vehiculos/'

    async def scrape(self, page) -> list:
        """
        Para Mazda, la página /vehiculos/ contiene datos JSON embebidos
        en window.mxp.data con toda la información de vehículos (nombres,
        precios, URLs, categorías). Extraemos directamente de esa estructura.
        """
        print(f"Iniciando scraping para Mazda desde: {self.start_url}")

        await page.goto(self.start_url, timeout=60000, wait_until='domcontentloaded')

        # Extraemos el HTML y buscamos los datos embebidos en scripts
        html = await page.content()
        soup = parse_html(html)

        all_models = []

        # Estrategia 1: Extraer de window.mxp.data (datos JSON embebidos en <script>)
        all_models = self._extract_from_mxp_data(html)

        if all_models:
            print(f"  -> Extraídos {len(all_models)} vehículos desde datos embebidos (mxp.data).")
        else:
            # Estrategia 2: Fallback — intentar parsear datos de showroom del DOM
            print(f"  -> No se encontraron datos en mxp.data. Intentando DOM...")
            all_models = self._extract_from_dom(soup)

        print(f"Scraping completado para Mazda. Total de modelos encontrados: {len(all_models)}")
        return all_models

    def _extract_from_mxp_data(self, html: str) -> list:
        """
        Extrae datos de vehículos del JSON embebido en window.mxp.data.
        La estructura contiene navegación con 'primaryNav.links' que tiene
        la lista de vehículos con precios.
        """
        all_models = []

        # Buscar todos los bloques JSON pusheados a mxp.data
        pattern = r'window\.mxp\.data\.push\(JSON\.parse\(\'(.*?)\'\)\)'
        matches = re.findall(pattern, html, re.DOTALL)

        for match in matches:
            try:
                # El JSON contiene escapes Unicode como \\u003c
                json_str = match.replace("\\'", "'")
                data = json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                continue

            # Navegar la estructura para encontrar las listas de vehículos
            props = data.get('props', {})

            # Buscar en primaryNav.links (navegación del header)
            primary_nav = props.get('primaryNav', {})
            nav_links = primary_nav.get('links', [])

            for link in nav_links:
                if link.get('type') != 'car':
                    continue

                model_name = link.get('text', link.get('model', '')).strip()
                if not model_name:
                    continue

                # Obtener precio
                new_price = link.get('newPrice', {})
                price = 0
                if new_price:
                    raw_price = new_price.get('rawPrice', 0)
                    if raw_price:
                        price = int(float(raw_price))

                if price == 0:
                    raw = link.get('price', 0)
                    if raw:
                        price = int(float(raw))

                if price == 0:
                    continue

                detail_url = link.get('link', '')
                if detail_url and not detail_url.startswith('http'):
                    detail_url = f"{self.base_url}{detail_url}"

                # Obtener categoría de sub-links
                category = 'No especificado'
                sub_links = link.get('links', [])
                if sub_links:
                    first_sub = sub_links[0]
                    cat = first_sub.get('category', '')
                    if cat:
                        category = cat

                all_models.append({
                    'marca': 'Mazda',
                    'modelo': model_name.upper(),
                    'version': 'Desde',
                    'precio': price,
                    'tipo': category if category != 'No especificado' else self._classify(model_name),
                    'url_fuente': detail_url,
                    'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        return all_models

    def _extract_from_dom(self, soup) -> list:
        """Fallback: intenta extraer datos del DOM si mxp.data no funciona."""
        all_models = []

        # Buscar tarjetas de showroom
        cards = soup.select('.showroom-card, .vehicle-card, [data-model-name]')
        for card in cards:
            try:
                name_el = card.find(['h2', 'h3', '.model-name'])
                price_el = card.find(['.price', '.precio'])

                if not name_el or not price_el:
                    continue

                model_name = name_el.get_text(strip=True)
                price_text = price_el.get_text(strip=True)
                price = int(re.sub(r'[^\d]', '', price_text)) if price_text else 0

                if price == 0:
                    continue

                link_tag = card.find('a', href=True)
                detail_url = f"{self.base_url}{link_tag['href']}" if link_tag else 'N/A'

                all_models.append({
                    'marca': 'Mazda',
                    'modelo': model_name,
                    'version': 'Desde',
                    'precio': price,
                    'tipo': self._classify(model_name),
                    'url_fuente': detail_url,
                    'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            except Exception as e:
                print(f"      - Error procesando tarjeta de Mazda: {e}")

        return all_models

    def _classify(self, model_name: str) -> str:
        name = model_name.lower()
        if any(x in name for x in ['cx-', 'cx ']):
            return 'SUV'
        elif any(x in name for x in ['bt-50', 'bt50']):
            return 'Pick-Up'
        elif any(x in name for x in ['mazda2', 'mazda 2', 'mazda3', 'mazda 3', 'mazda6', 'mazda 6']):
            return 'Automóvil'
        elif 'mx' in name:
            return 'Deportivo'
        else:
            return 'Automóvil'