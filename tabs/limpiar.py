import streamlit as st
import pandas as pd
import altair as alt


def mostrar(df):
    """Diagnostica la calidad del dataset y devuelve una copia limpia.

    El DataFrame original (df) nunca se modifica. Todas las
    transformaciones se aplican sobre df_limpio y se documentan
    en la bitácora de decisiones al final de la pestaña.
    """

    df_limpio = df.copy()
    bitacora = []

    # ----------------------------------
    # ENCABEZADO
    # ----------------------------------

    st.header("2. Limpiar los datos")

    st.markdown("""
    ### Pregunta de esta etapa

    **¿Qué problemas de calidad tienen los datos y qué decidimos hacer con cada uno?**

    Regla de trabajo: primero **investigamos**, después **decidimos** y siempre
    **escribimos la razón**. El dataset original se conserva sin cambios;
    las decisiones se aplican a una copia llamada `df_limpio`.
    """)


    # ----------------------------------
    # 1. VALORES FALTANTES
    # ----------------------------------

    st.subheader("2.1 Valores faltantes")

    faltantes = pd.DataFrame({
        "Variable": df.columns,
        "Faltantes": df.isnull().sum().values,
        "% del total": (df.isnull().mean() * 100).round(1).values
    })
    faltantes = faltantes[faltantes["Faltantes"] > 0]

    if faltantes.empty:
        st.success("No hay valores faltantes.")
    else:
        st.dataframe(faltantes, width="stretch", hide_index=True)

        st.markdown("""
        **Hipótesis:** los faltantes en recencia y monto de la última compra
        pertenecen a clientes que **no han comprado** en 12 meses.
        Si es así, el faltante no es un error: es información
        ("no existe una última compra").
        """)

        # Verificar la hipótesis contra compras_12m
        sin_compras = df["compras_12m"] == 0

        verificacion = pd.crosstab(
            df["dias_desde_ultima_compra"].isnull().map(
                {True: "Recencia faltante", False: "Recencia registrada"}
            ),
            sin_compras.map(
                {True: "Sin compras (compras_12m = 0)", False: "Con compras"}
            )
        )

        st.write("**Verificación: faltantes vs. compras en 12 meses**")
        st.dataframe(verificacion, width="stretch")

        coincide = (
            df["dias_desde_ultima_compra"].isnull().equals(sin_compras)
            and df["monto_ultima_compra"].isnull().equals(sin_compras)
        )

        if coincide:
            st.info(
                "La hipótesis se confirma: cada faltante corresponde a un "
                "cliente sin compras. **Decisión:** no imputamos ni eliminamos "
                "estos valores; agregamos la columna `sin_historial_compra` "
                "para que el significado quede explícito."
            )
            df_limpio["sin_historial_compra"] = sin_compras.astype(int)
            bitacora.append({
                "Problema": "Faltantes en dias_desde_ultima_compra y monto_ultima_compra",
                "Evidencia": f"{sin_compras.sum()} faltantes, todos con compras_12m = 0",
                "Decisión": "Conservar como faltantes + crear sin_historial_compra",
                "Razón": "No hay última compra; poner 0 inventaría una compra reciente de $0"
            })
        else:
            st.warning(
                "Los faltantes **no** coinciden por completo con clientes sin "
                "compras. Revisa los registros antes de decidir un tratamiento."
            )
            bitacora.append({
                "Problema": "Faltantes en recencia/monto",
                "Evidencia": "No coinciden totalmente con compras_12m = 0",
                "Decisión": "Pendiente de revisión",
                "Razón": "El significado del faltante no está establecido"
            })


    # ----------------------------------
    # 2. DUPLICADOS
    # ----------------------------------

    st.subheader("2.2 Duplicados")

    duplicados_exactos = df.duplicated().sum()
    duplicados_id = df["cliente_id"].duplicated().sum()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Filas idénticas", duplicados_exactos)

    with col2:
        st.metric("cliente_id repetidos", duplicados_id)

    if duplicados_exactos == 0 and duplicados_id == 0:
        st.success("Cada fila representa a un cliente distinto. No se elimina nada.")
    else:
        st.warning("Hay duplicados: revísalos antes de eliminarlos.")

    bitacora.append({
        "Problema": "Duplicados",
        "Evidencia": f"{duplicados_exactos} filas idénticas, {duplicados_id} IDs repetidos",
        "Decisión": "Sin cambios" if duplicados_exactos + duplicados_id == 0 else "Pendiente de revisión",
        "Razón": "Solo se elimina un duplicado si se confirma que es el mismo cliente"
    })


    # ----------------------------------
    # 3. TIPOS DE DATOS
    # ----------------------------------

    st.subheader("2.3 Tipos de datos")

    st.write(
        f"`fecha_alta` se leyó como **{df['fecha_alta'].dtype}** (texto). "
        "Para calcular antigüedad necesitamos convertirla a fecha."
    )

    fechas = pd.to_datetime(df["fecha_alta"], errors="coerce")
    fechas_invalidas = fechas.isnull().sum() - df["fecha_alta"].isnull().sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Fechas no convertibles", fechas_invalidas)

    with col2:
        st.metric("Primera alta", str(fechas.min().date()))

    with col3:
        st.metric("Última alta", str(fechas.max().date()))

    df_limpio["fecha_alta"] = fechas

    bitacora.append({
        "Problema": "fecha_alta guardada como texto",
        "Evidencia": f"{fechas_invalidas} fechas no convertibles",
        "Decisión": "Convertir a fecha en df_limpio",
        "Razón": "Permite calcular antigüedad del cliente en etapas posteriores"
    })


    # ----------------------------------
    # 4. RANGOS Y CONSISTENCIA
    # ----------------------------------

    st.subheader("2.4 Rangos válidos y consistencia lógica")

    st.write(
        "Cada regla describe algo que **debería** cumplirse. "
        "Contamos cuántos clientes la incumplen."
    )

    columnas_no_negativas = [
        "ingreso_mensual", "visitas_web_30d", "productos_vistos_30d",
        "carritos_30d", "compras_12m", "gasto_total_12m",
        "campanas_recibidas_30d", "emails_abiertos_30d", "clics_campanas_30d"
    ]

    reglas = {
        "Edad entre 18 y 100 años":
            ~df["edad"].between(18, 100),
        "Conteos y montos no negativos":
            (df[columnas_no_negativas] < 0).any(axis=1),
        "Emails abiertos ≤ campañas recibidas":
            df["emails_abiertos_30d"] > df["campanas_recibidas_30d"],
        "Clics ≤ campañas recibidas":
            df["clics_campanas_30d"] > df["campanas_recibidas_30d"],
        "Sin compras ⇒ gasto total = 0":
            (df["compras_12m"] == 0) & (df["gasto_total_12m"] > 0),
        "Abandono de carrito ⇒ al menos un carrito":
            (df["abandono_carrito_30d"] == 1) & (df["carritos_30d"] == 0),
    }

    resumen_reglas = pd.DataFrame({
        "Regla": list(reglas.keys()),
        "Clientes que no la cumplen": [int(m.sum()) for m in reglas.values()]
    })

    st.dataframe(resumen_reglas, width="stretch", hide_index=True)

    regla_elegida = st.selectbox(
        "Ver los registros que incumplen una regla:",
        list(reglas.keys()),
        key="regla_limpiar"
    )

    incumplen = df[reglas[regla_elegida]]

    if incumplen.empty:
        st.success("Ningún registro incumple esta regla.")
    else:
        st.dataframe(incumplen, width="stretch", hide_index=True)

    # Inconsistencia de carrito: se marca, no se corrige
    mascara_carrito = reglas["Abandono de carrito ⇒ al menos un carrito"]

    if mascara_carrito.any():
        st.warning(
            f"{mascara_carrito.sum()} clientes tienen abandono de carrito "
            "sin carritos registrados. Puede ser un error de captura o una "
            "definición distinta de 'carrito'. **Decisión:** no corregimos el "
            "dato; lo marcamos en `alerta_carrito` para revisarlo con el "
            "dueño de los datos."
        )
        df_limpio["alerta_carrito"] = mascara_carrito.astype(int)
        bitacora.append({
            "Problema": "abandono_carrito_30d = 1 con carritos_30d = 0",
            "Evidencia": f"{mascara_carrito.sum()} clientes",
            "Decisión": "Conservar y marcar con alerta_carrito",
            "Razón": "No sabemos cuál de los dos campos es el correcto"
        })


    # ----------------------------------
    # 5. VARIABLES SIN VARIACIÓN
    # ----------------------------------

    st.subheader("2.5 Variables sin variación")

    constantes = [c for c in df.columns if df[c].nunique(dropna=False) == 1]

    if constantes:
        st.warning(
            "Estas variables tienen **el mismo valor para todos los clientes**: "
            + ", ".join(f"`{c}`" for c in constantes)
            + ". No ayudan a distinguir clientes ni a predecir compra."
        )
        st.dataframe(
            df[constantes].drop_duplicates(),
            width="stretch",
            hide_index=True
        )
        bitacora.append({
            "Problema": "Variables constantes",
            "Evidencia": ", ".join(constantes),
            "Decisión": "Conservar en los datos; excluir de modelos y segmentación",
            "Razón": "Sin variación no aportan información en esta muestra"
        })
    else:
        st.success("Todas las variables tienen más de un valor.")


    # ----------------------------------
    # 6. VALORES ATÍPICOS
    # ----------------------------------

    st.subheader("2.6 Valores atípicos (regla IQR)")

    st.write(
        "Un valor es atípico si está por debajo de Q1 − 1.5·IQR o por encima "
        "de Q3 + 1.5·IQR. **Atípico no significa erróneo**: un cliente con "
        "ingreso alto puede ser real e importante."
    )

    columnas_numericas = [
        c for c in df.select_dtypes(include="number").columns
        if c not in constantes
    ]

    variable = st.selectbox(
        "Selecciona una variable numérica:",
        columnas_numericas,
        key="variable_atipicos_limpiar"
    )

    serie = df[variable].dropna()
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr
    atipicos = serie[(serie < limite_inferior) | (serie > limite_superior)]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Límite inferior", round(limite_inferior, 2))

    with col2:
        st.metric("Límite superior", round(limite_superior, 2))

    with col3:
        st.metric("Valores atípicos", len(atipicos))

    histograma = (
        alt.Chart(serie.to_frame())
        .mark_bar()
        .encode(
            x=alt.X(variable, bin=alt.Bin(maxbins=30), title=variable),
            y=alt.Y("count()", title="Clientes")
        )
    )

    st.altair_chart(histograma, width="stretch")

    if len(atipicos) > 0:
        st.dataframe(
            df.loc[atipicos.index],
            width="stretch",
            hide_index=True
        )

    bitacora.append({
        "Problema": "Valores atípicos",
        "Evidencia": "Revisión por variable con regla IQR",
        "Decisión": "Conservar todos los valores",
        "Razón": "Un valor extremo no se elimina sin evidencia de que sea un error"
    })


    # ----------------------------------
    # 7. ALERTA PARA LA ETAPA PREDICTIVA
    # ----------------------------------

    st.subheader("2.7 Alerta: posible fuga de información")

    coincidencia = (
        (df["compras_12m"] > 0).astype(int) == df["compro_ultima_campana"]
    ).mean() * 100

    st.write(
        f"Haber comprado en 12 meses (`compras_12m > 0`) coincide con "
        f"`compro_ultima_campana` en el **{coincidencia:.1f}%** de los clientes."
    )

    if coincidencia > 95:
        st.error(
            "Las variables de historial de compra (`compras_12m`, "
            "`gasto_total_12m`, `dias_desde_ultima_compra`, "
            "`monto_ultima_compra`) parecen **incluir la compra de la última "
            "campaña**. Si se usan para predecirla, el modelo estaría "
            "'viendo la respuesta'. No las borramos aquí, pero deberemos "
            "decidir en la etapa 4 si estaban disponibles **antes** de la campaña."
        )
        bitacora.append({
            "Problema": "Posible fuga de información",
            "Evidencia": f"compras_12m > 0 coincide {coincidencia:.1f}% con el objetivo",
            "Decisión": "Conservar; revisar en la etapa predictiva",
            "Razón": "Hay que definir el momento de la predicción antes de elegir variables"
        })


    # ----------------------------------
    # 8. BITÁCORA Y RESULTADO
    # ----------------------------------

    st.subheader("2.8 Bitácora de decisiones")

    st.dataframe(pd.DataFrame(bitacora), width="stretch", hide_index=True)

    st.subheader("Resultado: dataset original vs. dataset limpio")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Original (filas × columnas)", f"{df.shape[0]} × {df.shape[1]}")

    with col2:
        st.metric(
            "Limpio (filas × columnas)",
            f"{df_limpio.shape[0]} × {df_limpio.shape[1]}"
        )

    columnas_nuevas = [c for c in df_limpio.columns if c not in df.columns]
    if columnas_nuevas:
        st.write("Columnas agregadas: " + ", ".join(f"`{c}`" for c in columnas_nuevas))

    st.dataframe(df_limpio.head(10), width="stretch", hide_index=True)

    return df_limpio
