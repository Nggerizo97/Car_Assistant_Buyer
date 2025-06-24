import pandas as pd
import json
from pathlib import Path
import hashlib
import logging
from typing import Dict, List, Any
import sys
import re
from datetime import datetime

# --- CONFIGURACIÓN DE LOGGING A PRUEBA DE ERRORES DE UNICODE ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('data_processing.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self, project_root: Path = None):
        """Inicializa con la ruta del proyecto (auto-detectada si no se provee)"""
        self.project_root = project_root or self._find_project_root()
        logger.info(f"Usando directorio raíz del proyecto: {self.project_root}")
        
        self.data_dir = self.project_root / 'data'
        self.processed_dir = self.data_dir / 'processed'
        self.raw_dir = self.data_dir / 'raw'
        
        self._ensure_directories()
        
        self.input_csv = self.processed_dir / 'carros_actualizados.csv'
        self.clean_csv = self.processed_dir / 'carros_limpios.csv'
        self.clean_json = self.processed_dir / 'carros_limpios.json'
        self.historical_json = self.raw_dir / 'carros_scraped_historico.json'

    def _find_project_root(self) -> Path:
        """Busca recursivamente la raíz del proyecto buscando el archivo 'requirements.txt'."""
        current_path = Path(__file__).resolve()
        for parent in current_path.parents:
            if (parent / 'requirements.txt').exists():
                return parent
        return current_path.parents[3] 

    def _ensure_directories(self):
        """Crea los directorios necesarios si no existen."""
        try:
            self.processed_dir.mkdir(parents=True, exist_ok=True)
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Directorios de datos verificados en: {self.data_dir}")
        except Exception as e:
            logger.error(f"No se pudo crear directorios: {str(e)}")
            raise

    def run_pipeline(self) -> bool:
        """Ejecuta todo el pipeline de procesamiento."""
        try:
            logger.info("Iniciando pipeline de procesamiento de datos...")
            df = self._load_input_data()
            clean_df = self._clean_data(df)
            self._save_outputs(clean_df)
            logger.info("✅ Pipeline completado exitosamente.")
            return True
        except Exception as e:
            logger.error(f"❌ Error en el pipeline: {str(e)}", exc_info=True)
            return False

    def _load_input_data(self) -> pd.DataFrame:
        """Carga el archivo CSV de entrada."""
        logger.info(f"Cargando datos desde: {self.input_csv}")
        if not self.input_csv.exists():
            raise FileNotFoundError(f"No se encontró el archivo de entrada: {self.input_csv}")
        return pd.read_csv(self.input_csv)

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Realiza todas las transformaciones de limpieza."""
        logger.info("Iniciando limpieza de datos...")
        
        df = df.copy()

        # --- SOLUCIÓN: De-duplicación Inteligente ---
        initial_count = len(df)
        subset_cols = ['marca', 'modelo', 'version']
        subset_cols_exist = [col for col in subset_cols if col in df.columns]
        if subset_cols_exist:
            df.drop_duplicates(subset=subset_cols_exist, keep='first', inplace=True)
        logger.info(f"Removidos {initial_count - len(df)} duplicados por la combinación marca/modelo/versión.")
        
        # Limpieza de precios
        df['precio'] = pd.to_numeric(
            df['precio'].astype(str).str.replace(r'[^\d]', '', regex=True),
            errors='coerce'
        )
        
        # Normalización de tipo y año
        df['tipo'] = self._normalize_vehicle_type(df['tipo'])
        df['anio_modelo'] = self._calculate_model_year(df)
        
        # Corrección de versión para Mazda
        mazda_mask = (df['marca'] == 'Mazda') & (df['version'] == 'Desde')
        df.loc[mazda_mask, 'version'] = 'Modelo Base'

        # Procesamiento de características
        if 'caracteristicas' not in df.columns: df['caracteristicas'] = ''
        df['caracteristicas'] = df['caracteristicas'].fillna('')
        df['caracteristicas_detalladas'] = df['caracteristicas'].apply(self._parse_features)
        
        # Extracción de especificaciones técnicas
        tech_specs_df = df['caracteristicas_detalladas'].apply(self._extract_tech_specs).add_prefix('ext_')
        
        cols_to_drop = ['transmision', 'combustible', 'potencia_hp']
        df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
        
        df = pd.concat([df, tech_specs_df], axis=1)
        
        # Clasificación y IDs
        df['segmento'] = df['precio'].apply(self._classify_segment)
        df['id'] = df.apply(self._generate_vehicle_id, axis=1)
        
        df = df.rename(columns={
            'ext_transmision': 'transmision',
            'ext_combustible': 'combustible',
            'ext_potencia_hp': 'potencia_hp'
        })
        
        final_columns_order = [
            'id', 'marca', 'modelo', 'version', 'precio', 'segmento', 'tipo',
            'anio_modelo', 'transmision', 'combustible', 'potencia_hp',
            'caracteristicas', 'caracteristicas_detalladas',
            'url_fuente', 'url_ficha_tecnica', 'fecha_extraccion'
        ]
        
        existing_cols_in_order = [col for col in final_columns_order if col in df.columns]
        return df[existing_cols_in_order]

    def _save_outputs(self, clean_df: pd.DataFrame):
        logger.info("Guardando resultados...")
        clean_df.to_csv(self.clean_csv, index=False, encoding='utf-8-sig')
        df_for_json = clean_df.copy()
        if 'caracteristicas_detalladas' in df_for_json.columns:
             df_for_json['caracteristicas_detalladas'] = df_for_json['caracteristicas_detalladas'].apply(lambda x: x if isinstance(x, list) else [])
        df_for_json.to_json(self.clean_json, orient='records', force_ascii=False, indent=2)
        historical_data = {
            'metadata': {'fecha_procesamiento': datetime.now().isoformat(), 'version': '1.0'},
            'data': json.loads(df_for_json.to_json(orient='records'))
        }
        with open(self.historical_json, 'w', encoding='utf-8') as f:
            json.dump(historical_data, f, ensure_ascii=False, indent=2)
        logger.info(f"""
        📁 Resultados guardados:
        - CSV limpio: {self.clean_csv}
        - JSON limpio: {self.clean_json}
        - JSON histórico: {self.historical_json}
        """)

    # --- MÉTODOS AUXILIARES (HELPERS) ---
    @staticmethod
    def _calculate_model_year(df: pd.DataFrame) -> pd.Series:
        """Calcula el año-modelo basado en la fecha actual y lo aplica a toda la columna."""
        now = datetime.now()
        calculated_model_year = now.year + 1 if now.month > 6 else now.year
        logger.info(f"Estableciendo el año del modelo para todos los registros a: {calculated_model_year}")
        return pd.Series([calculated_model_year] * len(df), index=df.index)

    @staticmethod
    def _normalize_vehicle_type(series: pd.Series) -> pd.Series:
        series = series.astype(str)
        type_map = {
            'automóvil': 'automovil', 'suv': 'suv', 'pick-up': 'pickup',
            'vehiculos': 'automovil', 'suvs': 'suv', 'hibridos': 'hibrido',
            'deportivos': 'deportivo', 'utilitario': 'utilitario'
        }
        return series.str.lower().map(type_map).fillna('otro')

    @staticmethod
    def _parse_features(feature_str: str) -> List[Dict[str, Any]]:
        if pd.isna(feature_str) or not str(feature_str).strip(): return []
        features = []
        for item in str(feature_str).split('|'):
            item = item.strip()
            if not item: continue
            if ':' in item:
                key, val = map(str.strip, item.split(':', 1))
                features.append({'nombre': key, 'valor': val})
            else:
                features.append({'nombre': item, 'valor': True})
        return features

    @staticmethod
    def _extract_tech_specs(features: List[Dict[str, Any]]) -> pd.Series:
        specs = {'transmision': None, 'combustible': None, 'potencia_hp': None}
        if not isinstance(features, list): return pd.Series(specs)
        for feat in features:
            name = feat.get('nombre', '').lower()
            val = feat.get('valor', '')
            if any(t in name for t in ['transmisión', 'transmision', 'caja']):
                specs['transmision'] = str(val)
            elif 'combustible' in name:
                specs['combustible'] = DataProcessor._normalize_fuel_type(val)
            elif any(p in name for p in ['hp', 'potencia', 'kw', 'cv']):
                specs['potencia_hp'] = DataProcessor._parse_power(val)
        return pd.Series(specs)

    @staticmethod
    def _normalize_fuel_type(fuel_str: Any) -> str:
        if not fuel_str or pd.isna(fuel_str): return 'No especificado'
        fuel = str(fuel_str).lower()
        if 'gasolina' in fuel: return 'gasolina'
        if 'diésel' in fuel or 'diesel' in fuel: return 'diesel'
        if 'eléctrico' in fuel or 'electrico' in fuel: return 'electrico'
        if 'híbrido' in fuel or 'hibrido' in fuel: return 'hibrido'
        return fuel_str

    @staticmethod
    def _parse_power(power_str: Any) -> float:
        if pd.isna(power_str): return None
        numbers = re.findall(r'\d+\.?\d*', str(power_str))
        return float(numbers[0]) if numbers else None

    @staticmethod
    def _classify_segment(price: float) -> str:
        if pd.isna(price): return 'desconocido'
        if price < 80_000_000: return 'economico'
        if price < 120_000_000: return 'medio'
        if price < 200_000_000: return 'premium'
        return 'lujo'

    @staticmethod
    def _generate_vehicle_id(row: pd.Series) -> str:
        base_str = f"{row.get('marca', '')}_{row.get('modelo', '')}_{row.get('version', '')}"
        return hashlib.md5(base_str.lower().encode()).hexdigest()[:10]

def main():
    try:
        processor = DataProcessor()
        success = processor.run_pipeline()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.critical(f"El script no pudo completarse debido a un error crítico: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

