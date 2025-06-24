# app/ui_components.py
import streamlit as st

def initialize_session_state():
    """
    Define los valores por defecto para los inputs del usuario en el estado de la sesión.
    Esto se ejecuta solo una vez al inicio de la aplicación.
    """
    defaults = {
        'ingreso_neto': 5_000_000,
        'egresos_fijos': 2_000_000,
        'cuota_inicial': 30_000_000,
        'plazo_meses': 72,
        'tasa_personalizada_pct': 18.5,
        'km_anuales': 15_000
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def sidebar_input_widgets():
    """
    Crea los widgets en la barra lateral. Ahora usan `st.session_state` para
    mantener sus valores entre ejecuciones y cambios de página.
    """
    st.sidebar.header("✨ Tu Perfil Financiero")

    # El parámetro 'key' conecta el widget directamente al st.session_state.
    st.sidebar.number_input(
        "Ingreso Neto Mensual (COP)", min_value=1_000_000,
        step=200_000, help="Tu salario después de descuentos.",
        key='ingreso_neto'
    )
    
    st.sidebar.number_input(
        "Egresos Fijos Mensuales (COP)", min_value=0,
        step=100_000, help="Arriendo, servicios, deudas, etc.",
        key='egresos_fijos'
    )
    
    st.sidebar.number_input(
        "Cuota Inicial Disponible (COP)", min_value=0,
        step=1_000_000,
        key='cuota_inicial'
    )
    
    st.sidebar.slider(
        "Plazo del Crédito (meses)", min_value=12, max_value=84,
        help="El plazo estándar suele ser entre 60 y 72 meses.",
        key='plazo_meses'
    )
    
    st.sidebar.slider(
        "Tasa de Interés Anual (E.A.) que te ofrecieron",
        min_value=5.0, max_value=22.0,
        step=0.1, format="%.1f%%",
        help="Ingresa la tasa de interés Efectiva Anual que te ha ofrecido el banco.",
        key='tasa_personalizada_pct'
    )
    
    st.sidebar.header("🚗 Tu Uso del Vehículo")
    st.sidebar.slider(
        "Kilometraje Anual Estimado (km)", min_value=5_000, max_value=40_000,
        step=1_000,
        key='km_anuales'
    )
    # Ya no es necesario que esta función devuelva un diccionario.

def display_recommendation_card(container, vehicle):
    """Muestra una tarjeta de vehículo visualmente atractiva."""
    with container:
        with st.container(border=True):
            st.subheader(f"{vehicle['marca']} {vehicle['modelo']}")
            st.caption(f"Versión: {vehicle['version']}")
            
            col1, col2 = st.columns(2)
            col1.metric("Precio", f"${int(vehicle['precio']):,}")
            col2.metric("Cuota Crédito", f"${int(vehicle['cuota_financiacion']):,}")
            
            with st.expander("Ver Costos Adicionales (Mensual)"):
                st.metric("Costo Total Mensual Estimado (TCO)", f"${int(vehicle['tco_total_mensual']):,}")
                
                additional_costs = {
                    "Seguro": vehicle['seguro_mensual'],
                    "Impuestos": vehicle['impuestos_mensuales'],
                    "SOAT": vehicle['soat_mensual'],
                    "Mantenimiento": vehicle['mantenimiento_mensual'],
                    "Depreciación (Costo Oculto)": vehicle['depreciacion_mensual']
                }
                st.bar_chart(additional_costs)