import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap, MarkerCluster, Fullscreen
from datetime import datetime, timedelta
import json
from streamlit_folium import st_folium

# Configuración de la página para mejor responsive
st.set_page_config(
    page_title="Terremotos en Perú",
    layout="wide",
    initial_sidebar_state="auto"
)

# CSS personalizado para mejorar el responsive
st.markdown("""
<style>
    /* Ajustes generales para móviles */
    @media screen and (max-width: 768px) {
        .stSlider > div {
            width: 100% !important;
        }
        .stDataFrame {
            font-size: 12px !important;
        }
        .stMetric {
            padding: 5px !important;
        }
        .css-1v0mbdj {
            max-width: 100% !important;
        }
    }
    
    /* Mejorar visualización de tabs en móviles */
    .stTabs [role="tablist"] {
        flex-wrap: wrap;
    }
    
    /* Ajustar popups del mapa */
    .folium-popup {
        max-width: 250px !important;
    }
    
    /* Sidebar más compacta en móviles */
    @media screen and (max-width: 768px) {
        section[data-testid="stSidebar"] {
            width: 200px !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Título de la aplicación responsive
st.title("🌍 Monitoreo Sísmico del Perú")
st.markdown("""
<div style="background-color:#f0f2f6;padding:10px;border-radius:5px;margin-bottom:10px;font-size:14px">
Visualización de actividad sísmica | Datos de <a href="https://earthquake.usgs.gov" target="_blank">USGS</a><br>
<small>Desarrollado por <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a></small>
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

# Cargar GeoJSON de departamentos (simplificado para el ejemplo)
try:
    DEPARTAMENTOS_GEOJSON = json.load(open('departamentos.geojson'))
except:
    DEPARTAMENTOS_GEOJSON = {
        "type": "FeatureCollection",
        "features": []
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

def crear_mapa_responsive(df):
    """Crea un mapa interactivo responsive"""
    # Mapa base centrado en Perú
    mapa = folium.Map(
        location=[-9.19, -75.01],
        zoom_start=5,
        control_scale=True,
        tiles='cartodbpositron'
    )
    
    # Añadir controles de pantalla completa
    Fullscreen(
        position='topright',
        title='Pantalla completa',
        title_cancel='Salir de pantalla completa',
        force_separate_button=True
    ).add_to(mapa)
    
    # Capa de departamentos
    if DEPARTAMENTOS_GEOJSON['features']:
        folium.GeoJson(
            DEPARTAMENTOS_GEOJSON,
            name="Departamentos",
            style_function=lambda x: {
                'fillColor': '#ffff00',
                'color': '#000000',
                'weight': 1,
                'fillOpacity': 0.1
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=['NOMBDEP'],
                aliases=['Departamento:'],
                localize=True,
                style=("font-size: 12px;")
            )
        ).add_to(mapa)
    
    # Agrupar marcadores para mejor rendimiento en móviles
    marker_cluster = MarkerCluster(
        name="Terremotos",
        options={
            'maxClusterRadius': 40,
            'spiderfyOnMaxZoom': True,
            'showCoverageOnHover': False,
            'zoomToBoundsOnClick': True
        }
    ).add_to(mapa)
    
    # Añadir marcadores responsivos
    for idx, row in df.iterrows():
        color = 'red' if row['magnitud'] >= 6.0 else 'orange' if row['magnitud'] >= 5.0 else 'blue'
        icon_size = max(5, min(20, row['magnitud'] * 2))  # Tamaño responsivo
        
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=icon_size,
            popup=folium.Popup(
                f"""
                <div style="font-size:12px">
                    <b>Magnitud:</b> {row['magnitud']:.1f}<br>
                    <b>Fecha:</b> {row['fecha'].strftime('%d/%m/%Y %H:%M')}<br>
                    <b>Lugar:</b> {row['lugar']}
                </div>
                """,
                max_width=250
            ),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1
        ).add_to(marker_cluster)
    
    # Mapa de calor responsivo
    HeatMap(
        data=df[['latitud', 'longitud', 'magnitud']].values.tolist(),
        name="Mapa de Calor",
        radius=15,
        blur=10,
        min_opacity=0.5,
        gradient={0.2: 'blue', 0.5: 'lime', 0.8: 'red'}
    ).add_to(mapa)
    
    # Control de capas responsivo
    folium.LayerControl(
        position='bottomright',
        collapsed=True
    ).add_to(mapa)
    
    return mapa

def mostrar_graficos_responsive(df):
    """Muestra gráficos adaptados a móviles"""
    st.subheader("📊 Análisis de Datos")
    
    # Gráficos en tabs para mejor organización en móviles
    tab1, tab2, tab3 = st.tabs(["Magnitudes", "Profundidad", "Temporal"])
    
    with tab1:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.hist(df['magnitud'], bins=12, color='#ff7f0e', edgecolor='white')
        ax.set_xlabel('Magnitud', fontsize=10)
        ax.set_ylabel('Frecuencia', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
        st.pyplot(fig, use_container_width=True)
    
    with tab2:
        fig, ax = plt.subplots(figsize=(6, 3))
        ax.scatter(
            df['magnitud'],
            df.get('profundidad', 10),
            c=df['magnitud'],
            cmap='viridis',
            s=30,
            alpha=0.6
        )
        ax.set_xlabel('Magnitud', fontsize=10)
        ax.set_ylabel('Profundidad (km)', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
        st.pyplot(fig, use_container_width=True)
    
    with tab3:
        fig, ax = plt.subplots(figsize=(8, 3))
        ax.plot(df['fecha'], df['magnitud'], 'o', markersize=4, alpha=0.7)
        ax.set_xlabel('Fecha', fontsize=10)
        ax.set_ylabel('Magnitud', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
        plt.xticks(rotation=45)
        st.pyplot(fig, use_container_width=True)

# Sidebar responsiva
with st.sidebar:
    st.markdown("""
    <div style="text-align:center">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Mapa_del_Per%C3%BA_-_Departamentos.png/320px-Mapa_del_Per%C3%BA_-_Departamentos.png" 
             style="width:100%;max-width:200px;margin:0 auto">
    </div>
    """, unsafe_allow_html=True)
    
    st.header("⚙️ Configuración")
    
    dias_atras = st.slider(
        "Días a analizar",
        1, 365, 30,
        help="Seleccione el período de tiempo a revisar"
    )
    
    magnitud_minima = st.slider(
        "Magnitud mínima",
        2.0, 8.0, 4.0, 0.1,
        help="Filtre los terremotos por magnitud"
    )
    
    st.markdown("---")
    st.markdown("**📈 Datos Rápidos**")
    
    if 'df' in locals():
        cols = st.columns(2)
        cols[0].metric("Eventos", len(df))
        cols[1].metric("Máxima", f"{df['magnitud'].max():.1f}")
    
    st.markdown("---")
    st.markdown("""
    <div style="font-size:12px">
    <b>ℹ️ Información</b><br>
    Aplicación desarrollada por<br>
    <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a>
    </div>
    """, unsafe_allow_html=True)

# Obtener datos
df = obtener_terremotos(dias_atras, magnitud_minima)

if df is not None and not df.empty:
    # Mostrar métricas responsivas
    cols = st.columns(4)
    metrics = [
        ("Eventos", len(df)),
        ("Máxima", f"{df['magnitud'].max():.1f}"),
        ("Promedio", f"{df['magnitud'].mean():.1f}"),
        ("Último", df['fecha'].max().strftime('%d/%m'))
    ]
    
    for i, (title, value) in enumerate(metrics):
        cols[i].metric(title, value)
    
    # Contenido principal en tabs
    tab_mapa, tab_datos = st.tabs(["🗺 Mapa Interactivo", "📋 Datos Completos"])
    
    with tab_mapa:
        st.markdown("""
        <div style="font-size:12px;background-color:#f8f9fa;padding:8px;border-radius:5px;margin-bottom:10px">
        <b>🔍 Toque los marcadores para más detalles. Use dos dedos para hacer zoom.</b>
        </div>
        """, unsafe_allow_html=True)
        
        mapa = crear_mapa_responsive(df)
        st_folium(
            mapa,
            width=700 if st.session_state.get('IS_MOBILE', False) else 1000,
            height=400 if st.session_state.get('IS_MOBILE', False) else 600,
            returned_objects=[]
        )
    
    with tab_datos:
        mostrar_graficos_responsive(df)
        st.dataframe(
            df.sort_values('fecha', ascending=False),
            column_config={
                "fecha": "Fecha/Hora",
                "magnitud": st.column_config.NumberColumn(format="%.1f"),
                "lugar": "Ubicación"
            },
            hide_index=True,
            use_container_width=True
        )

# Pie de página responsivo
st.markdown("---")
st.markdown("""
<div style="font-size:12px;text-align:center">
Datos de <a href="https://earthquake.usgs.gov" target="_blank">USGS</a> | 
Actualizado: {date} | 
Desarrollado por <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a>
</div>
""".format(date=datetime.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)

# Detección de móvil (simplificada)
st.markdown("""
<script>
    function checkMobile() {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        if (isMobile) {
            window.parent.postMessage({type: 'setIsMobile', value: true}, '*');
        }
    }
    checkMobile();
    window.addEventListener('resize', checkMobile);
</script>
""", unsafe_allow_html=True)
