import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap, MarkerCluster, Fullscreen, MiniMap
from datetime import datetime, timedelta
import json
from streamlit_folium import st_folium
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Configuración de la página
st.set_page_config(
    page_title="Monitoreo Sísmico Perú-Venezuela",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon="🌎"
)

# CSS personalizado mejorado
st.markdown("""
<style>
    /* Ajustes generales */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Mejorar visualización de tabs */
    .stTabs [role="tablist"] {
        flex-wrap: wrap;
    }
    
    .stTabs [role="tab"] {
        padding: 0.5rem 1rem;
        font-size: 0.9rem;
    }
    
    /* Ajustar popups del mapa */
    .folium-popup {
        max-width: 300px !important;
        font-size: 12px !important;
    }
    
    /* Sidebar más compacta */
    section[data-testid="stSidebar"] {
        width: 280px !important;
    }
    
    /* Gráficos responsive */
    .stPlotlyChart, .stDataFrame {
        width: 100% !important;
    }
    
    /* Tarjetas de métricas */
    .stMetric {
        border-left: 4px solid #4e79a7;
        padding-left: 0.5rem;
    }
    
    /* Ajustes para móviles */
    @media screen and (max-width: 768px) {
        .stMetric {
            padding: 5px !important;
            margin-bottom: 10px !important;
        }
        
        section[data-testid="stSidebar"] {
            width: 200px !important;
        }
        
        .stSlider > div {
            width: 100% !important;
        }
    }
    
    /* Estilo para el footer */
    .footer {
        font-size: 0.8rem;
        text-align: center;
        padding: 1rem;
        color: #666;
        border-top: 1px solid #eee;
        margin-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Título de la aplicación
st.title("🌎 Monitoreo Sísmico de Perú y Venezuela")
st.markdown("""
<div style="background-color:#f0f2f6;padding:15px;border-radius:5px;margin-bottom:15px;font-size:14px">
Visualización de actividad sísmica en Perú y Venezuela | Datos de <a href="https://earthquake.usgs.gov" target="_blank">USGS</a><br>
<small>Desarrollado por <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a></small>
</div>
""", unsafe_allow_html=True)

# Configuración inicial
BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"

# Coordenadas de los países
COUNTRY_BOUNDS = {
    'Perú': {
        'min_latitude': -18.5,
        'max_latitude': 0.0,
        'min_longitude': -81.5,
        'max_longitude': -68.0
    },
    'Venezuela': {
        'min_latitude': 0.6,
        'max_latitude': 12.5,
        'min_longitude': -74.0,
        'max_longitude': -59.0
    },
    'Ambos': {
        'min_latitude': -18.5,
        'max_latitude': 12.5,
        'min_longitude': -81.5,
        'max_longitude': -59.0
    }
}

# Cargar GeoJSON de regiones (simplificado para el ejemplo)
try:
    DEPARTAMENTOS_GEOJSON = json.load(open('departamentos.geojson'))
except:
    DEPARTAMENTOS_GEOJSON = {
        "type": "FeatureCollection",
        "features": []
    }

try:
    ESTADOS_VENEZUELA_GEOJSON = json.load(open('estados_venezuela.geojson'))
except:
    ESTADOS_VENEZUELA_GEOJSON = {
        "type": "FeatureCollection",
        "features": []
    }

@st.cache_data(ttl=3600)
def obtener_terremotos(dias_atras=30, magnitud_minima=4.0, pais='Perú'):
    """Obtiene datos de terremotos desde la API de USGS para el país seleccionado"""
    fecha_fin = datetime.now()
    fecha_inicio = fecha_fin - timedelta(days=dias_atras)
    
    bounds = COUNTRY_BOUNDS.get(pais, COUNTRY_BOUNDS['Perú'])
    
    parametros = {
        'format': 'geojson',
        'starttime': fecha_inicio.strftime('%Y-%m-%d'),
        'endtime': fecha_fin.strftime('%Y-%m-%d'),
        'minmagnitude': magnitud_minima,
        'minlatitude': bounds['min_latitude'],
        'maxlatitude': bounds['max_latitude'],
        'minlongitude': bounds['min_longitude'],
        'maxlongitude': bounds['max_longitude']
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
            
            # Determinar país basado en coordenadas
            lat, lon = geo['coordinates'][1], geo['coordinates'][0]
            country = 'Perú' if ((lat >= COUNTRY_BOUNDS['Perú']['min_latitude']) and 
                                (lat <= COUNTRY_BOUNDS['Perú']['max_latitude']) and 
                                (lon >= COUNTRY_BOUNDS['Perú']['min_longitude']) and 
                                (lon <= COUNTRY_BOUNDS['Perú']['max_longitude'])) else 'Venezuela'
            
            terremotos.append({
                'fecha': pd.to_datetime(prop['time'], unit='ms'),
                'magnitud': prop['mag'],
                'profundidad': geo['coordinates'][2] if len(geo['coordinates']) > 2 else None,
                'lugar': prop['place'],
                'latitud': lat,
                'longitud': lon,
                'pais': country,
                'tsunami': 1 if prop.get('tsunami', 0) == 1 else 0,
                'significancia': prop.get('sig', 0)
            })
        
        return pd.DataFrame(terremotos)
    
    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectarse a la API: {e}")
        return None

def crear_mapa_completo(df, pais_seleccionado):
    """Crea un mapa interactivo con todas las funcionalidades"""
    # Centro y zoom inicial basado en el país seleccionado
    if pais_seleccionado == 'Perú':
        center = [-9.19, -75.01]
        zoom = 5
    elif pais_seleccionado == 'Venezuela':
        center = [7.0, -66.0]
        zoom = 5
    else:
        center = [-5.0, -70.0]
        zoom = 4
    
    # Crear mapa base
    mapa = folium.Map(
        location=center,
        zoom_start=zoom,
        control_scale=True,
        tiles='cartodbpositron',
        min_zoom=4,
        max_bounds=True
    )
    
    # Añadir controles
    Fullscreen(
        position='topright',
        title='Pantalla completa',
        title_cancel='Salir de pantalla completa',
        force_separate_button=True
    ).add_to(mapa)
    
    # Añadir minimapa
    MiniMap(position="bottomleft").add_to(mapa)
    
    # Capa de regiones según el país
    if pais_seleccionado == 'Perú' and DEPARTAMENTOS_GEOJSON['features']:
        folium.GeoJson(
            DEPARTAMENTOS_GEOJSON,
            name="Departamentos del Perú",
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
    elif pais_seleccionado == 'Venezuela' and ESTADOS_VENEZUELA_GEOJSON['features']:
        folium.GeoJson(
            ESTADOS_VENEZUELA_GEOJSON,
            name="Estados de Venezuela",
            style_function=lambda x: {
                'fillColor': '#00ff00',
                'color': '#000000',
                'weight': 1,
                'fillOpacity': 0.1
            },
            tooltip=folium.features.GeoJsonTooltip(
                fields=['ESTADO'],
                aliases=['Estado:'],
                localize=True,
                style=("font-size: 12px;")
            )
        ).add_to(mapa)
    
    # Agrupar marcadores para mejor rendimiento
    marker_cluster = MarkerCluster(
        name="Terremotos",
        options={
            'maxClusterRadius': 40,
            'spiderfyOnMaxZoom': True,
            'showCoverageOnHover': False,
            'zoomToBoundsOnClick': True
        }
    ).add_to(mapa)
    
    # Añadir marcadores con popups detallados
    for idx, row in df.iterrows():
        # Determinar color y tamaño basado en magnitud
        if row['magnitud'] >= 6.0:
            color = '#d62728'  # Rojo para sismos fuertes
            icon_size = row['magnitud'] * 2.5
        elif row['magnitud'] >= 5.0:
            color = '#ff7f0e'  # Naranja para sismos moderados
            icon_size = row['magnitud'] * 2.0
        else:
            color = '#1f77b4'  # Azul para sismos leves
            icon_size = row['magnitud'] * 1.5
        
        # Limitar tamaño máximo
        icon_size = min(icon_size, 30)
        
        # Crear contenido del popup
        popup_content = f"""
        <div style="font-size:12px;width:250px">
            <b>Magnitud:</b> {row['magnitud']:.1f}<br>
            <b>Fecha:</b> {row['fecha'].strftime('%d/%m/%Y %H:%M')}<br>
            <b>Profundidad:</b> {row['profundidad']:.1f} km<br>
            <b>Lugar:</b> {row['lugar']}<br>
            <b>País:</b> {row['pais']}<br>
            <b>Significancia:</b> {row['significancia']}
        </div>
        """
        
        # Añadir marcador al cluster
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=icon_size,
            popup=folium.Popup(popup_content, max_width=300),
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.7,
            weight=1,
            tooltip=f"Magnitud: {row['magnitud']:.1f}"
        ).add_to(marker_cluster)
    
    # Mapa de calor
    HeatMap(
        data=df[['latitud', 'longitud', 'magnitud']].values.tolist(),
        name="Mapa de Calor",
        radius=15,
        blur=10,
        min_opacity=0.5,
        gradient={0.2: 'blue', 0.5: 'lime', 0.8: 'red'},
        max_zoom=10
    ).add_to(mapa)
    
    # Añadir control de capas
    folium.LayerControl(
        position='bottomright',
        collapsed=True
    ).add_to(mapa)
    
    return mapa

def crear_graficos_avanzados(df):
    """Crea gráficos interactivos con Plotly"""
    st.subheader("📊 Análisis Estadístico Avanzado")
    
    # Gráficos en tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Distribuciones", "Relaciones", "Temporal", "Comparación por País"])
    
    with tab1:
        # Histograma de magnitudes con distribución de países
        fig = px.histogram(
            df, 
            x='magnitud', 
            color='pais', 
            nbins=20,
            title='Distribución de Magnitudes por País',
            labels={'magnitud': 'Magnitud', 'count': 'Número de Sismos'},
            marginal='box',
            barmode='overlay',
            opacity=0.7
        )
        fig.update_layout(bargap=0.1)
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de profundidad
        fig2 = px.box(
            df, 
            y='profundidad', 
            color='pais', 
            title='Distribución de Profundidad por País',
            labels={'profundidad': 'Profundidad (km)'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab2:
        # Scatter plot de magnitud vs profundidad
        fig = px.scatter(
            df,
            x='magnitud',
            y='profundidad',
            color='pais',
            size='magnitud',
            hover_name='lugar',
            title='Relación entre Magnitud y Profundidad',
            labels={'magnitud': 'Magnitud', 'profundidad': 'Profundidad (km)'},
            trendline='lowess'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Gráfico de violín para magnitud por país
        fig2 = px.violin(
            df,
            y='magnitud',
            x='pais',
            color='pais',
            box=True,
            points='all',
            title='Distribución de Magnitudes por País'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        # Serie temporal de sismos
        df['fecha_dia'] = df['fecha'].dt.date
        daily_counts = df.groupby(['fecha_dia', 'pais']).size().reset_index(name='counts')
        
        fig = px.line(
            daily_counts,
            x='fecha_dia',
            y='counts',
            color='pais',
            title='Frecuencia Diaria de Sismos',
            labels={'fecha_dia': 'Fecha', 'counts': 'Número de Sismos'},
            markers=True
        )
        fig.update_xaxes(rangeslider_visible=True)
        st.plotly_chart(fig, use_container_width=True)
        
        # Heatmap temporal
        df['hora'] = df['fecha'].dt.hour
        hour_counts = df.groupby(['hora', 'pais']).size().reset_index(name='counts')
        
        fig2 = px.density_heatmap(
            df,
            x=df['fecha'].dt.hour,
            y=df['fecha'].dt.day,
            z='magnitud',
            facet_col='pais',
            title='Distribución de Sismos por Hora y Día',
            labels={'x': 'Hora del día', 'y': 'Día del mes', 'z': 'Magnitud'},
            nbinsx=24,
            nbinsy=31
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab4:
        # Comparación estadística entre países
        st.subheader("Estadísticas Comparativas")
        
        stats = df.groupby('pais').agg({
            'magnitud': ['mean', 'max', 'min', 'std'],
            'profundidad': ['mean', 'max', 'min', 'std'],
            'significancia': ['mean', 'max'],
            'tsunami': 'sum'
        }).reset_index()
        
        st.dataframe(
            stats.style.format({
                ('magnitud', 'mean'): '{:.2f}',
                ('magnitud', 'std'): '{:.2f}',
                ('profundidad', 'mean'): '{:.2f}',
                ('profundidad', 'std'): '{:.2f}',
                ('significancia', 'mean'): '{:.2f}'
            }),
            use_container_width=True
        )
        
        # Gráfico de radar para comparación
        fig = go.Figure()
        
        for pais in df['pais'].unique():
            df_pais = df[df['pais'] == pais]
            fig.add_trace(go.Scatterpolar(
                r=[
                    df_pais['magnitud'].mean(),
                    df_pais['profundidad'].mean(),
                    df_pais['significancia'].mean(),
                    df_pais['tsunami'].sum()
                ],
                theta=['Magnitud', 'Profundidad', 'Significancia', 'Tsunamis'],
                fill='toself',
                name=pais
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, max(df['magnitud'].max(), df['profundidad'].max()/10, df['significancia'].max()/100)]
                )),
            showlegend=True,
            title='Comparación de Estadísticas por País'
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Sidebar mejorada
with st.sidebar:
    st.markdown("""
    <div style="text-align:center">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Mapa_del_Per%C3%BA_-_Departamentos.png/320px-Mapa_del_Per%C3%BA_-_Departamentos.png" 
             style="width:100%;max-width:200px;margin:0 auto;border-radius:5px;margin-bottom:10px">
        <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/0/06/Venezuela_-_administrative_map.png/320px-Venezuela_-_administrative_map.png" 
             style="width:100%;max-width:200px;margin:0 auto;border-radius:5px">
    </div>
    """, unsafe_allow_html=True)
    
    st.header("⚙️ Configuración")
    
    # Selector de país
    pais_seleccionado = st.selectbox(
        "País a analizar",
        ['Perú', 'Venezuela', 'Ambos'],
        index=0,
        help="Seleccione el país o ambos para comparar"
    )
    
    # Rango de fechas
    dias_atras = st.slider(
        "Días a analizar",
        1, 365, 30,
        help="Seleccione el período de tiempo a revisar"
    )
    
    # Filtro de magnitud
    magnitud_minima = st.slider(
        "Magnitud mínima",
        2.0, 8.0, 4.0, 0.1,
        help="Filtre los terremotos por magnitud"
    )
    
    # Filtros adicionales
    st.markdown("**🔍 Filtros Adicionales**")
    
    profundidad_max = st.number_input(
        "Profundidad máxima (km)",
        min_value=0,
        max_value=700,
        value=300,
        step=10
    )
    
    mostrar_tsunamis = st.checkbox(
        "Mostrar solo sismos con alerta de tsunami",
        value=False
    )
    
    st.markdown("---")
    st.markdown("**📈 Datos Rápidos**")
    
    # Mostrar métricas rápidas (se actualizarán después de cargar los datos)
    if 'df' in locals():
        cols = st.columns(2)
        cols[0].metric("Total Eventos", len(df))
        cols[1].metric("Magnitud Máxima", f"{df['magnitud'].max():.1f}")
        
        cols = st.columns(2)
        cols[0].metric("Profundidad Promedio", f"{df['profundidad'].mean():.1f} km")
        cols[1].metric("Alertas Tsunami", f"{df['tsunami'].sum()}")
    
    st.markdown("---")
    st.markdown("""
    <div style="font-size:12px">
    <b>ℹ️ Información</b><br>
    Datos sísmicos proporcionados por el <a href="https://earthquake.usgs.gov" target="_blank">USGS</a>.<br>
    Actualizado automáticamente cada hora.<br><br>
    <b>Desarrollado por:</b><br>
    <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a>
    </div>
    """, unsafe_allow_html=True)

# Obtener datos
df = obtener_terremotos(dias_atras, magnitud_minima, pais_seleccionado)

if df is not None and not df.empty:
    # Aplicar filtros adicionales
    df = df[df['profundidad'] <= profundidad_max]
    
    if mostrar_tsunamis:
        df = df[df['tsunami'] == 1]
    
    # Mostrar métricas principales
    st.subheader("📌 Resumen Estadístico")
    
    cols = st.columns(4)
    metrics = [
        ("Total Eventos", len(df), "# eventos registrados"),
        ("Magnitud Máxima", f"{df['magnitud'].max():.1f}", "Mayor magnitud registrada"),
        ("Profundidad Promedio", f"{df['profundidad'].mean():.1f} km", "Profundidad media de los sismos"),
        ("Alertas Tsunami", f"{df['tsunami'].sum()}", "Eventos con potencial de tsunami")
    ]
    
    for i, (title, value, help_text) in enumerate(metrics):
        cols[i].metric(
            label=title,
            value=value,
            help=help_text
        )
    
    # Mostrar últimos 5 eventos
    st.markdown("**Últimos 5 eventos registrados**")
    st.dataframe(
        df[['fecha', 'magnitud', 'profundidad', 'lugar', 'pais']]
        .sort_values('fecha', ascending=False)
        .head(5)
        .style.format({
            'magnitud': '{:.1f}',
            'profundidad': '{:.1f} km'
        }),
        hide_index=True,
        use_container_width=True
    )
    
    # Contenido principal en tabs
    tab_mapa, tab_graficos, tab_datos = st.tabs(["🗺 Mapa Interactivo", "📊 Análisis Avanzado", "📋 Datos Completos"])
    
    with tab_mapa:
        st.markdown("""
        <div style="font-size:12px;background-color:#f8f9fa;padding:10px;border-radius:5px;margin-bottom:15px">
        <b>🔍 Interactividad:</b> Haz clic en los marcadores para ver detalles. Usa los controles en la esquina superior derecha para cambiar la vista.
        </div>
        """, unsafe_allow_html=True)
        
        mapa = crear_mapa_completo(df, pais_seleccionado)
        st_folium(
            mapa,
            width=1200,
            height=700,
            returned_objects=[]
        )
    
    with tab_graficos:
        crear_graficos_avanzados(df)
    
    with tab_datos:
        st.dataframe(
            df.sort_values('fecha', ascending=False),
            column_config={
                "fecha": st.column_config.DatetimeColumn("Fecha/Hora", format="DD/MM/YYYY HH:mm"),
                "magnitud": st.column_config.NumberColumn(format="%.1f"),
                "profundidad": st.column_config.NumberColumn(format="%.1f km"),
                "lugar": "Ubicación",
                "pais": "País",
                "tsunami": st.column_config.CheckboxColumn("Tsunami"),
                "significancia": "Significancia"
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Botón para descargar datos
        st.download_button(
            label="📥 Descargar datos como CSV",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name=f"sismos_{pais_seleccionado.lower()}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime='text/csv'
        )

# Pie de página mejorado
st.markdown("""
<div class="footer">
    <div style="margin-bottom:5px">
        <strong>Sistema de Monitoreo Sísmico</strong> | Datos proporcionados por <a href="https://earthquake.usgs.gov" target="_blank">USGS</a>
    </div>
    <div>
        Actualizado: {date} | Desarrollado por <a href="https://digitalinnovation.agency" target="_blank">Digital Innovation Agency</a> | v2.1.0
    </div>
</div>
""".format(date=datetime.now().strftime('%d/%m/%Y %H:%M')), unsafe_allow_html=True)
