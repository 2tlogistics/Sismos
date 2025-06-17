import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
from datetime import datetime, timedelta
from streamlit_folium import st_folium

# Configuración inicial
st.set_page_config(page_title="Terremotos en Perú", layout="wide")
BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
PERU_BOUNDS = {
    'min_latitude': -18.5,
    'max_latitude': 0.0,
    'min_longitude': -81.5,
    'max_longitude': -68.0
}

# Título de la aplicación
st.title("🌍 Monitoreo de Terremotos en Perú")
st.markdown("Visualización de datos sísmicos obtenidos de la [API de USGS](https://earthquake.usgs.gov)")

@st.cache_data(ttl=3600)  # Cachear datos por 1 hora
def obtener_terremotos(dias_atras=30, magnitud_minima=4.0):
    """Obtiene datos de terremotos en Perú desde la API de USGS"""
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=dias_atras)
    
    parametros = {
        'format': 'geojson',
        'starttime': fecha_inicio.strftime('%Y-%m-%d'),
        'endtime': fecha_fin.strftime('%Y-%m-%d'),
        'minmagnitude': magnitud_minima,
        'minlatitude': PERU_BOUNDS['min_latitude'],
        'maxlatitude': PERU_BOUNDS['max_latitude'],
        'minlongitude': PERU_BOUNDS['min_longitude'],
        'maxlongitude': PERU_BOUNDS['max_longitude']
    }
    
    try:
        respuesta = requests.get(BASE_URL, params=parametros)
        respuesta.raise_for_status()
        datos = respuesta.json()
        
        if not datos['features']:
            st.warning("No se encontraron terremotos con los criterios especificados.")
            return None
        
        # Procesar los datos
        terremotos = []
        for evento in datos['features']:
            prop = evento['properties']
            geo = evento['geometry']
            terremotos.append({
                'fecha': pd.to_datetime(prop['time'], unit='ms'),
                'magnitud': prop['mag'],
                'profundidad': prop.get('depth', None),
                'lugar': prop['place'],
                'latitud': geo['coordinates'][1],
                'longitud': geo['coordinates'][0]
            })
        
        return pd.DataFrame(terremotos)
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectarse a la API: {e}")
        return None

def crear_mapa(df):
    """Crea un mapa interactivo con los terremotos"""
    mapa = folium.Map(
        location=[-9.19, -75.01], 
        zoom_start=5, 
        tiles='Stamen Terrain',
        attr='Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
    )
    
    # Añadir marcadores para los terremotos más fuertes
    for idx, row in df.iterrows():
        color = 'red' if row['magnitud'] >= 5.5 else 'orange'
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=row['magnitud']*1.5,
            popup=f"""
                <b>Magnitud:</b> {row['magnitud']}<br>
                <b>Fecha:</b> {row['fecha']}<br>
                <b>Lugar:</b> {row['lugar']}
            """,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7
        ).add_to(mapa)
    
    # Añadir mapa de calor
    HeatMap(data=df[['latitud', 'longitud', 'magnitud']].values.tolist(), radius=15).add_to(mapa)
    
    return mapa

# Sidebar con controles
with st.sidebar:
    st.header("⚙️ Configuración")
    dias_atras = st.slider("Días a revisar", 1, 365, 30)
    magnitud_minima = st.slider("Magnitud mínima", 2.0, 8.0, 4.0, 0.1)
    
    st.markdown("---")
    st.markdown("**Información:**")
    st.markdown("Esta aplicación muestra los terremotos registrados en Perú usando datos de la USGS.")
    st.markdown("Los círculos en el mapa representan terremotos, con tamaño proporcional a su magnitud.")

# Obtener datos
df = obtener_terremotos(dias_atras, magnitud_minima)

if df is not None and not df.empty:
    # Mostrar métricas principales
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de terremotos", len(df))
    max_mag = df['magnitud'].max()
    col2.metric("Magnitud máxima", f"{max_mag:.1f}")
    ultimo = df['fecha'].max().strftime('%Y-%m-%d %H:%M')
    col3.metric("Último terremoto", ultimo)
    
    st.markdown("---")
    
    # Mostrar mapa
    st.header("🌐 Mapa de Terremotos")
    mapa = crear_mapa(df)
    st_folium(mapa, width=1200, height=600)
    
    # Mostrar gráficos
    st.header("📊 Análisis de Datos")
    
    tab1, tab2, tab3 = st.tabs(["Magnitud vs Tiempo", "Distribución de Magnitudes", "Datos Completos"])
    
    with tab1:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.scatter(df['fecha'], df['magnitud'], c=df['magnitud'], cmap='Reds', s=50, alpha=0.7)
        plt.colorbar(ax.scatter(df['fecha'], df['magnitud'], c=df['magnitud'], cmap='Reds', s=50, alpha=0.7), label='Magnitud')
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Magnitud')
        ax.set_title('Terremotos en Perú: Magnitud vs Tiempo')
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    
    with tab2:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.hist(df['magnitud'], bins=15, color='salmon', edgecolor='black')
        ax.set_xlabel('Magnitud')
        ax.set_ylabel('Frecuencia')
        ax.set_title('Distribución de Magnitudes de Terremotos')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    
    with tab3:
        st.dataframe(df.sort_values('magnitud', ascending=False).style.background_gradient(
            subset=['magnitud'], cmap='Reds'
        ), height=600)
else:
    st.warning("No se encontraron datos con los criterios especificados.")
