# app/pages/2_Resultados_Detallados.py
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Resultados Detallados", page_icon="📊", layout="wide")
st.title("📊 Desglose de Costos por Vehículo")

if 'recommendations' not in st.session_state or st.session_state.recommendations.empty:
    st.warning("Aún no has calculado tus opciones. Ve a la página principal para empezar.")
    st.page_link("app.py", label="Ir a la página principal", icon="🏠")
else:
    df = st.session_state.recommendations
    
    st.info("Selecciona un vehículo de la lista para ver un análisis detallado de sus costos de propiedad mensuales.")
    
    # Crear una columna 'display_name' para que el usuario pueda seleccionar el carro
    df['display_name'] = df['marca'] + " " + df['modelo'] + " " + df['version']
    
    selected_vehicle_name = st.selectbox(
        "Selecciona un vehículo para analizar:",
        options=df['display_name']
    )
    
    selected_vehicle_data = df[df['display_name'] == selected_vehicle_name].iloc[0]

    st.subheader(f"Análisis para: {selected_vehicle_name}")
    
    # Mostrar métricas clave para el vehículo seleccionado
    col1, col2 = st.columns(2)
    col1.metric("Cuota Mensual del Crédito", f"${selected_vehicle_data['cuota_financiacion']:,.0f}")
    col2.metric("Costos Adicionales Mensuales", f"${selected_vehicle_data['total_costos_adicionales']:,.0f}")
    
    st.subheader("Desglose de Costos Adicionales de Propiedad (Estimados Mensuales)")
    
    st.info(
        "**¿Cómo leer este gráfico?** Estos son los gastos estimados que tendrías cada mes, "
        "además de la cuota de tu crédito. La 'Depreciación' no es un gasto que pagas, "
        "sino la pérdida de valor que sufre el carro."
    )

    additional_costs = {
        "Seguro Todo Riesgo": selected_vehicle_data['seguro_mensual'],
        "Impuesto Vehicular": selected_vehicle_data['impuestos_mensuales'],
        "SOAT": selected_vehicle_data['soat_mensual'],
        "Mantenimiento": selected_vehicle_data['mantenimiento_mensual'],
        "Depreciación (Costo Oculto)": selected_vehicle_data['depreciacion_mensual']
    }
    
    st.bar_chart(additional_costs)
