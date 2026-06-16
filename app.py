# Aplicación Streamlit: sismos y zonas sísmicas de Costa Rica
# Proyecto final - TPB708 Programación en SIG
#
# La aplicación combina una tabla (pandas), un gráfico (Plotly) y un mapa
# interactivo (folium + streamlit-folium), siguiendo el patrón del ejemplo
# del profesor.

import re

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_folium import st_folium


# ----- Fuentes de datos -----

URL_SISMOS = "datos/SISMOS.gpkg"
URL_ZONAS = "datos/ZONAS.gpkg"


# ----- Columnas principales -----
COL_ZONA = "ZONA"
COL_MAGNITUD = "Magnitude"
COL_PROFUNDIDAD = "Depth"
COL_TIPO_FALLA = "tipo_falla1"


# ----- Colores por zona -----
# Color para los polígonos de cada zona
COLORES_ZONAS = {
    "1": "#66c2ff",  # celeste
    "2": "#98df8a",  # verde claro
    "3": "#ffbb78",  # naranja claro
    "4": "#c5b0d5",  # lila
    "5": "#ff9896",  # rosado
    "6": "#c49c94",  # café claro
    "7": "#9edae5",  # turquesa claro
    "8": "#c7c7c7",  # gris claro
}

# Color para los sismos de cada zona
COLORES_SISMOS = {
    "1": "#1f77b4",  # azul
    "2": "#2ca02c",  # verde
    "3": "#ff7f0e",  # naranja
    "4": "#9467bd",  # morado
    "5": "#d62728",  # rojo
    "6": "#8c564b",  # café
    "7": "#17becf",  # turquesa
    "8": "#7f7f7f",  # gris
}

# ----- Funciones para recuperar los datos -----
@st.cache_data
def cargar_sismos():
    """Carga la capa de sismos desde el GeoPackage."""
    sismos = gpd.read_file(URL_SISMOS)
    return sismos.to_crs(4326)

@st.cache_data
def cargar_zonas():
    """
    El archivo ZONAS.gpkg contiene una capa por zona. Por eso se leen todas
    las capas y se unen en un solo GeoDataFrame.
    """
    capas = gpd.list_layers(URL_ZONAS)["name"].tolist()
    zonas_lista = []

    for indice, nombre_capa in enumerate(capas, start=1):
        zona = gpd.read_file(URL_ZONAS, layer=nombre_capa)

        numero_zona = re.search(r"\d+", nombre_capa)
        zona[COL_ZONA] = numero_zona.group() if numero_zona else str(indice)

        zonas_lista.append(zona)

    zonas = pd.concat(zonas_lista, ignore_index=True)
    zonas = gpd.GeoDataFrame(zonas, geometry="geometry", crs=zonas_lista[0].crs)

    return zonas.to_crs(4326)

# El diccionario define los colores, pero estilo_zona() aplica esos colores a los polígonos.
def estilo_zona(feature):
    """Define el estilo de cada polígono según el número de zona."""
    zona = str(feature["properties"][COL_ZONA])
    color = COLORES_ZONAS.get(zona, "#3186cc")

    return {
        "color": color,
        "weight": 2,
        "fillColor": color,
        "fillOpacity": 0.20,
    }

# ----- Configuración de la página -----
st.set_page_config(
    page_title="Sismos de Costa Rica",
    layout="wide",
)

st.title(
    "Caracterización del estrés sísmico en Costa Rica mediante la inversión "
    "de mecanismos focales"
)

st.markdown(
    "Esta aplicación muestra un catálogo de sismos utilizado en el estudio en curso "
    "titulado **Caracterización del estrés tectónico de Costa Rica mediante la inversión "
    "de mecanismos focales**. En ella se pueden observar los sismos utilizados y las zonas "
    "sísmicas de trabajo asignadas. La información se presenta mediante una tabla, un "
    "gráfico estadístico y un mapa interactivo desarrollado con Folium."
)

# ----- Carga de los datos -----
sismos = cargar_sismos()
zonas = cargar_zonas()

# ----- Preparación de datos -----
sismos[COL_ZONA] = sismos[COL_ZONA].astype(str)
zonas[COL_ZONA] = zonas[COL_ZONA].astype(str)

sismos = sismos.dropna(subset=["geometry"])
zonas = zonas.dropna(subset=["geometry"])

# ----- Filtros -----
st.sidebar.header("Filtros")

zonas_disponibles = sorted(sismos[COL_ZONA].unique())

zona_seleccionada = st.sidebar.selectbox(
    "Zona sísmica",
    options=["Todas las zonas"] + zonas_disponibles,
)

if zona_seleccionada == "Todas las zonas":
    sismos_filtrados = sismos.copy()
    zonas_filtradas = zonas.copy()
else:
    sismos_filtrados = sismos[sismos[COL_ZONA] == zona_seleccionada].copy()
    zonas_filtradas = zonas[zonas[COL_ZONA] == zona_seleccionada].copy()


tipos_falla = sorted(sismos_filtrados[COL_TIPO_FALLA].dropna().unique())

tipo_falla_seleccionado = st.sidebar.selectbox(
    "Tipo de falla",
    options=["Todos los tipos"] + tipos_falla,
)

if tipo_falla_seleccionado != "Todos los tipos":
    sismos_filtrados = sismos_filtrados[
        sismos_filtrados[COL_TIPO_FALLA] == tipo_falla_seleccionado
    ].copy()


st.sidebar.metric("Sismos mostrados", len(sismos_filtrados))

# ----- Tabla -----
st.header("Tabla de catálogo de sismos")

st.markdown(
    "La siguiente tabla muestra los registros de sismos filtrados según la zona "
    "sísmica y el tipo de falla seleccionados. En ella se incluyen los datos del "
    "catálogo y los parámetros de los mecanismos focales utilizados para el análisis "
    "del estrés tectónico."
)

tabla_sismos = sismos_filtrados.drop(columns="geometry")

st.dataframe(
    tabla_sismos,
    use_container_width=True,
    hide_index=True,
)


# ----- Gráfico estadístico -----
st.header("Relación entre magnitud y profundidad de los sismos")

st.markdown(
    "El gráfico muestra la relación entre la magnitud y la profundidad de los eventos "
    "sísmicos filtrados. Cada punto representa un sismo. Al seleccionar una zona sísmica "
    "en la barra lateral, el gráfico se actualiza para mostrar únicamente los sismos "
    "correspondientes a esa zona."
)

datos_grafico = sismos_filtrados.copy()
datos_grafico[COL_MAGNITUD] = pd.to_numeric(datos_grafico[COL_MAGNITUD], errors="coerce")
datos_grafico[COL_PROFUNDIDAD] = pd.to_numeric(
    datos_grafico[COL_PROFUNDIDAD],
    errors="coerce",
)
datos_grafico = datos_grafico.dropna(subset=[COL_MAGNITUD, COL_PROFUNDIDAD])

if len(datos_grafico) > 0:
    grafico = px.scatter(
        datos_grafico,
        x=COL_MAGNITUD,
        y=COL_PROFUNDIDAD,
        color=COL_TIPO_FALLA,
        hover_data=[COL_ZONA, COL_MAGNITUD, COL_PROFUNDIDAD, COL_TIPO_FALLA],
        labels={
            COL_MAGNITUD: "Magnitud (Mw)",
            COL_PROFUNDIDAD: "Profundidad (km)",
            COL_TIPO_FALLA: "Tipo de falla",
            COL_ZONA: "Zona sísmica",
        },
        title="Magnitud vs profundidad de los sismos",
    )

    grafico.update_yaxes(autorange="reversed")
    grafico.update_layout(
        xaxis_title="Magnitud (Mw)",
        yaxis_title="Profundidad (km)",
        legend_title="Tipo de falla",
    )

    st.plotly_chart(
        grafico,
        use_container_width=True,
    )
else:
    st.warning(
        "No hay registros con valores válidos de magnitud y profundidad para "
        "los filtros seleccionados."
    )


# ----- Mapa interactivo -----
st.header("Mapa de sismos y zonas sísmicas")

st.markdown(
    "El mapa muestra las zonas sísmicas como polígonos y los sismos como círculos. "
    "Cada zona tiene un color propio y los sismos asociados se representan con un "
    "color similar más oscuro. Al hacer clic en un sismo, se muestra un tooltip con " \
    "información detallada "
)

mapa = folium.Map(
    location=[9.8, -84.0],
    zoom_start=7,
    tiles="CartoDB positron",
)

folium.GeoJson(
    data=zonas_filtradas,
    name="Zonas sísmicas",
    style_function=estilo_zona,
    tooltip=folium.GeoJsonTooltip(
        fields=[COL_ZONA],
        aliases=["Zona:"],
        localize=True,
    ),
).add_to(mapa)


capa_sismos = folium.FeatureGroup(name="Sismos")

for _, sismo in sismos_filtrados.iterrows():
    zona_sismo = str(sismo[COL_ZONA])
    color_sismo = COLORES_SISMOS.get(zona_sismo, "#cc3131")

    texto_tooltip = (
        f"Zona: {sismo[COL_ZONA]}<br>"
        f"Magnitud: {sismo[COL_MAGNITUD]}<br>"
        f"Profundidad: {sismo[COL_PROFUNDIDAD]}<br>"
        f"Tipo de falla: {sismo[COL_TIPO_FALLA]}"
    )

    folium.CircleMarker(
        location=[sismo.geometry.y, sismo.geometry.x],
        radius=5,
        color=color_sismo,
        fill=True,
        fill_color=color_sismo,
        fill_opacity=0.75,
        tooltip=texto_tooltip,
    ).add_to(capa_sismos)

capa_sismos.add_to(mapa)


leyenda_html = """
<div style="
    position: fixed;
    bottom: 40px;
    left: 40px;
    width: 180px;
    z-index: 9999;
    background-color: white;
    border: 2px solid grey;
    border-radius: 5px;
    padding: 10px;
    font-size: 13px;
">
<b>Zonas sísmicas</b><br>
<span style="color:#66c2ff;">■</span> Zona 1<br>
<span style="color:#98df8a;">■</span> Zona 2<br>
<span style="color:#ffbb78;">■</span> Zona 3<br>
<span style="color:#c5b0d5;">■</span> Zona 4<br>
<span style="color:#ff9896;">■</span> Zona 5<br>
<span style="color:#c49c94;">■</span> Zona 6<br>
<span style="color:#9edae5;">■</span> Zona 7<br>
<span style="color:#c7c7c7;">■</span> Zona 8<br>
</div>
"""

mapa.get_root().html.add_child(folium.Element(leyenda_html))
folium.LayerControl().add_to(mapa)

st_folium(
    mapa,
    use_container_width=True,
    height=600,
)