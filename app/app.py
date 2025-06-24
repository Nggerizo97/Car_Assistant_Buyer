# app/app.py

import streamlit as st
import pandas as pd
from pathlib import Path
from src.analysis.financial_models import ModeloFinancieroVehicular 
from ui_components import sidebar_input_widgets, display_recommendation_card, initialize_session_state

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Asesor de Compra de Vehículos",
    page_icon="🚗",
    layout="wide"
)

# --- ESTADO DE LA SESIÓN ---
# Inicializa los valores por defecto en el estado de la sesión la primera vez que se ejecuta.
initialize_session_state()
if 'ran_calculation' not in st.session_state: st.session_state.ran_calculation = False
if 'recommendations' not in st.session_state: st.session_state.recommendations = pd.DataFrame()
if 'viability' not in st.session_state: st.session_state.viability = {}

# --- FUNCIÓN DE CARGA DE DATOS ---
@st.cache_data
def load_data():
    """Carga los datos limpios y los prepara para la app."""
    clean_csv_path = Path(__file__).parents[1] / 'data' / 'processed' / 'carros_limpios.csv'
    if clean_csv_path.exists():
        df = pd.read_csv(clean_csv_path)
        for col in ['precio']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    st.error(f"❌ No se encontró el archivo de datos en {clean_csv_path}.")
    return None

# --- SIDEBAR Y LÓGICA PRINCIPAL ---
# Esta función ahora lee y escribe directamente en st.session_state
sidebar_input_widgets() 

st.image("https://www.kia.com/co/content/dam/kwcms/co/es/images/our-vehicles/ev3/gallery/exterior/kia-ev3-galeria-exterior-01-d.png", use_container_width=True)
st.title("🚗 Asesor de Compra de Vehículos")
st.markdown("Bienvenido. Ingresa tus datos en la barra lateral y te mostraré un universo de vehículos nuevos a tu alcance.")

df_carros = load_data()

if st.sidebar.button("Calcular Opciones", type="primary", use_container_width=True):
    st.session_state.ran_calculation = True
    if df_carros is not None:
        # Construimos el diccionario de datos del usuario DESDE el estado de la sesión
        user_data = {
            'ingreso_neto': st.session_state.ingreso_neto,
            'egresos_fijos': st.session_state.egresos_fijos,
            'cuota_inicial': st.session_state.cuota_inicial,
            'plazo_meses': st.session_state.plazo_meses,
            'tasa_personalizada': st.session_state.tasa_personalizada_pct / 100.0,
            'km_anuales': st.session_state.km_anuales,
            'score_crediticio': 'medio'
        }
        with st.spinner("Analizando tu perfil y el catálogo completo de vehículos..."):
            modelo_financiero = ModeloFinancieroVehicular()
            st.session_state.viability = modelo_financiero.calcular_viabilidad(user_data)
            st.session_state.recommendations = modelo_financiero.generar_recomendaciones(user_data, df_carros)

# --- LÓGICA DE VISUALIZACIÓN INTELIGENTE ---
if st.session_state.ran_calculation:
    viability = st.session_state.viability
    recommendations = st.session_state.recommendations

    st.markdown("---")
    st.header("📊 Tu Resumen Financiero")
    col1, col2 = st.columns(2)
    col1.metric("Tu Cuota Mensual Máxima para el Crédito", f"COP ${viability.get('capacidad_pago_mensual', 0):,.0f}")
    col2.metric("Precio Máximo del Vehículo que Puedes Financiar", f"COP ${viability.get('precio_maximo_vehiculo', 0):,.0f}")

    if not recommendations.empty:
        st.success(f"¡Buenas noticias! Hemos encontrado {len(recommendations)} opciones de vehículos que se ajustan a tu presupuesto.")
        
        st.markdown("---")
        st.header("🏆 Principales Recomendaciones para Ti")

        top_recommendations = recommendations.head(6)
        for i in range(0, len(top_recommendations), 3):
            cols = st.columns(3)
            row_vehicles = top_recommendations.iloc[i:i+3]
            for j, vehicle in enumerate(row_vehicles.to_dict('records')):
                display_recommendation_card(cols[j], vehicle)
        
        st.markdown("---")
        st.header("📋 Catálogo Completo a tu Alcance")
        st.markdown("Aquí está la lista completa de opciones. Puedes hacer clic en los encabezados para reordenar.")
        
        cols_to_show = ['marca', 'modelo', 'version', 'precio', 'cuota_financiacion', 'total_costos_adicionales']
        df_display = recommendations[[col for col in cols_to_show if col in recommendations.columns]].copy()
        
        st.data_editor(
            df_display, use_container_width=True, hide_index=True,
            column_config={
                "precio": st.column_config.NumberColumn(format="COP $ %d"),
                "cuota_financiacion": st.column_config.NumberColumn(format="COP $ %d"),
                "total_costos_adicionales": st.column_config.NumberColumn(format="COP $ %d")
            }
        )
        st.info("Para un desglose detallado de los costos de cualquier vehículo, navega a la página de **Resultados Detallados**.", icon="➡️")

    else:
        st.warning("No encontramos vehículos cuyo crédito se ajuste a tu capacidad de pago actual.")
        if df_carros is not None and not df_carros.empty:
            modelo_financiero = ModeloFinancieroVehicular()
            carro_mas_barato = df_carros.loc[df_carros['precio'].idxmin()]
            
            # Reconstruimos los datos del usuario para el cálculo
            user_data_for_calc = {
                'ingreso_neto': st.session_state.ingreso_neto, 'egresos_fijos': st.session_state.egresos_fijos,
                'cuota_inicial': st.session_state.cuota_inicial, 'plazo_meses': st.session_state.plazo_meses,
                'tasa_personalizada': st.session_state.tasa_personalizada_pct / 100.0,
                'score_crediticio': 'medio'
            }
            cuota_necesaria = modelo_financiero._calcular_cuota(
                carro_mas_barato['precio'], user_data_for_calc['cuota_inicial'],
                user_data_for_calc['plazo_meses'], viability.get('tasa_interes_anual', 0.2)
            )
            capacidad_pago = viability.get('capacidad_pago_mensual', 0)
            
            st.metric(
                label=f"Cuota Mínima Requerida (para un {carro_mas_barato['marca']} {carro_mas_barato['modelo']})",
                value=f"COP ${cuota_necesaria:,.0f}",
                delta=f"Te faltan COP ${max(0, cuota_necesaria - capacidad_pago):,.0f}",
                delta_color="inverse"
            )
            st.info("💡 **Sugerencia:** Para ver opciones, intenta aumentar tu cuota inicial, extender el plazo del crédito o buscar una tasa de interés más baja.")
