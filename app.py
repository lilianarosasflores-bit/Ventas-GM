import streamlit as st
import pandas as pd

from tabs.entender import mostrar as mostrar_entender
from tabs.limpiar import mostrar as mostrar_limpiar
from tabs.descriptiva import mostrar as mostrar_descriptiva
from tabs.predictiva import mostrar as mostrar_predictiva
from tabs.prescriptiva import mostrar as mostrar_prescriptiva
from tabs.decisiones import mostrar as mostrar_decisiones

# Configuración de la página
st.set_page_config(
    page_title="GM Ventas de Autos",
    page_icon="🚗",
    layout="wide",
)

st.title("🚗 Ventas de Vehículos GM ")

# Carga de datos
df = pd.read_csv(
    "data/dataset_clientes_autos_gm.csv"
)

# Crear una sola estructura de pestañas
(
    tab_entender,
    tab_limpiar,
    tab_descriptiva,
    tab_predictiva,
    tab_prescriptiva,
    tab_decisiones,
) = st.tabs([
    "1. Entender",
    "2. Limpiar",
    "3. Descriptiva",
    "4. Predictiva",
    "5. Prescriptiva",
    "6. Decisiones",
])

# 1. Entender los datos
with tab_entender:
    mostrar_entender(df)

# 2. Limpiar los datos (df se conserva; df_limpio es la copia trabajada)
with tab_limpiar:
    df_limpio = mostrar_limpiar(df)


# 3. Estadística descriptiva
with tab_descriptiva:
    mostrar_descriptiva(df_limpio)

# 4. Estadística predictiva
# df_predicho = df_limpio + probabilidad_compra y nivel_probabilidad
with tab_predictiva:
    df_predicho = mostrar_predictiva(df_limpio)

# 5. Estadística prescriptiva
# df_acciones = df_predicho + accion, prioridad, alerta_saturacion y motivo
with tab_prescriptiva:
    df_acciones = mostrar_prescriptiva(df_predicho)

# 6. Toma de decisiones
with tab_decisiones:
    mostrar_decisiones(df_acciones)
