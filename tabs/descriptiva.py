import streamlit as st
import pandas as pd
import altair as alt


COLOR_BARRAS = "#2a78d6"
TAMANO_MINIMO_SEGMENTO = 30

# Variables que en la etapa 2 mostraron posible fuga de información
VARIABLES_HISTORIAL = [
    "compras_12m", "gasto_total_12m",
    "dias_desde_ultima_compra", "monto_ultima_compra"
]


# ----------------------------------
# FUNCIONES DE APOYO
# ----------------------------------

def dividir(numerador, denominador):
    """Divide solo si el denominador es mayor que cero; si no, devuelve None."""
    if denominador is None or pd.isnull(denominador) or denominador == 0:
        return None
    return numerador / denominador


def formato_porcentaje(valor):
    return "No definido" if valor is None or pd.isnull(valor) else f"{valor:.1%}"


def formato_dinero(valor):
    return "No definido" if valor is None or pd.isnull(valor) else f"${valor:,.0f}"


def formato_numero(valor, decimales=1):
    return "No definido" if valor is None or pd.isnull(valor) else f"{valor:,.{decimales}f}"


def agregar_segmentos(df):
    """Crea columnas de agrupación solo para esta pestaña (no modifica df)."""
    df_seg = df.copy()

    df_seg["grupo_edad"] = pd.cut(
        df_seg["edad"],
        bins=[17, 34, 44, 54, 120],
        labels=["18-34", "35-44", "45-54", "55+"]
    ).astype(str)

    df_seg["nivel_ingreso"] = pd.qcut(
        df_seg["ingreso_mensual"],
        q=4,
        labels=["Q1 (bajo)", "Q2", "Q3", "Q4 (alto)"]
    ).astype(str)

    df_seg["trimestre_alta"] = (
        pd.to_datetime(df_seg["fecha_alta"]).dt.to_period("Q").astype(str)
    )

    return df_seg


def calcular_kpis(df):
    """Calcula los KPIs a partir de sumas, para usar el denominador correcto."""
    clientes = len(df)
    compradores_12m = (df["compras_12m"] > 0).sum()
    clientes_con_carrito = (df["carritos_30d"] > 0).sum()
    abandonos_con_carrito = (
        (df["carritos_30d"] > 0) & (df["abandono_carrito_30d"] == 1)
    ).sum()

    return {
        "Clientes": clientes,
        "Compradores en 12 meses": compradores_12m,
        "Tasa de compra en la última campaña":
            dividir(df["compro_ultima_campana"].sum(), clientes),
        "Ingreso por cliente":
            dividir(df["gasto_total_12m"].sum(), clientes),
        "Ticket promedio":
            dividir(df["gasto_total_12m"].sum(), df["compras_12m"].sum()),
        "Frecuencia de compra":
            dividir(df["compras_12m"].sum(), compradores_12m),
        "Recencia mediana (días)":
            df["dias_desde_ultima_compra"].median(),
        "Tasa de apertura":
            dividir(df["emails_abiertos_30d"].sum(), df["campanas_recibidas_30d"].sum()),
        "CTR de campañas":
            dividir(df["clics_campanas_30d"].sum(), df["campanas_recibidas_30d"].sum()),
        "Clics por apertura (CTOR)":
            dividir(df["clics_campanas_30d"].sum(), df["emails_abiertos_30d"].sum()),
        "Tasa de abandono de carrito":
            dividir(abandonos_con_carrito, clientes_con_carrito),
    }


def kpis_por_segmento(df, columna):
    """Tabla de KPIs para cada valor de la columna de segmentación."""
    filas = []

    for valor, grupo in df.groupby(columna, dropna=False):
        kpis = calcular_kpis(grupo)
        filas.append({
            "Segmento": str(valor),
            "Clientes": kpis["Clientes"],
            "% del total": len(grupo) / len(df),
            "Tasa de compra en la última campaña": kpis["Tasa de compra en la última campaña"],
            "Ingreso por cliente": kpis["Ingreso por cliente"],
            "Tasa de apertura": kpis["Tasa de apertura"],
            "CTR de campañas": kpis["CTR de campañas"],
            "Tasa de abandono de carrito": kpis["Tasa de abandono de carrito"],
        })

    return pd.DataFrame(filas)


# ----------------------------------
# PESTAÑA
# ----------------------------------

def mostrar(df):
    """Muestra KPIs de marketing a partir del dataset limpio (df_limpio)."""

    # ----------------------------------
    # ENCABEZADO
    # ----------------------------------

    st.header("3. Estadística descriptiva")

    st.markdown("""
    ### Pregunta de esta etapa

    **¿Cómo se comportan nuestros clientes y qué tan bien funcionan las campañas?**

    Aquí **describimos** lo que pasó. Una diferencia entre grupos no prueba
    que una variable *cause* la compra: solo indica dónde vale la pena investigar.
    """)

    kpis = calcular_kpis(df)


    # ----------------------------------
    # 1. KPIs GENERALES
    # ----------------------------------

    st.subheader("3.1 KPIs generales")

    st.write("**Clientes y ventas**")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Clientes", f"{kpis['Clientes']:,}")
    with col2:
        st.metric("Compradores en 12 meses", f"{kpis['Compradores en 12 meses']:,}")
    with col3:
        st.metric(
            "Tasa de compra en la última campaña",
            formato_porcentaje(kpis["Tasa de compra en la última campaña"])
        )
    with col4:
        st.metric("Ingreso por cliente", formato_dinero(kpis["Ingreso por cliente"]))

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Ticket promedio", formato_dinero(kpis["Ticket promedio"]))
    with col2:
        st.metric("Frecuencia de compra", formato_numero(kpis["Frecuencia de compra"], 2))
    with col3:
        st.metric("Recencia mediana (días)", formato_numero(kpis["Recencia mediana (días)"], 0))
    with col4:
        st.metric(
            "Tasa de abandono de carrito",
            formato_porcentaje(kpis["Tasa de abandono de carrito"])
        )

    st.write("**Campañas**")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Tasa de apertura", formato_porcentaje(kpis["Tasa de apertura"]))
    with col2:
        st.metric("CTR de campañas", formato_porcentaje(kpis["CTR de campañas"]))
    with col3:
        st.metric(
            "Clics por apertura (CTOR)",
            formato_porcentaje(kpis["Clics por apertura (CTOR)"])
        )

    with st.expander("¿Cómo se calcula cada KPI? (numerador / denominador)"):
        definiciones = pd.DataFrame([
            ["Tasa de compra en la última campaña",
             "Clientes con compro_ultima_campana = 1", "Total de clientes", ""],
            ["Ingreso por cliente",
             "Suma de gasto_total_12m", "Total de clientes",
             "Incluye clientes sin compras (aportan $0)"],
            ["Ticket promedio",
             "Suma de gasto_total_12m", "Suma de compras_12m",
             "Solo existe si hubo al menos una compra"],
            ["Frecuencia de compra",
             "Suma de compras_12m", "Clientes con compras_12m > 0", ""],
            ["Recencia mediana",
             "Mediana de dias_desde_ultima_compra", "Solo compradores",
             "Los clientes sin compras no tienen recencia (faltante estructural)"],
            ["Tasa de apertura",
             "Suma de emails_abiertos_30d", "Suma de campanas_recibidas_30d",
             "Supuesto: cada campaña recibida incluye un email. Validar con el negocio"],
            ["CTR de campañas",
             "Suma de clics_campanas_30d", "Suma de campanas_recibidas_30d", ""],
            ["Clics por apertura (CTOR)",
             "Suma de clics_campanas_30d", "Suma de emails_abiertos_30d",
             "Mide qué tan atractivo es el contenido una vez abierto"],
            ["Tasa de abandono de carrito",
             "Clientes con carrito que abandonaron", "Clientes con carritos_30d > 0",
             "Excluye a los clientes con alerta_carrito (abandono sin carrito)"],
        ], columns=["KPI", "Numerador", "Denominador", "Nota"])

        st.dataframe(definiciones, width="stretch", hide_index=True)
        st.caption(
            "Si un denominador es 0, el KPI se muestra como «No definido» "
            "en lugar de inventar un valor."
        )


    # ----------------------------------
    # 2. EMBUDO DIGITAL
    # ----------------------------------

    st.subheader("3.2 Embudo digital")

    embudo = pd.DataFrame({
        "Etapa": [
            "1. Clientes",
            "2. Visitaron la web (30 días)",
            "3. Vieron productos (30 días)",
            "4. Crearon un carrito (30 días)",
            "5. Compraron en la última campaña",
        ],
        "Clientes": [
            len(df),
            (df["visitas_web_30d"] > 0).sum(),
            (df["productos_vistos_30d"] > 0).sum(),
            (df["carritos_30d"] > 0).sum(),
            df["compro_ultima_campana"].sum(),
        ]
    })
    embudo["% del total"] = embudo["Clientes"] / len(df)

    grafica_embudo = (
        alt.Chart(embudo)
        .mark_bar(color=COLOR_BARRAS, cornerRadiusEnd=4)
        .encode(
            x=alt.X("Clientes:Q", title="Clientes"),
            y=alt.Y("Etapa:N", sort=None, title=None),
            tooltip=[
                alt.Tooltip("Etapa:N"),
                alt.Tooltip("Clientes:Q"),
                alt.Tooltip("% del total:Q", format=".1%"),
            ]
        )
    )

    st.altair_chart(grafica_embudo, width="stretch")

    st.caption(
        "Precaución: las etapas 2 a 4 miden los últimos 30 días y la etapa 5 "
        "mide la última campaña. No sabemos si cada compra pasó por un carrito, "
        "así que el embudo es una aproximación, no un recorrido observado."
    )


    # ----------------------------------
    # 3. KPIs POR SEGMENTO
    # ----------------------------------

    st.subheader("3.3 KPIs por segmento")

    df_seg = agregar_segmentos(df)

    opciones_segmento = {
        "Categoría preferida": "categoria_preferida",
        "Canal de origen": "canal_origen",
        "Ciudad": "ciudad",
        "Género": "genero",
        "Grupo de edad": "grupo_edad",
        "Nivel de ingreso (cuartiles)": "nivel_ingreso",
        "Trimestre de alta": "trimestre_alta",
    }

    col1, col2 = st.columns(2)

    with col1:
        etiqueta_segmento = st.selectbox(
            "Segmentar por:",
            list(opciones_segmento.keys()),
            key="segmento_descriptiva"
        )

    with col2:
        kpi_grafica = st.selectbox(
            "KPI para la gráfica:",
            [
                "Tasa de compra en la última campaña",
                "Ingreso por cliente",
                "Tasa de apertura",
                "CTR de campañas",
                "Tasa de abandono de carrito",
                "Clientes",
            ],
            key="kpi_descriptiva"
        )

    tabla_segmento = kpis_por_segmento(df_seg, opciones_segmento[etiqueta_segmento])

    es_dinero = kpi_grafica == "Ingreso por cliente"
    es_conteo = kpi_grafica == "Clientes"
    formato_eje = "$,.0f" if es_dinero else (",d" if es_conteo else ".0%")

    grafica_segmento = (
        alt.Chart(tabla_segmento.dropna(subset=[kpi_grafica]))
        .mark_bar(color=COLOR_BARRAS, cornerRadiusEnd=4)
        .encode(
            x=alt.X(f"{kpi_grafica}:Q", title=kpi_grafica,
                    axis=alt.Axis(format=formato_eje)),
            y=alt.Y("Segmento:N", sort="-x", title=etiqueta_segmento),
            tooltip=[
                alt.Tooltip("Segmento:N"),
                alt.Tooltip(f"{kpi_grafica}:Q", format=formato_eje),
                alt.Tooltip("Clientes:Q", title="Clientes en el segmento"),
            ]
        )
    )

    st.altair_chart(grafica_segmento, width="stretch")

    tabla_mostrar = tabla_segmento.copy()
    for columna in ["% del total", "Tasa de compra en la última campaña",
                    "Tasa de apertura", "CTR de campañas", "Tasa de abandono de carrito"]:
        tabla_mostrar[columna] = tabla_mostrar[columna].map(formato_porcentaje)
    tabla_mostrar["Ingreso por cliente"] = tabla_mostrar["Ingreso por cliente"].map(formato_dinero)

    st.dataframe(tabla_mostrar, width="stretch", hide_index=True)

    segmentos_pequenos = tabla_segmento[tabla_segmento["Clientes"] < TAMANO_MINIMO_SEGMENTO]
    if not segmentos_pequenos.empty:
        st.warning(
            f"Hay {len(segmentos_pequenos)} segmento(s) con menos de "
            f"{TAMANO_MINIMO_SEGMENTO} clientes: "
            + ", ".join(segmentos_pequenos["Segmento"])
            + ". Con pocos clientes, una tasa puede cambiar mucho por uno o dos "
            "casos; interpreta esas diferencias con cautela."
        )


    # ----------------------------------
    # 4. COMPRADORES VS. NO COMPRADORES
    # ----------------------------------

    st.subheader("3.4 ¿En qué se diferencian quienes compraron en la campaña?")

    variables_comparar = [
        "edad", "ingreso_mensual",
        "visitas_web_30d", "productos_vistos_30d", "carritos_30d",
        "abandono_carrito_30d", "campanas_recibidas_30d",
        "emails_abiertos_30d", "clics_campanas_30d",
    ]

    comparacion = (
        df.groupby("compro_ultima_campana")[variables_comparar]
        .mean()
        .T
        .rename(columns={0: "No compró (promedio)", 1: "Compró (promedio)"})
    )
    comparacion["Diferencia"] = (
        comparacion["Compró (promedio)"] - comparacion["No compró (promedio)"]
    )
    comparacion = comparacion.round(2)
    comparacion.index.name = "Variable"

    st.dataframe(comparacion, width="stretch")

    st.caption(
        "No se incluyen " + ", ".join(f"`{v}`" for v in VARIABLES_HISTORIAL)
        + ": en la etapa 2 vimos que coinciden con la compra de la campaña, "
        "así que compararlas aquí solo repetiría el resultado."
    )


    # ----------------------------------
    # 5. INTERPRETACIÓN
    # ----------------------------------

    st.subheader("3.5 Preguntas para interpretar")

    st.markdown("""
    1. ¿Qué segmento tiene la **mayor tasa de compra** y cuántos clientes lo forman?
       ¿Es suficiente para confiar en la diferencia?
    2. ¿Dónde se **pierden más clientes** en el embudo digital?
    3. ¿La tasa de apertura y el CTR son altos o bajos? ¿Contra qué los compararías?
    4. ¿Qué diferencias ves entre compradores y no compradores? ¿Podrían
       explicarse por otra variable (por ejemplo, el canal de origen)?
    5. Escribe **una** conclusión descriptiva y separa claramente lo que
       *observaste* de lo que *supones*.
    """)
