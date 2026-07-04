# src/scraper/car_brands/renault_scraper.py

import json
import re
import asyncio
from datetime import datetime
from playwright.async_api import Page, TimeoutError
from .base_scraper import BaseScraper, parse_html


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
        """
        Scraper principal de Renault. Usa JSON-LD embebido en cada página
        de versiones y precios para extraer datos de manera confiable.
        """
        print(f"Iniciando scraping para Renault usando {len(self.version_urls)} URLs de modelos...")

        all_final_models = []
        for partial_url in self.version_urls:
            model_url = f"{self.base_url}{partial_url}"
            try:
                extracted = await self._extract_from_jsonld(page, model_url)
                if extracted:
                    all_final_models.extend(extracted)
                await asyncio.sleep(1)
            except Exception as e:
                print(f"  Error extrayendo detalles de {model_url}: {e}")
                continue

        print(f"Scraping completado para Renault. Total de versiones encontradas: {len(all_final_models)}")
        return all_final_models

    def _get_model_name_from_url(self, url: str) -> str:
        try:
            model_slug = url.split('/')[-2]
            return model_slug.replace('-', ' ').title()
        except Exception:
            return "Modelo Desconocido"

    async def _extract_from_jsonld(self, page, url: str) -> list:
        """
        Extrae datos del JSON-LD embebido en las páginas de Renault.
        Renault Colombia usa Schema.org ProductModel con @reverse.schema:isVariantOf[]
        que contiene todas las versiones con nombres y precios.
        """
        model_name = self._get_model_name_from_url(url)
        print(f"  -> Extrayendo detalles para '{model_name}' desde: {url}")

        await page.goto(url, timeout=60000, wait_until='domcontentloaded')

        html = await page.content()
        soup = parse_html(html)

        jsonld_scripts = soup.find_all('script', type='application/ld+json')
        if not jsonld_scripts:
            print(f"     - No se encontró JSON-LD en {url}")
            return []

        extracted_versions = []

        for script_tag in jsonld_scripts:
            try:
                data = json.loads(script_tag.string)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(data, dict):
                continue

            # Renault uses schema: prefix in their JSON-LD
            # Look for ProductModel / Car type
            node_type = data.get('@type', [])
            if isinstance(node_type, str):
                node_type = [node_type]

            is_product = any(t in ['schema:ProductModel', 'schema:Car', 'ProductModel', 'Car']
                            for t in node_type)

            if not is_product:
                continue

            # Get the main model name
            main_name = data.get('schema:name', data.get('name', model_name))

            # Get variants from @reverse.schema:isVariantOf
            reverse = data.get('@reverse', {})
            variants = reverse.get('schema:isVariantOf', [])

            if not variants:
                # Try direct offers if no variants
                offers = data.get('schema:offers', data.get('offers', {}))
                if offers:
                    price_spec = offers.get('schema:priceSpecification',
                                            offers.get('priceSpecification', {}))
                    price_str = price_spec.get('schema:price',
                                               offers.get('schema:price',
                                                           offers.get('price', '0')))
                    price = self._parse_price(price_str)
                    if price > 0:
                        extracted_versions.append({
                            'marca': 'Renault',
                            'modelo': main_name,
                            'version': 'Base',
                            'precio': price,
                            'tipo': self.classify_vehicle(main_name),
                            'url_fuente': url,
                            'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                continue

            for variant in variants:
                try:
                    version_name = variant.get('schema:name', variant.get('name', ''))
                    # Clean version name: remove model prefix
                    clean_name = version_name
                    if main_name and clean_name.lower().startswith(main_name.lower()):
                        clean_name = clean_name[len(main_name):].strip()
                    if not clean_name:
                        clean_name = version_name

                    offers = variant.get('schema:offers', variant.get('offers', {}))
                    price_spec = offers.get('schema:priceSpecification',
                                            offers.get('priceSpecification', {}))
                    price_str = price_spec.get('schema:price',
                                               offers.get('schema:price',
                                                           offers.get('price', '0')))
                    price = self._parse_price(price_str)

                    if price == 0:
                        continue

                    currency = price_spec.get('schema:priceCurrency',
                                              offers.get('schema:priceCurrency', 'COP'))

                    extracted_versions.append({
                        'marca': 'Renault',
                        'modelo': main_name,
                        'version': clean_name,
                        'precio': price,
                        'tipo': self.classify_vehicle(main_name),
                        'url_fuente': url,
                        'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    print(f"      - Error procesando variante de {main_name}: {e}")
                    continue

        if extracted_versions:
            print(f"     ... {len(extracted_versions)} versiones extraídas para {model_name}.")
        else:
            print(f"     ... No se encontraron datos de versiones en JSON-LD para {model_name}.")

        return extracted_versions

    def _parse_price(self, price_str) -> int:
        """Parse a price string that might be scientific notation or regular number."""
        try:
            return int(float(str(price_str)))
        except (ValueError, TypeError):
            # Try extracting digits
            digits = re.sub(r'[^\d.]', '', str(price_str))
            if digits:
                return int(float(digits))
            return 0

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