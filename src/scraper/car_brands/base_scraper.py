# src/scraper/car_brands/base_scraper.py
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re
from datetime import datetime
from typing import Dict, List
import asyncio
import random

class BaseScraper:
    def __init__(self, brand: str):
        self.brand = brand.lower()
        self.url = None
        self.models = []
        
    async def navigate_to_models_page(self, page):
        """Navega a la página de modelos de la marca"""
        raise NotImplementedError("Debe implementarse en cada scraper específico")
        
    async def extract_model_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extrae datos de los modelos de la página"""
        raise NotImplementedError("Debe implementarse en cada scraper específico")
        
    async def scrape(self, page) -> List[Dict]:
        """Método principal que ejecuta todo el scraping"""
        try:
            print(f"Iniciando scraping para {self.brand.capitalize()}...")
            
            # Navegar a la página principal de modelos
            await self.navigate_to_models_page(page)
            
            # Esperar aleatoriamente entre 1-3 segundos
            await asyncio.sleep(random.uniform(1, 3))
            
            # Obtener HTML y parsear
            html = await page.content()
            soup = BeautifulSoup(html, 'lxml')
            
            # Extraer datos de los modelos
            self.models = await self.extract_model_data(soup)
            
            print(f"Scraping completado para {self.brand.capitalize()}. Modelos encontrados: {len(self.models)}")
            return self.models
            
        except Exception as e:
            print(f"Error en scraping de {self.brand.capitalize()}: {str(e)}")
            return []