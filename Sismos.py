import requests
import pandas as pd
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
from ipywidgets import interact, widgets
from datetime import datetime, timedelta
import ipywidgets as widgets
from IPython.display import display, HTML

# Configuración inicial
BASE_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
PERU_BOUNDS = {
    'min_latitude': -18.5,
    'max_latitude': 0.0,
    'min_longitude': -81.5,
    'max_longitude': -68.0
}

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
            print("No se encontraron terremotos con los criterios especificados.")
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
        print(f"Error al conectarse a la API: {e}")
        return None

def graficar_magnitudes_vs_tiempo(df):
    """Grafica magnitud de terremotos vs tiempo"""
    plt.figure(figsize=(12, 6))
    plt.scatter(df['fecha'], df['magnitud'], c=df['magnitud'], cmap='Reds', s=100, alpha=0.7)
    plt.colorbar(label='Magnitud')
    plt.xlabel('Fecha')
    plt.ylabel('Magnitud')
    plt.title('Terremotos en Perú: Magnitud vs Tiempo')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def graficar_mapa_calor(df):
    """Crea un mapa de calor de terremotos"""
    # Configuración del mapa con atribución
    mapa = folium.Map(
        location=[-9.19, -75.01], 
        zoom_start=5, 
        tiles='Stamen Terrain',
        attr='Map data © <a href="https://openstreetmap.org">OpenStreetMap</a> contributors'
    )
    
    # Añadir marcadores para los terremotos más fuertes (mag > 5.5)
    for idx, row in df[df['magnitud'] >= 5.5].iterrows():
        folium.CircleMarker(
            location=[row['latitud'], row['longitud']],
            radius=row['magnitud']*2,
            popup=f"Magnitud: {row['magnitud']}<br>Fecha: {row['fecha']}<br>Lugar: {row['lugar']}",
            color='red',
            fill=True,
            fill_color='red'
        ).add_to(mapa)
    
    # Añadir mapa de calor
    HeatMap(data=df[['latitud', 'longitud', 'magnitud']].values.tolist(), radius=15).add_to(mapa)
    
    # Mostrar el mapa en Colab
    display(mapa)

def graficar_distribucion_magnitudes(df):
    """Grafica histograma de distribución de magnitudes"""
    plt.figure(figsize=(10, 6))
    plt.hist(df['magnitud'], bins=15, color='salmon', edgecolor='black')
    plt.xlabel('Magnitud')
    plt.ylabel('Frecuencia')
    plt.title('Distribución de Magnitudes de Terremotos en Perú')
    plt.grid(True, alpha=0.3)
    plt.show()

def mostrar_tabla(df):
    """Muestra una tabla con los terremotos más fuertes"""
    df_mostrar = df.sort_values('magnitud', ascending=False).head(10)
    display(df_mostrar[['fecha', 'magnitud', 'lugar']].style.background_gradient(cmap='Reds'))

def interfaz_grafica():
    """Interfaz interactiva para el usuario"""
    # Widgets de entrada
    dias_widget = widgets.IntSlider(
        value=30,
        min=1,
        max=365,
        step=1,
        description='Días atrás:',
        continuous_update=False
    )
    
    magnitud_widget = widgets.FloatSlider(
        value=4.0,
        min=2.0,
        max=8.0,
        step=0.1,
        description='Magnitud mínima:',
        continuous_update=False
    )
    
    # Función de actualización
    def actualizar(dias_atras, magnitud_minima):
        print(f"Obteniendo datos para los últimos {dias_atras} días con magnitud ≥ {magnitud_minima}...")
        df = obtener_terremotos(dias_atras, magnitud_minima)
        
        if df is not None and not df.empty:
            print(f"\n📊 Se encontraron {len(df)} terremotos con los criterios especificados")
            
            # Mostrar el terremoto más fuerte
            max_mag = df.loc[df['magnitud'].idxmax()]
            print(f"\n🔥 Terremoto más fuerte: Magnitud {max_mag['magnitud']}")
            print(f"📅 Fecha: {max_mag['fecha']}")
            print(f"📍 Lugar: {max_mag['lugar']}")
            
            # Mostrar gráficos
            mostrar_tabla(df)
            graficar_magnitudes_vs_tiempo(df)
            graficar_distribucion_magnitudes(df)
            graficar_mapa_calor(df)
        else:
            print("No se encontraron datos con los criterios especificados.")
    
    # Interactividad
    interact(actualizar, dias_atras=dias_widget, magnitud_minima=magnitud_widget)

# Ejecutar la interfaz
print("""
🌎 Visualizador de Terremotos en Perú
------------------------------------
Usando datos de la API de USGS (https://earthquake.usgs.gov)
""")

# Instalar folium si es necesario en Colab
try:
    import folium
except ImportError:
    !pip install folium
    import folium

interfaz_grafica()
