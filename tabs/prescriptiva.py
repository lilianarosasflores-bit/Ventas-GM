import streamlit as st
import pandas as pd
import altair as alt


COLOR_BARRAS = "#2a78d6"

# Saturación: recibió varias campañas y no abrió ningún email
MINIMO_CAMPANAS_SATURACION = 4

# Reglas en orden: a cada cliente se le aplica la PRIMERA que cumple
REGLAS = [
    {
        "Orden": 1,
        "Acción": "Seguimiento postventa",
        "¿A quién?": "Clientes que compraron en la última campaña",
        "¿Qué hacer?": "Agradecer la compra y dar seguimiento a la entrega. "
                       "No enviarle ofertas de otro vehículo.",
        "¿Por qué?": "Acaba de comprar; insistir con otra venta puede molestar "
                     "y desperdicia presupuesto.",
    },
    {
        "Orden": 2,
        "Acción": "Verificar datos",
        "¿A quién?": "Clientes con abandono de carrito pero sin carrito registrado",
        "¿Qué hacer?": "Revisar el registro con el equipo de datos antes de "
                       "contactarlos.",
        "¿Por qué?": "Sus datos se contradicen (lo vimos en la etapa 2); "
                     "un mensaje equivocado daña la relación.",
    },
    {
        "Orden": 3,
        "Acción": "Recuperar carrito",
        "¿A quién?": "Clientes que agregaron un vehículo al carrito y no compraron",
        "¿Qué hacer?": "Recordatorio del vehículo que dejó en el carrito y "
                       "contacto de un asesor para resolver dudas.",
        "¿Por qué?": "Ya mostró una intención clara: eligió un vehículo "
                     "pero algo lo detuvo.",
    },
    {
        "Orden": 4,
        "Acción": "Reactivar interés",
        "¿A quién?": "Clientes que no compraron y no tienen carrito",
        "¿Qué hacer?": "Mensajes de bajo costo con información de su vehículo "
                       "de interés, sin presionar.",
        "¿Por qué?": "Su interés reciente es bajo; conviene mantener el "
                     "contacto sin gastar en atención personal.",
    },
]

ORDEN_ACCIONES = [regla["Acción"] for regla in REGLAS]

PRIORIDAD_POR_NIVEL = {
    "Alta": "1 · Contactar primero",
    "Media": "2 · Contactar después",
    "Baja": "3 · Contactar al final",
}

ORDEN_PRIORIDAD = list(PRIORIDAD_POR_NIVEL.values())


# ----------------------------------
# FUNCIONES DE APOYO
# ----------------------------------

def asignar_accion(cliente):
    """Devuelve la acción de la primera regla que cumple el cliente."""
    if cliente["compro_ultima_campana"] == 1:
        return "Seguimiento postventa"
    if cliente["abandono_carrito_30d"] == 1 and cliente["carritos_30d"] == 0:
        return "Verificar datos"
    if cliente["abandono_carrito_30d"] == 1:
        return "Recuperar carrito"
    return "Reactivar interés"


def explicar_cliente(cliente):
    """Arma en una línea la evidencia que respalda la recomendación."""
    partes = []

    if cliente["compro_ultima_campana"] == 1:
        partes.append("Compró en la última campaña")
    elif cliente["abandono_carrito_30d"] == 1 and cliente["carritos_30d"] == 0:
        partes.append("Abandono de carrito sin carrito registrado")
    elif cliente["abandono_carrito_30d"] == 1:
        partes.append("Dejó un vehículo en el carrito")
    else:
        partes.append("Sin carrito en 30 días")

    partes.append(f"{cliente['visitas_web_30d']} visitas a la web")
    partes.append(f"vio {cliente['productos_vistos_30d']} vehículos")
    partes.append(f"probabilidad {cliente['probabilidad_compra']:.0%}")

    return " · ".join(partes)


def aplicar_reglas(df):
    """Agrega acción, prioridad, alerta de saturación y motivo a cada cliente."""
    df_acciones = df.copy()

    df_acciones["accion"] = df_acciones.apply(asignar_accion, axis=1)

    # La prioridad solo tiene sentido para quienes no han comprado
    df_acciones["prioridad"] = df_acciones["nivel_probabilidad"].map(PRIORIDAD_POR_NIVEL)
    df_acciones.loc[df_acciones["accion"].isin(["Seguimiento postventa", "Verificar datos"]),
                    "prioridad"] = "No aplica"

    df_acciones["alerta_saturacion"] = (
        (df_acciones["campanas_recibidas_30d"] >= MINIMO_CAMPANAS_SATURACION)
        & (df_acciones["emails_abiertos_30d"] == 0)
    )

    df_acciones["motivo"] = df_acciones.apply(explicar_cliente, axis=1)

    return df_acciones


# ----------------------------------
# PESTAÑA
# ----------------------------------

def mostrar(df):
    """Convierte comportamiento y probabilidad de compra en acciones de marketing.
    Recibe df_predicho (etapa 4) y devuelve df con accion, prioridad,
    alerta_saturacion y motivo."""

    # ----------------------------------
    # ENCABEZADO
    # ----------------------------------

    st.header("5. Estadística prescriptiva")

    st.markdown("""
    ### Pregunta de esta etapa

    **¿Qué acción de marketing conviene para cada tipo de cliente?**

    Combinamos dos cosas:
    - **Lo que el cliente hizo** (compró, dejó un vehículo en el carrito, navegó poco) → decide **qué acción** le toca.
    - **Su probabilidad de compra** (etapa 4) → decide **a quién contactar primero** dentro de cada acción.
    """)

    st.info(
        "Las reglas son **simples y visibles** a propósito: cualquier persona del "
        "equipo puede revisarlas, discutirlas y cambiarlas. Una recomendación "
        "no garantiza una venta."
    )


    # ----------------------------------
    # 1. LAS REGLAS
    # ----------------------------------

    st.subheader("5.1 Las reglas que usamos")

    st.write(
        "Se revisan **en orden**: a cada cliente se le asigna la **primera** regla "
        "que cumple. Así nadie recibe dos acciones distintas."
    )

    st.dataframe(pd.DataFrame(REGLAS), width="stretch", hide_index=True)

    with st.expander("¿Por qué no hay venta cruzada ni descuentos?"):
        st.markdown("""
        - **Venta cruzada:** el dataset solo tiene dos tipos de vehículo (pickup y SUV
          eléctrica) y no incluye accesorios ni servicios. No tenemos con qué
          respaldar una oferta así.
        - **Descuentos o cupones:** todos los clientes tienen 0 en uso de cupón y
          descuento promedio. No sabemos cómo reaccionan a un descuento, así que
          no lo recomendamos.

        Regla de oro: **solo recomendamos lo que los datos pueden respaldar.**
        """)

    df_acciones = aplicar_reglas(df)


    # ----------------------------------
    # 2. RESULTADO
    # ----------------------------------

    st.subheader("5.2 ¿Cuántos clientes hay en cada acción?")

    resumen = pd.DataFrame({
        "Acción": ORDEN_ACCIONES,
        "Clientes": [(df_acciones["accion"] == a).sum() for a in ORDEN_ACCIONES],
        "Probabilidad promedio": [
            df_acciones.loc[df_acciones["accion"] == a, "probabilidad_compra"].mean()
            for a in ORDEN_ACCIONES
        ],
    })
    resumen["% de clientes"] = resumen["Clientes"] / len(df_acciones)

    columnas_tarjetas = st.columns(len(ORDEN_ACCIONES))

    for columna, (_, fila) in zip(columnas_tarjetas, resumen.iterrows()):
        with columna:
            st.metric(fila["Acción"], f"{fila['Clientes']} clientes")
            st.caption(f"{fila['% de clientes']:.0%} del total")

    grafica_acciones = (
        alt.Chart(resumen)
        .mark_bar(color=COLOR_BARRAS, cornerRadiusEnd=4)
        .encode(
            x=alt.X("Clientes:Q", title="Clientes"),
            y=alt.Y("Acción:N", sort=ORDEN_ACCIONES, title=None),
            tooltip=[
                alt.Tooltip("Acción:N"),
                alt.Tooltip("Clientes:Q"),
                alt.Tooltip("% de clientes:Q", format=".0%"),
            ]
        )
    )

    st.altair_chart(grafica_acciones, width="stretch")

    # Prioridad dentro de las acciones que buscan una venta
    st.write("**¿A quién contactar primero?** (solo acciones que buscan una venta)")

    acciones_venta = ["Recuperar carrito", "Reactivar interés"]

    tabla_prioridad = pd.crosstab(
        df_acciones.loc[df_acciones["accion"].isin(acciones_venta), "accion"],
        df_acciones.loc[df_acciones["accion"].isin(acciones_venta), "prioridad"]
    ).reindex(columns=ORDEN_PRIORIDAD, fill_value=0)
    tabla_prioridad.index.name = "Acción"
    tabla_prioridad.columns.name = None

    st.dataframe(tabla_prioridad, width="stretch")

    st.caption(
        "La prioridad viene del nivel de probabilidad de la etapa 4: Alta → "
        "primero, Media → después, Baja → al final. Si cambias las opciones del "
        "modelo en la pestaña 4, esta tabla se actualiza."
    )


    # ----------------------------------
    # 3. ALERTA DE SATURACIÓN
    # ----------------------------------

    st.subheader("5.3 Alerta: ¿estamos saturando a los clientes?")

    saturados = df_acciones["alerta_saturacion"].sum()

    st.write(
        f"**{saturados} de {len(df_acciones)} clientes** "
        f"({saturados / len(df_acciones):.0%}) recibieron "
        f"{MINIMO_CAMPANAS_SATURACION} o más campañas en 30 días y **no abrieron "
        "ningún email**."
    )

    saturacion_por_accion = (
        df_acciones.groupby("accion")["alerta_saturacion"]
        .agg(["sum", "mean"])
        .reindex(ORDEN_ACCIONES)
        .rename(columns={"sum": "Clientes saturados", "mean": "% de la acción"})
    )
    saturacion_por_accion["% de la acción"] = saturacion_por_accion["% de la acción"].map(
        lambda v: f"{v:.0%}"
    )
    saturacion_por_accion.index.name = "Acción"

    st.dataframe(saturacion_por_accion, width="stretch")

    st.warning(
        "Recomendación: para estos clientes, **no sumar más emails**. Antes de "
        "contactarlos, probar otro canal o reducir la frecuencia. Mandar más de lo "
        "mismo a quien no abre puede empeorar la relación."
    )


    # ----------------------------------
    # 4. LISTA DE CLIENTES
    # ----------------------------------

    st.subheader("5.4 Lista de clientes por acción")

    accion_elegida = st.selectbox(
        "Elige una acción:",
        ORDEN_ACCIONES,
        index=ORDEN_ACCIONES.index("Recuperar carrito"),
        key="accion_prescriptiva"
    )

    solo_no_saturados = st.checkbox(
        "Ocultar clientes con alerta de saturación",
        value=False,
        key="saturacion_prescriptiva"
    )

    lista = df_acciones[df_acciones["accion"] == accion_elegida]

    if solo_no_saturados:
        lista = lista[~lista["alerta_saturacion"]]

    lista = lista.sort_values("probabilidad_compra", ascending=False)

    columnas_lista = [
        "cliente_id", "prioridad", "probabilidad_compra",
        "categoria_preferida", "canal_origen", "ciudad",
        "alerta_saturacion", "motivo",
    ]

    st.write(f"**{len(lista)} clientes** en «{accion_elegida}».")

    st.dataframe(
        lista[columnas_lista],
        width="stretch",
        hide_index=True,
        column_config={
            "cliente_id": "Cliente",
            "prioridad": "Prioridad",
            "probabilidad_compra": st.column_config.ProgressColumn(
                "Probabilidad de compra", format="percent", min_value=0, max_value=1
            ),
            "categoria_preferida": "Vehículo de interés",
            "canal_origen": "Canal",
            "ciudad": "Ciudad",
            "alerta_saturacion": st.column_config.CheckboxColumn("¿Saturado?"),
            "motivo": st.column_config.TextColumn("¿Por qué esta acción?", width="large"),
        }
    )

    st.download_button(
        "Descargar esta lista (CSV)",
        data=lista[columnas_lista].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"clientes_{accion_elegida.lower().replace(' ', '_')}.csv",
        mime="text/csv",
        key="descargar_prescriptiva"
    )


    # ----------------------------------
    # 5. ANTES DE EJECUTAR
    # ----------------------------------

    st.subheader("5.5 Antes de ejecutar las acciones")

    st.markdown("""
    - **Separar un grupo de comparación.** Dentro de cada acción, dejar un grupo
      pequeño de clientes **sin contactar**. Solo así sabremos si la acción
      generó ventas o si esos clientes habrían comprado de todos modos.
    - **Una probabilidad alta no es una venta asegurada.** Es una forma de ordenar
      a quién llamar primero.
    - **Las reglas son una propuesta del equipo**, no una verdad del modelo.
      Discútanlas: ¿cambiarían el orden? ¿agregarían otra regla?
    - **Datos de práctica:** estos resultados sirven para aprender el proceso,
      no para decidir campañas reales.
    """)

    return df_acciones
