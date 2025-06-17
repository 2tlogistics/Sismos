import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap, MarkerCluster
from datetime import datetime, timedelta
import json
from streamlit_folium import st_folium

# Configuración de la página
st.set_page_config(page_title="Terremotos en Perú", layout="wide")

# Título de la aplicación
st.title("🌍 Monitoreo Sísmico del Perú")
st.markdown("""
<div style="background-color:#f0f2f6;padding:10px;border-radius:5px;margin-bottom:20px">
Visualización en tiempo real de actividad sísmica en territorio peruano<br>
Datos proporcionados por el <a href="https://earthquake.usgs.gov" target="_blank">Servicio Geológico de EE.UU. (USGS)</a><br>
Desarrollado por <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a>
</div>
""", unsafe_allow_html=True)

# Configuración inicial
BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
PERU_BOUNDS = {
    'min_latitude': -18.5,
    'max_latitude': 0.0,
    'min_longitude': -81.5,
    'max_longitude': -68.0
}

# GeoJSON simplificado de departamentos del Perú
DEPARTAMENTOS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"NOMBDEP": "Lima"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[-77.2, -12.0], [-76.0, -12.0], [-76.0, -11.0], [-77.2, -11.0], [-77.2, -12.0]]]
            }
        }
        # Agregar más departamentos aquí o cargar desde un archivo GeoJSON
    ]
}

@st.cache_data(ttl=3600)
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

def crear_mapa_detallado(df):
    """Crea un mapa interactivo con límites departamentales"""
    mapa = folium.Map(
        location=[-9.19, -75.01],
        zoom_start=5,
        control_scale=True
    )
    
    # Capas base
    folium.TileLayer(
        'openstreetmap',
        name='Mapa de Calles',
        attr='OpenStreetMap contributors'
    ).add_to(mapa)
    
    folium.TileLayer(
        'cartodbpositron',
        name='Mapa Ligero',
        attr='CartoDB'
    ).add_to(mapa)
    
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        name='Imagen Satelital',
        attr='Esri World Imagery'
    ).add_to(mapa)
    
    # Límites departamentales
    try:
        folium.GeoJson(
            DEPARTAMENTOS_GEOJSON,
            name="Departamentos",
            style_function=lambda x: {
                'fillColor': '#ffff00',
                'color': '#000000',
                'weight': 1.5,
                'fillOpacity': 0.1
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=['NOMBDEP'],
                aliases=['Departamento:'],
                localize=True,
                style=("font-weight: bold;")
            )
        ).add_to(mapa)
    except Exception as e:
        st.warning(f"No se pudieron cargar los límites departamentales: {str(e)}")
    
    # Marcadores de terremotos
    marker_cluster = MarkerCluster(
        name="Terremotos",
        overlay=True,
        control=True
    ).add_to(mapa)
    
    for idx, row in df.iterrows():
        color = 'red' if row['magnitud'] >= 6.0 else 'orange' if row['magnitud'] >= 5.0 else 'lightblue'
        icono = 'flash' if row['magnitud'] >= 6.0 else 'alert' if row['magnitud'] >= 5.0 else 'info-sign'
        
        popup_content = f"""
        <div style="width:250px;font-family:Arial">
            <h4 style="color:{color};margin-bottom:5px">Terremoto {row['magnitud']:.1f} M</h4>
            <p><b>Fecha:</b> {row['fecha'].strftime('%Y-%m-%d %H:%M')}</p>
            <p><b>Ubicación:</b> {row['lugar']}</p>
            <p><b>Coordenadas:</b> {row['latitud']:.3f}, {row['longitud']:.3f}</p>
        </div>
        """
        
        folium.Marker(
            location=[row['latitud'], row['longitud']],
            popup=folium.Popup(popup_content, max_width=300),
            icon=folium.Icon(
                color=color,
                icon=icono,
                prefix='glyphicon'
            ),
            tooltip=f"Terremoto {row['magnitud']:.1f} M"
        ).add_to(marker_cluster)
    
    # Mapa de calor
    HeatMap(
        data=df[['latitud', 'longitud', 'magnitud']].values.tolist(),
        name="Mapa de Calor",
        radius=20,
        blur=15,
        gradient={0.2: 'blue', 0.4: 'lime', 0.6: 'yellow', 1: 'red'}
    ).add_to(mapa)
    
    # Controles
    folium.LayerControl(
        position='topright',
        collapsed=False
    ).add_to(mapa)
    
    folium.plugins.MiniMap().add_to(mapa)
    
    return mapa

def mostrar_graficos(df):
    """Muestra gráficos analíticos"""
    st.subheader("📈 Análisis de Datos Sísmicos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Distribución de Magnitudes**")
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.hist(df['magnitud'], bins=15, color='#ff7f0e', edgecolor='black')
        ax.set_xlabel('Magnitud')
        ax.set_ylabel('Frecuencia')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    
    with col2:
        st.markdown("**Magnitud vs. Profundidad**")
        fig, ax = plt.subplots(figsize=(8, 4))
        scatter = ax.scatter(
            df['magnitud'],
            df.get('profundidad', 10),
            c=df['magnitud'],
            cmap='viridis',
            alpha=0.6
        )
        plt.colorbar(scatter, label='Magnitud')
        ax.set_xlabel('Magnitud')
        ax.set_ylabel('Profundidad (km)')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)
    
    st.markdown("**Evolución Temporal**")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df['fecha'], df['magnitud'], 'o-', markersize=5, alpha=0.7)
    ax.set_xlabel('Fecha')
    ax.set_ylabel('Magnitud')
    ax.grid(True)
    plt.xticks(rotation=45)
    st.pyplot(fig)

# Sidebar con controles
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Mapa_del_Per%C3%BA_-_Departamentos.png/320px-Mapa_del_Per%C3%BA_-_Departamentos.png", 
             use_container_width=True)  # Corregido: use_container_width en lugar de use_column_width
    
    st.header("⚙️ Configuración")
    
    dias_atras = st.slider(
        "Período de análisis (días)",
        1, 365, 30
    )
    
    magnitud_minima = st.slider(
        "Magnitud mínima",
        2.0, 8.0, 4.0, 0.1
    )
    
    st.markdown("---")
    st.markdown("**📊 Estadísticas Rápidas**")
    if 'df' in locals():
        st.metric("Terremotos registrados", len(df))
        st.metric("Magnitud máxima", f"{df['magnitud'].max():.1f}")
    
    st.markdown("---")
    st.markdown("""
    **ℹ️ Información**  
    Desarrollado por [Digital Innovation Agency](https://digitalinnovation.agency)  
    Datos del Servicio Geológico de EE.UU.
    """)

# Obtener datos
df = obtener_terremotos(dias_atras, magnitud_minima)

if df is not None and not df.empty:
    # Mostrar métricas
    st.subheader("🔍 Resumen de Actividad Sísmica")
    
    cols = st.columns(4)
    cols[0].metric("Total de eventos", len(df))
    cols[1].metric("Magnitud máxima", f"{df['magnitud'].max():.1f}")
    cols[2].metric("Magnitud promedio", f"{df['magnitud'].mean():.1f}")
    cols[3].metric("Último evento", df['fecha'].max().strftime('%d/%m/%Y %H:%M'))
    
    # Pestañas
    tab1, tab2 = st.tabs(["🗺️ Mapa Interactivo", "📊 Análisis"])
    
    with tab1:
        st.markdown("""
        <div style="background-color:#f8f9fa;padding:10px;border-radius:5px;margin-bottom:20px">
        <b>Instrucciones:</b> Use los controles en la esquina superior derecha para cambiar la visualización.
        </div>
        """, unsafe_allow_html=True)
        
        mapa = crear_mapa_detallado(df)
        st_folium(mapa, width=1200, height=700, returned_objects=[])
    
    with tab2:
        mostrar_graficos(df)
        st.subheader("📋 Datos Completos")
        st.dataframe(
            df.sort_values('fecha', ascending=False),
            use_container_width=True  # Corregido: use_container_width en lugar de use_column_width
        )

# Pie de página
st.markdown("---")
st.caption(f"""
Datos proporcionados por el Servicio Geológico de los Estados Unidos (USGS).  
Desarrollado por [Digital Innovation Agency](https://digitalinnovation.agency) - Actualizado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
""")
