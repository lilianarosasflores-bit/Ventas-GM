import streamlit as st
import pandas as pd
import altair as alt

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score


SEMILLA = 42
PORCENTAJE_EXAMEN = 0.25

COLOR_AUMENTA = "#2a78d6"
COLOR_DISMINUYE = "#eb6834"
COLOR_BARRAS = "#2a78d6"

# Datos que conocemos del cliente ANTES de lanzar la campaña
DATOS_PERFIL_Y_NAVEGACION = [
    "edad", "ingreso_mensual", "antiguedad_dias",
    "visitas_web_30d", "productos_vistos_30d", "carritos_30d",
]

DATOS_CATEGORICOS = [
    "genero", "ciudad", "canal_origen", "categoria_preferida",
]

DATOS_CAMPANAS_PREVIAS = [
    "campanas_recibidas_30d", "emails_abiertos_30d", "clics_campanas_30d",
]

# Nombres en lenguaje de negocio
NOMBRES_AMIGABLES = {
    "edad": "Edad",
    "ingreso_mensual": "Ingreso mensual",
    "antiguedad_dias": "Antigüedad como cliente",
    "visitas_web_30d": "Visitas a la web (30 días)",
    "productos_vistos_30d": "Vehículos vistos (30 días)",
    "carritos_30d": "Agregó un vehículo al carrito (30 días)",
    "campanas_recibidas_30d": "Campañas recibidas (30 días)",
    "emails_abiertos_30d": "Emails abiertos (30 días)",
    "clics_campanas_30d": "Clics en campañas (30 días)",
    "genero": "Género",
    "ciudad": "Ciudad",
    "canal_origen": "Canal por el que llegó",
    "categoria_preferida": "Vehículo de interés",
}


# ----------------------------------
# FUNCIONES DE APOYO
# ----------------------------------

def preparar_datos(df):
    """Agrega la antigüedad del cliente (días desde su alta hasta la fecha más reciente)."""
    df_modelo = df.copy()
    fechas = pd.to_datetime(df_modelo["fecha_alta"])
    df_modelo["antiguedad_dias"] = (fechas.max() - fechas).dt.days
    return df_modelo


def entrenar_modelo(df_modelo, columnas_numericas, columnas_categoricas):
    """Separa clientes de práctica y de examen, y entrena una regresión logística."""
    X = df_modelo[columnas_numericas + columnas_categoricas]
    y = df_modelo["compro_ultima_campana"]

    X_practica, X_examen, y_practica, y_examen = train_test_split(
        X, y,
        test_size=PORCENTAJE_EXAMEN,
        random_state=SEMILLA,
        stratify=y
    )

    preparacion = ColumnTransformer([
        ("num", StandardScaler(), columnas_numericas),
        ("cat", OneHotEncoder(handle_unknown="ignore"), columnas_categoricas),
    ])

    modelo = Pipeline([
        ("preparacion", preparacion),
        ("modelo", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])

    modelo.fit(X_practica, y_practica)

    return modelo, X_examen, y_examen


def nombre_factor(nombre_tecnico):
    """Convierte 'cat__ciudad_guanajuato' en 'Ciudad: guanajuato'."""
    tipo, variable = nombre_tecnico.split("__", 1)

    if tipo == "num":
        return NOMBRES_AMIGABLES.get(variable, variable)

    for columna in DATOS_CATEGORICOS:
        if variable.startswith(columna + "_"):
            valor = variable[len(columna) + 1:]
            return f"{NOMBRES_AMIGABLES[columna]}: {valor}"

    return variable


def nivel_probabilidad(probabilidad):
    if probabilidad >= 0.6:
        return "Alta"
    if probabilidad >= 0.4:
        return "Media"
    return "Baja"


def de_cada_10(valor):
    return "Nadie marcado" if valor is None else f"{valor * 10:.1f} de cada 10"


# ----------------------------------
# PESTAÑA
# ----------------------------------

def mostrar(df):
    """Estima la probabilidad de compra de cada cliente y explica el resultado
    en lenguaje de mercadotecnia. Devuelve df con dos columnas nuevas:
    probabilidad_compra y nivel_probabilidad."""

    # ----------------------------------
    # ENCABEZADO
    # ----------------------------------

    st.header("4. Estadística predictiva")

    st.markdown("""
    ### Pregunta de esta etapa

    **Antes de lanzar una campaña, ¿qué clientes tienen más probabilidad de comprar?**

    Usamos un modelo que **aprende de clientes pasados**: revisa quiénes compraron
    y quiénes no, busca patrones y después le asigna a cada cliente un
    **puntaje de probabilidad de compra** (de 0% a 100%).
    """)

    st.info(
        "Piensa en el modelo como un **asistente que prioriza**, no como un adivino. "
        "Nos ayuda a decidir a quién contactar primero, pero la decisión final "
        "siempre la toma una persona."
    )


    # ----------------------------------
    # 1. INFORMACIÓN QUE USA EL MODELO
    # ----------------------------------

    st.subheader("4.1 ¿Qué información usa el modelo?")

    st.write(
        "Solo usamos datos que **ya conocemos antes de lanzar la campaña**. "
        "Si usáramos datos que se generan *después*, el modelo parecería perfecto "
        "pero no serviría en la vida real (sería como hacer un examen con las respuestas)."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ✅ **Sí usamos**
        - Perfil: edad, género, ciudad, ingreso
        - Antigüedad como cliente
        - Canal por el que llegó y vehículo de interés
        - Navegación en la web: visitas, vehículos vistos, carritos
        """)

    with col2:
        st.markdown("""
        ❌ **No usamos (y por qué)**
        - **Compras e importe de los últimos 12 meses:** ya incluyen la compra
          de la campaña; sería darle la respuesta.
        - **Abandono de carrito:** ningún cliente que "abandonó" compró;
          abandonar significa justamente *no comprar*.
        - **Cupones y descuentos:** todos tienen el mismo valor (0).
        - **ID del cliente:** es solo un número de registro.
        """)

    incluir_campanas = st.checkbox(
        "Incluir la respuesta a campañas anteriores (campañas recibidas, "
        "emails abiertos y clics)",
        value=False,
        key="incluir_campanas_predictiva"
    )

    st.caption(
        "Actívalo solo si confirmas que esas aperturas y clics son de "
        "campañas **anteriores** y no de la campaña que queremos predecir. "
        "El dataset no lo aclara, por eso viene apagado."
    )

    columnas_numericas = list(DATOS_PERFIL_Y_NAVEGACION)
    if incluir_campanas:
        columnas_numericas += DATOS_CAMPANAS_PREVIAS

    df_modelo = preparar_datos(df)
    modelo, X_examen, y_examen = entrenar_modelo(
        df_modelo, columnas_numericas, DATOS_CATEGORICOS
    )


    # ----------------------------------
    # 2. ¿QUÉ TAN CONFIABLE ES?
    # ----------------------------------

    st.subheader("4.2 ¿Qué tan bien funciona?")

    st.write(
        f"Para comprobarlo, el modelo aprendió con el {1 - PORCENTAJE_EXAMEN:.0%} "
        f"de los clientes y luego le hicimos un **examen** con el otro "
        f"{PORCENTAJE_EXAMEN:.0%} ({len(X_examen)} clientes) que **nunca había visto**."
    )

    umbral = st.slider(
        "¿A partir de qué probabilidad consideramos a un cliente "
        "«probable comprador»?",
        min_value=0.20,
        max_value=0.80,
        value=0.50,
        step=0.05,
        format="%.2f",
        key="umbral_predictiva"
    )

    st.caption(
        "Más bajo = contactamos a más clientes (encontramos más compradores, "
        "pero también más falsas alarmas). Más alto = lista más corta y más "
        "segura, pero se nos escapan compradores."
    )

    prob_examen = modelo.predict_proba(X_examen)[:, 1]
    marcados = prob_examen >= umbral
    compraron = y_examen.values == 1

    aciertos_compra = int((marcados & compraron).sum())
    falsas_alarmas = int((marcados & ~compraron).sum())
    oportunidades_perdidas = int((~marcados & compraron).sum())
    aciertos_no_compra = int((~marcados & ~compraron).sum())

    precision = aciertos_compra / marcados.sum() if marcados.sum() > 0 else None
    cobertura = aciertos_compra / compraron.sum() if compraron.sum() > 0 else None
    capacidad_ordenar = roc_auc_score(y_examen, prob_examen)
    tasa_real = compraron.mean()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Puntería",
            f"{de_cada_10(precision)}",
            help="De cada 10 clientes que el modelo marca como probables "
                 "compradores, cuántos sí compraron."
        )
        st.caption("de los clientes que el modelo señala **sí compraron**")

    with col2:
        st.metric(
            "Alcance",
            f"{de_cada_10(cobertura)}",
            help="De cada 10 clientes que sí compraron, cuántos detectó el modelo."
        )
        st.caption("de los compradores reales **fueron detectados**")

    with col3:
        st.metric(
            "Sin modelo (al azar)",
            f"{de_cada_10(tasa_real)}",
            help="Si eligiéramos clientes al azar, esta sería la proporción "
                 "de compradores."
        )
        st.caption("comprarían si elegimos clientes **al azar**")

    if precision is not None and precision > tasa_real:
        st.success(
            f"Con el modelo, la lista de contacto tiene **{precision / tasa_real:.1f} veces** "
            "más compradores que una lista elegida al azar."
        )
    elif precision is None:
        st.warning("Con este nivel, el modelo no marca a ningún cliente. Baja el nivel.")
    else:
        st.warning("Con este nivel, el modelo no mejora a una selección al azar.")

    # Resultado del examen en 4 cajas
    st.write("**Resultado del examen**")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("✅ Le apostamos y compró", aciertos_compra)
        st.metric("⚠️ Se nos escapó: no le apostamos y sí compró", oportunidades_perdidas)

    with col2:
        st.metric("💸 Falsa alarma: le apostamos y no compró", falsas_alarmas)
        st.metric("✅ No le apostamos y no compró", aciertos_no_compra)

    # Capacidad de ordenar explicada como semáforo
    if capacidad_ordenar >= 0.75:
        semaforo = "🟢 Buena"
    elif capacidad_ordenar >= 0.60:
        semaforo = "🟡 Moderada"
    else:
        semaforo = "🔴 Débil"

    st.write(
        f"**Capacidad para ordenar clientes: {semaforo}.** Si tomamos al azar un "
        f"cliente que compró y uno que no, el modelo le da mayor probabilidad al "
        f"comprador **{capacidad_ordenar:.0%} de las veces** "
        "(50% sería lanzar una moneda; 100% sería perfecto)."
    )


    # ----------------------------------
    # 3. FACTORES QUE MÁS PESAN
    # ----------------------------------

    st.subheader("4.3 ¿Qué factores pesan más en la probabilidad?")

    nombres = modelo.named_steps["preparacion"].get_feature_names_out()
    pesos = modelo.named_steps["modelo"].coef_[0]

    factores = pd.DataFrame({
        "Factor": [nombre_factor(n) for n in nombres],
        "Peso": pesos,
    })
    factores["Efecto"] = factores["Peso"].map(
        lambda p: "Aumenta la probabilidad" if p > 0 else "Disminuye la probabilidad"
    )
    factores["Importancia"] = factores["Peso"].abs()
    factores = factores.sort_values("Importancia", ascending=False).head(10)

    grafica_factores = (
        alt.Chart(factores)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("Peso:Q", title="← Disminuye        Peso en la probabilidad        Aumenta →",
                    axis=alt.Axis(labels=False, ticks=False)),
            y=alt.Y("Factor:N", sort=alt.EncodingSortField("Importancia", order="descending"),
                    title=None),
            color=alt.Color(
                "Efecto:N",
                scale=alt.Scale(
                    domain=["Aumenta la probabilidad", "Disminuye la probabilidad"],
                    range=[COLOR_AUMENTA, COLOR_DISMINUYE]
                ),
                legend=alt.Legend(title=None, orient="top")
            ),
            tooltip=[alt.Tooltip("Factor:N"), alt.Tooltip("Efecto:N")]
        )
    )

    st.altair_chart(grafica_factores, width="stretch")

    st.caption(
        "Se muestran los 10 factores con más peso. Las barras más largas influyen "
        "más. **Importante:** que un factor esté asociado con la compra no significa "
        "que la cause. Por ejemplo, un cliente que ve muchos vehículos puede ya tener "
        "decidido comprar; mandarle más visitas a la web no garantiza la venta."
    )


    # ----------------------------------
    # 4. PUNTAJE DE CADA CLIENTE
    # ----------------------------------

    st.subheader("4.4 Probabilidad de compra de cada cliente")

    df_resultado = df.copy()
    df_resultado["probabilidad_compra"] = modelo.predict_proba(
        df_modelo[columnas_numericas + DATOS_CATEGORICOS]
    )[:, 1]
    df_resultado["nivel_probabilidad"] = df_resultado["probabilidad_compra"].map(
        nivel_probabilidad
    )

    st.write(
        "Agrupamos a los clientes en tres niveles: **Alta** (60% o más), "
        "**Media** (40% a 59%) y **Baja** (menos de 40%)."
    )

    # ¿Se cumple en el examen? Compra real por nivel, solo clientes del examen
    examen = df_resultado.loc[X_examen.index]
    orden_niveles = ["Alta", "Media", "Baja"]

    resumen_niveles = pd.DataFrame({
        "Nivel": orden_niveles,
        "Clientes (todos)": [
            (df_resultado["nivel_probabilidad"] == n).sum() for n in orden_niveles
        ],
        "Clientes en el examen": [
            (examen["nivel_probabilidad"] == n).sum() for n in orden_niveles
        ],
        "Compraron realmente (examen)": [
            examen.loc[examen["nivel_probabilidad"] == n, "compro_ultima_campana"].mean()
            for n in orden_niveles
        ],
    })

    grafica_niveles = (
        alt.Chart(resumen_niveles.dropna())
        .mark_bar(color=COLOR_BARRAS, cornerRadiusEnd=4)
        .encode(
            x=alt.X("Nivel:N", sort=orden_niveles, title="Nivel de probabilidad"),
            y=alt.Y("Compraron realmente (examen):Q", title="% que compró realmente",
                    axis=alt.Axis(format=".0%")),
            tooltip=[
                alt.Tooltip("Nivel:N"),
                alt.Tooltip("Compraron realmente (examen):Q", format=".0%"),
                alt.Tooltip("Clientes en el examen:Q"),
            ]
        )
    )

    col1, col2 = st.columns(2)

    with col1:
        st.altair_chart(grafica_niveles, width="stretch")

    with col2:
        tabla_niveles = resumen_niveles.copy()
        tabla_niveles["Compraron realmente (examen)"] = tabla_niveles[
            "Compraron realmente (examen)"
        ].map(lambda v: "—" if pd.isnull(v) else f"{v:.0%}")
        st.dataframe(tabla_niveles, width="stretch", hide_index=True)
        st.caption(
            "Si el modelo es útil, el grupo «Alta» debe tener más compradores "
            "reales que «Media», y «Media» más que «Baja»."
        )

    nivel_elegido = st.multiselect(
        "Ver clientes del nivel:",
        orden_niveles,
        default=["Alta"],
        key="nivel_predictiva"
    )

    columnas_lista = [
        "cliente_id", "probabilidad_compra", "nivel_probabilidad",
        "categoria_preferida", "ciudad", "canal_origen",
        "visitas_web_30d", "productos_vistos_30d",
    ]

    lista_clientes = (
        df_resultado[df_resultado["nivel_probabilidad"].isin(nivel_elegido)]
        [columnas_lista]
        .sort_values("probabilidad_compra", ascending=False)
    )

    st.dataframe(
        lista_clientes,
        width="stretch",
        hide_index=True,
        column_config={
            "probabilidad_compra": st.column_config.ProgressColumn(
                "Probabilidad de compra", format="percent", min_value=0, max_value=1
            ),
            "nivel_probabilidad": "Nivel",
            "cliente_id": "Cliente",
            "categoria_preferida": "Vehículo de interés",
            "ciudad": "Ciudad",
            "canal_origen": "Canal",
            "visitas_web_30d": "Visitas web",
            "productos_vistos_30d": "Vehículos vistos",
        }
    )


    # ----------------------------------
    # 5. LÍMITES
    # ----------------------------------

    st.subheader("4.5 Antes de usar estos resultados")

    st.warning("""
    - **Son datos de práctica (sintéticos)** y solo 240 clientes: los resultados
      sirven para aprender el proceso, no para tomar decisiones reales de GM.
    - **Una probabilidad no es una promesa.** Un cliente con 80% puede no comprar
      y uno con 20% puede hacerlo.
    - **El modelo repite los patrones del pasado.** Si cambia la oferta, el precio
      o el mercado, hay que volver a revisarlo.
    - **Siempre hay revisión humana:** el equipo de mercadotecnia valida la lista
      antes de contactar a cualquier cliente.
    """)

    return df_resultado
