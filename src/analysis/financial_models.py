import pandas as pd
import numpy_financial as npf
from typing import Dict, List, Any
from datetime import datetime

class ModeloFinancieroVehicular:
    def __init__(self, datos_colombia: Dict = None):
        """Inicializa con valores por defecto para Colombia"""
        self.config = {
            'tasas_por_score': { 'bajo': 0.22, 'medio': 0.18, 'alto': 0.15, 'preferencial': 0.1, 'exclusivo' : 0.05 },
            'seguro_anual_pct': 0.04,
            'impuesto_anual_pct': 0.015,
            'depreciacion_anual_pct': 0.10,
            'costo_mantenimiento_anual_pct': 0.01,
            'soat_anual': 550000,
            'garantia_anios': 5,
            'porcentaje_endeudamiento': 0.30
        }
        if datos_colombia: self.config.update(datos_colombia)
    
    # --- MÉTODO AÑADIDO ---
    def calcular_viabilidad(self, datos_usuario: Dict) -> Dict:
        """
        Calcula un resumen rápido de la viabilidad financiera del usuario.
        """
        try:
            capacidad_pago = self._calcular_capacidad_pago(
                datos_usuario['ingreso_neto'], datos_usuario['egresos_fijos']
            )
            
            tasa_interes = self._determinar_tasa_interes(
                datos_usuario.get('score_crediticio', 'medio'),
                datos_usuario.get('tasa_personalizada')
            )
            
            # Usamos la capacidad de pago para estimar el precio máximo
            precio_max = self._calcular_precio_maximo(
                capacidad_pago, datos_usuario['cuota_inicial'],
                tasa_interes, datos_usuario['plazo_meses']
            )
            
            return {
                'capacidad_pago_mensual': capacidad_pago,
                'tasa_interes_anual': tasa_interes,
                'precio_maximo_vehiculo': precio_max,
                'viable': precio_max > datos_usuario.get('cuota_inicial', 0)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def generar_recomendaciones(self, datos_usuario: Dict, catalogo_vehiculos: pd.DataFrame) -> pd.DataFrame:
        """
        Encuentra todos los vehículos cuyo CRÉDITO es asequible para el usuario
        y luego calcula los costos adicionales de propiedad para cada uno.
        """
        capacidad_pago = self._calcular_capacidad_pago(
            datos_usuario['ingreso_neto'], datos_usuario['egresos_fijos']
        )
        
        df = catalogo_vehiculos.copy()

        tasa_interes = self._determinar_tasa_interes(
            datos_usuario.get('score_crediticio', 'medio'),
            datos_usuario.get('tasa_personalizada')
        )
        df['cuota_financiacion'] = df.apply(
            lambda row: self._calcular_cuota(
                row['precio'], datos_usuario['cuota_inicial'],
                datos_usuario['plazo_meses'], tasa_interes
            ),
            axis=1
        )

        vehiculos_viables = df[df['cuota_financiacion'] <= capacidad_pago].copy()

        if vehiculos_viables.empty:
            return pd.DataFrame()

        costos_adicionales_df = vehiculos_viables.apply(
            lambda row: pd.Series(self._calcular_costos_adicionales_mensuales(row.to_dict())),
            axis=1
        )
        
        resultado_final = pd.concat([vehiculos_viables, costos_adicionales_df], axis=1)
        resultado_final['tco_total_mensual'] = resultado_final['cuota_financiacion'] + resultado_final['total_costos_adicionales']
        resultado_final.sort_values('precio', ascending=True, inplace=True)
        
        return resultado_final

    def _calcular_costos_adicionales_mensuales(self, vehiculo: Dict) -> Dict:
        precio_vehiculo = vehiculo.get('precio', 0)
        anio_modelo = vehiculo.get('anio_modelo', datetime.now().year)
        
        seguro_mensual = (precio_vehiculo * self.config['seguro_anual_pct']) / 12
        impuestos_mensuales = (precio_vehiculo * self.config['impuesto_anual_pct']) / 12
        soat_mensual = self.config['soat_anual'] / 12
        depreciacion_mensual = (precio_vehiculo * self.config['depreciacion_anual_pct']) / 12
        
        # El cálculo de mantenimiento con garantía ya es correcto
        if (datetime.now().year - int(anio_modelo)) < self.config['garantia_anios']:
            mantenimiento_mensual = 0
        else:
            mantenimiento_mensual = (precio_vehiculo * self.config['costo_mantenimiento_anual_pct']) / 12
        
        total_adicional = seguro_mensual + impuestos_mensuales + soat_mensual + depreciacion_mensual + mantenimiento_mensual
        
        return {
            'seguro_mensual': seguro_mensual,
            'impuestos_mensuales': impuestos_mensuales,
            'soat_mensual': soat_mensual,
            'mantenimiento_mensual': mantenimiento_mensual,
            'depreciacion_mensual': depreciacion_mensual,
            'total_costos_adicionales': total_adicional
        }

    def _calcular_capacidad_pago(self, ingreso_neto: float, egresos: float) -> float:
        capacidad = (ingreso_neto - egresos) * self.config['porcentaje_endeudamiento']
        return max(0, capacidad)

    def _determinar_tasa_interes(self, score: str, tasa_personalizada: float = None) -> float:
        if tasa_personalizada and 0 < tasa_personalizada < 1: return tasa_personalizada
        return self.config['tasas_por_score'].get(score.lower(), self.config['tasas_por_score']['medio'])

    def _calcular_cuota(self, precio: float, cuota_inicial: float, 
                         plazo_meses: int, tasa_anual_ea: float) -> float:
        valor_financiado = precio - cuota_inicial
        if valor_financiado <= 0: return 0
        tasa_mensual = (1 + tasa_anual_ea)**(1/12) - 1
        if tasa_mensual <= 0: return valor_financiado / plazo_meses if plazo_meses > 0 else 0
        return npf.pmt(rate=tasa_mensual, nper=plazo_meses, pv=-valor_financiado)
    
    def _calcular_precio_maximo(self, capacidad_pago: float, cuota_inicial: float, 
                                 tasa_anual_ea: float, plazo_meses: int) -> float:
        if plazo_meses <= 0: return cuota_inicial
        tasa_mensual = (1 + tasa_anual_ea)**(1/12) - 1
        if tasa_mensual <= 0:
            valor_financiable = capacidad_pago * plazo_meses
        else:
            valor_financiable = npf.pv(rate=tasa_mensual, nper=plazo_meses, pmt=-capacidad_pago)
        return cuota_inicial + valor_financiable
