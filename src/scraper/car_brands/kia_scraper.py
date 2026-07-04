# src/scraper/car_brands/kia_scraper.py

import json
import re
import asyncio
from datetime import datetime
from playwright.async_api import Page, TimeoutError
from .base_scraper import parse_html


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
        """
        Scraper principal de Kia. Usa JSON-LD embebido en cada página de modelo
        para extraer versiones y precios de manera confiable.
        """
        print(f"Iniciando scraping para Kia usando {len(self.detail_page_urls)} URLs de la lista maestra...")

        all_final_models = []
        for partial_url in self.detail_page_urls:
            model_url = f"{self.base_url}{partial_url}"
            try:
                extracted = await self._extract_from_jsonld(page, model_url)
                if extracted:
                    all_final_models.extend(extracted)
                    print(f"     ... {len(extracted)} versiones extraídas.")
                else:
                    print(f"     ... No se encontraron datos en JSON-LD.")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"  Error procesando {model_url}: {e.__class__.__name__}: {e}")
                if "closed" in str(e).lower():
                    print("  El navegador se ha cerrado, deteniendo el scraper de Kia.")
                    break

        print(f"Scraping completado para Kia. Total de versiones encontradas: {len(all_final_models)}")
        return all_final_models

    async def _extract_from_jsonld(self, page: Page, model_url: str) -> list:
        """
        Extrae datos de versiones y precios del bloque JSON-LD embebido en la página.
        Kia Colombia usa Schema.org ProductGroup con hasVariant[] que contiene
        todas las versiones con sus precios y URLs.
        """
        model_name_from_url = model_url.split('/')[-1].replace('-', ' ').title()
        print(f"  -> Extrayendo detalles para '{model_name_from_url}' desde: {model_url}")

        await page.goto(model_url, timeout=60000, wait_until='domcontentloaded')

        # Obtener el HTML y buscar el JSON-LD
        html = await page.content()
        soup = parse_html(html)

        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        if not jsonld_scripts:
            print(f"     - No se encontró JSON-LD en {model_url}")
            return []

        extracted_versions = []

        for script_tag in jsonld_scripts:
            try:
                data = json.loads(script_tag.string)
            except (json.JSONDecodeError, TypeError):
                continue

            # El JSON-LD de Kia usa @graph con un objeto ProductGroup
            graph = data.get('@graph', [data]) if isinstance(data, dict) else []

            for node in graph:
                if not isinstance(node, dict):
                    continue

                # Buscar el ProductGroup que contiene hasVariant
                node_type = node.get('@type', '')
                if isinstance(node_type, list):
                    is_product_group = 'ProductGroup' in node_type
                else:
                    is_product_group = node_type == 'ProductGroup'

                if not is_product_group:
                    continue

                variants = node.get('hasVariant', [])
                model_name = node.get('model', model_name_from_url)
                # Clean model name: remove year patterns like "2027"
                model_name_clean = re.sub(r'\s*\d{4}\s*', ' ', model_name).strip()

                for variant in variants:
                    try:
                        version_name = variant.get('name', '')
                        # Extract the short version name from the full name
                        # e.g., "Kia Picanto Vibrant MT 2025 / 2026 | Transmisión mecánica" -> "Vibrant MT"
                        short_name = version_name
                        if '|' in short_name:
                            short_name = short_name.split('|')[0].strip()
                        # Remove brand/model prefix
                        for prefix in ['Kia ', 'kia ']:
                            if short_name.lower().startswith(prefix.lower()):
                                short_name = short_name[len(prefix):]
                        # Remove model name prefix
                        if model_name_clean and short_name.lower().startswith(model_name_clean.lower()):
                            short_name = short_name[len(model_name_clean):].strip()
                        # Remove year patterns
                        short_name = re.sub(r'\b20\d{2}\b', '', short_name).strip()
                        short_name = re.sub(r'\s*/\s*', ' / ', short_name).strip(' /')
                        if not short_name:
                            short_name = version_name

                        offers = variant.get('offers', {})
                        price_str = offers.get('price', '0')
                        price = int(float(price_str))

                        variant_url = variant.get('url', offers.get('url', model_url))

                        if price == 0:
                            continue

                        extracted_versions.append({
                            'marca': 'Kia',
                            'modelo': model_name_clean or model_name_from_url,
                            'version': short_name,
                            'precio': price,
                            'url_fuente': variant_url,
                            'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except Exception as e:
                        print(f"      - Error procesando variante: {e}")
                        continue

        return extracted_versions