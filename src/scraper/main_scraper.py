# src/scraper/main_scraper.py
import asyncio
from playwright.async_api import async_playwright, Page
import pandas as pd
import importlib
from .config import (
    HEADLESS, TIMEOUT, USER_AGENTS, DELAY_BETWEEN_REQUESTS,
    RAW_DIR, PROCESSED_DIR, get_output_filename, BRAND_URLS
)
ALL_BRANDS = [
    'kia', 'toyota', 'renault', 'mazda', 'chevrolet', 'suzuki',
    'nissan', 'hyundai', 'ford', 'volkswagen', 'foton', 'jac',
    'chery', 'volvo'
]

brand_scrapers = {}
for brand_name in ALL_BRANDS:
    try:
        # Asumimos que el nombre de la clase sigue el patrón MarcaScraper
        class_name = f"{brand_name.capitalize()}Scraper"
        module = importlib.import_module(f".car_brands.{brand_name}_scraper", package="src.scraper")
        scraper_class = getattr(module, class_name)
        brand_scrapers[brand_name] = scraper_class
        print(f"INFO: Scraper para '{brand_name}' cargado exitosamente.")
    except (ImportError, AttributeError):
        print(f"ADVERTENCIA: No se encontró el scraper para '{brand_name}'. Saltando.")


async def block_unnecessary_resources(page: Page):
    """Bloquea la carga de imágenes, css y fuentes para acelerar la navegación."""
    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "stylesheet", "font"] else route.continue_())


async def run_brand_scraper(page: Page, brand_name: str, scraper_class):
    """
    Ejecuta un scraper para una marca específica usando una página ya existente.
    """
    scraper = scraper_class()
    try:
        # Pasamos la página ya configurada al scraper
        data = await scraper.scrape(page)
        return data
    except Exception as e:
        print(f"Error CRÍTICO durante el scraping de {brand_name.capitalize()}: {e.__class__.__name__}: {e}")
        return []


async def main():
    """
    Función principal que lanza UN SOLO NAVEGADOR y lo reutiliza
    para todos los scrapers, mejorando rendimiento y estabilidad.
    """
    all_data = []
    
    if not brand_scrapers:
        print("ERROR: No se encontró ningún scraper válido para ejecutar.")
        return

    async with async_playwright() as p:
        # 1. Lanzamos el navegador UNA SOLA VEZ
        browser = await p.chromium.launch(headless=HEADLESS)
        page = await browser.new_page()
        
        # 2. Aplicamos el bloqueo de recursos a la página
        await block_unnecessary_resources(page)

        print("\n--- INICIANDO EJECUCIÓN DE SCRAPERS DISPONIBLES ---")
        for brand_name, scraper_class in brand_scrapers.items():
            # 3. Pasamos la misma página a cada scraper
            brand_data = await run_brand_scraper(page, brand_name, scraper_class)
            if brand_data:
                all_data.extend(brand_data)
            
            # Mantenemos el delay para ser corteses con los servidores
            if len(brand_scrapers) > 1:
                await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
        
        # 4. Cerramos el navegador al final de todo el proceso
        await browser.close()

    # Guardado de datos sin cambios
    if all_data:
        output_file = PROCESSED_DIR / 'carros_actualizados.csv'
        df = pd.DataFrame(all_data)
        df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\nDatos guardados en {output_file}. Total de versiones de vehículos: {len(df)}")
    else:
        print("\nNo se encontraron datos para guardar de los scrapers ejecutados.")

if __name__ == "__main__":
    asyncio.run(main())