import streamlit as st
import pandas as pd


ORDEN_ACCIONES = [
    "Recuperar carrito",
    "Reactivar interés",
    "Seguimiento postventa",
    "Verificar datos",
]

# Lo que se decide para cada acción. Las cifras se calculan con los datos;
# estos textos son la propuesta del equipo y se pueden discutir en clase.
PLAN_POR_ACCION = {
    "Recuperar carrito": {
        "Recomendación": "Recordatorio del vehículo que dejó en el carrito y "
                         "ofrecer la ayuda de un asesor.",
        "KPI a mover": "% de clientes del grupo que compran",
        "Responsable sugerido": "Asesores de venta + equipo CRM",
        "Próximo paso": "Contactar primero a prioridad 1; dejar un grupo sin contactar.",
        "Riesgo": "Insistir demasiado; la mayoría ya está saturada de emails.",
        "Cómo medimos": "Comparar % de compra entre contactados y no contactados.",
    },
    "Reactivar interés": {
        "Recomendación": "Mensajes informativos de bajo costo sobre su vehículo "
                         "de interés, sin presionar.",
        "KPI a mover": "Tasa de apertura y visitas a la web",
        "Responsable sugerido": "Equipo de contenido / CRM",
        "Próximo paso": "Enviar un mensaje informativo y revisar respuesta en 30 días.",
        "Riesgo": "Gastar en clientes con poco interés real.",
        "Cómo medimos": "Comparar apertura y visitas entre contactados y no contactados.",
    },
    "Seguimiento postventa": {
        "Recomendación": "Agradecer la compra y preguntar por su experiencia. "
                         "No enviar ofertas de otro vehículo.",
        "KPI a mover": "Satisfacción del cliente (dato nuevo: encuesta)",
        "Responsable sugerido": "Servicio al cliente",
        "Próximo paso": "Diseñar una encuesta corta de satisfacción.",
        "Riesgo": "Hoy no medimos satisfacción; sin encuesta no sabremos si funcionó.",
        "Cómo medimos": "Respuestas de la encuesta (hay que empezar a recolectarlas).",
    },
    "Verificar datos": {
        "Recomendación": "No contactar hasta revisar sus registros.",
        "KPI a mover": "% de registros revisados y corregidos",
        "Responsable sugerido": "Equipo de datos",
        "Próximo paso": "Revisar por qué hay abandono de carrito sin carrito.",
        "Riesgo": "Enviar un mensaje equivocado por un dato erróneo.",
        "Cómo medimos": "Registros corregidos / registros con alerta.",
    },
}

NOMBRE_VEHICULO = {
    "suv electrica": "SUV eléctrica",
    "pickup electrica": "pickup eléctrica",
}

CANAL_SUGERIDO = {
    "email": "Email",
    "meta ads": "Anuncio en redes sociales (Meta)",
    "directo": "Contacto de un asesor",
    "organico": "Email",
}


# ----------------------------------
# FUNCIONES DE APOYO
# ----------------------------------

def evidencia_accion(grupo):
    """Resume con cifras lo que sabemos del grupo."""
    clientes = len(grupo)
    recibidas = grupo["campanas_recibidas_30d"].sum()
    apertura = grupo["emails_abiertos_30d"].sum() / recibidas if recibidas > 0 else None
    vehiculo = grupo["categoria_preferida"].value_counts(normalize=True)

    texto = (
        f"{clientes} clientes · probabilidad promedio "
        f"{grupo['probabilidad_compra'].mean():.0%} · "
        f"{grupo['alerta_saturacion'].mean():.0%} saturados · "
        f"{vehiculo.iloc[0]:.0%} prefiere {NOMBRE_VEHICULO.get(vehiculo.index[0], vehiculo.index[0])}"
    )

    if apertura is not None:
        texto += f" · apertura de emails {apertura:.0%}"

    return texto


def valor_actual_kpi(accion, grupo):
    """Valor de partida del KPI con los datos disponibles."""
    if accion == "Recuperar carrito":
        return f"{grupo['compro_ultima_campana'].mean():.0%} compró en la última campaña"
    if accion == "Reactivar interés":
        recibidas = grupo["campanas_recibidas_30d"].sum()
        apertura = grupo["emails_abiertos_30d"].sum() / recibidas if recibidas > 0 else 0
        return f"Apertura {apertura:.0%} · {grupo['visitas_web_30d'].mean():.0f} visitas promedio"
    if accion == "Verificar datos":
        return f"0 de {len(grupo)} revisados"
    return "Sin dato (no existe encuesta)"


def construir_mensaje(accion, cliente):
    """Mensaje de ejemplo usando solo datos que existen en el dataset."""
    vehiculo = NOMBRE_VEHICULO.get(cliente["categoria_preferida"], cliente["categoria_preferida"])

    if accion == "Recuperar carrito":
        return (
            f"Hola. Vimos que te interesó una {vehiculo}. "
            "Si tienes preguntas sobre el vehículo, un asesor puede ayudarte "
            "a resolverlas. Responde a este mensaje y te contactamos."
        )
    if accion == "Reactivar interés":
        return (
            f"Hola. Te compartimos información sobre la {vehiculo}, "
            "el tipo de vehículo que has consultado con nosotros. "
            "Si prefieres recibir menos mensajes, puedes indicárnoslo."
        )
    if accion == "Seguimiento postventa":
        return (
            "Hola. Gracias por tu compra. Nos gustaría saber cómo ha sido tu "
            "experiencia hasta ahora. ¿Nos ayudas respondiendo una pregunta corta?"
        )
    return None


# ----------------------------------
# PESTAÑA
# ----------------------------------

def mostrar(df):
    """Vista final: conecta KPI, segmento, evidencia, recomendación,
    responsable y plan de medición. Recibe df_acciones (etapa 5)."""

    # ----------------------------------
    # ENCABEZADO
    # ----------------------------------

    st.header("6. Toma de decisiones")

    st.markdown("""
    ### Pregunta de esta etapa

    **¿Qué vamos a hacer, quién lo hace y cómo sabremos si funcionó?**

    Aquí juntamos todo lo anterior en un plan: para cada grupo de clientes,
    **qué sabemos**, **qué recomendamos**, **quién es responsable** y
    **cómo lo vamos a medir**.
    """)


    # ----------------------------------
    # 1. RESUMEN PARA DIRECCIÓN
    # ----------------------------------

    st.subheader("6.1 Resumen en 30 segundos")

    total = len(df)
    compraron = df["compro_ultima_campana"].sum()
    carrito = (df["accion"] == "Recuperar carrito").sum()
    carrito_prioridad_1 = (
        (df["accion"] == "Recuperar carrito")
        & (df["prioridad"] == "1 · Contactar primero")
    ).sum()
    saturados = df["alerta_saturacion"].sum()
    verificar = (df["accion"] == "Verificar datos").sum()

    st.markdown(f"""
    - De **{total} clientes**, **{compraron} ({compraron / total:.0%})** compraron en la última campaña.
    - La mayor oportunidad son **{carrito} clientes que dejaron un vehículo en el carrito**;
      **{carrito_prioridad_1}** tienen probabilidad alta y conviene contactarlos primero.
    - **{saturados} clientes ({saturados / total:.0%})** recibieron muchas campañas sin abrir
      ningún email: **más emails no es la solución**.
    - **{verificar} registros** tienen datos contradictorios y no deben contactarse hasta revisarlos.
    """)


    # ----------------------------------
    # 2. TABLERO DE DECISIONES
    # ----------------------------------

    st.subheader("6.2 Tablero de decisiones")

    filas = []
    for accion in ORDEN_ACCIONES:
        grupo = df[df["accion"] == accion]
        if grupo.empty:
            continue
        plan = PLAN_POR_ACCION[accion]
        filas.append({
            "Acción": accion,
            "Clientes": len(grupo),
            "Evidencia": evidencia_accion(grupo),
            "Recomendación": plan["Recomendación"],
            "KPI a mover": plan["KPI a mover"],
            "Valor actual": valor_actual_kpi(accion, grupo),
            "Riesgo": plan["Riesgo"],
            "Cómo medimos": plan["Cómo medimos"],
        })

    tablero = pd.DataFrame(filas)

    st.dataframe(
        tablero,
        width="stretch",
        hide_index=True,
        column_config={
            "Evidencia": st.column_config.TextColumn(width="large"),
            "Recomendación": st.column_config.TextColumn(width="large"),
        }
    )


    # ----------------------------------
    # 3. PLAN DE TRABAJO (EDITABLE)
    # ----------------------------------

    st.subheader("6.3 Plan de trabajo: ¿quién hace qué?")

    st.write(
        "Esta tabla es **editable**: escribe sobre ella para asignar responsables, "
        "próximos pasos y fechas. Los valores iniciales son solo una sugerencia."
    )

    plan_inicial = pd.DataFrame([
        {
            "Acción": accion,
            "Responsable": PLAN_POR_ACCION[accion]["Responsable sugerido"],
            "Próximo paso": PLAN_POR_ACCION[accion]["Próximo paso"],
            "Fecha límite": None,
        }
        for accion in tablero["Acción"]
    ])

    plan_editado = st.data_editor(
        plan_inicial,
        width="stretch",
        hide_index=True,
        disabled=["Acción"],
        column_config={
            "Próximo paso": st.column_config.TextColumn(width="large"),
            "Fecha límite": st.column_config.DateColumn(format="DD/MM/YYYY"),
        },
        key="plan_decisiones"
    )

    plan_completo = tablero.merge(plan_editado, on="Acción")

    st.download_button(
        "Descargar el plan completo (CSV)",
        data=plan_completo.to_csv(index=False).encode("utf-8-sig"),
        file_name="plan_de_decisiones.csv",
        mime="text/csv",
        key="descargar_decisiones"
    )


    # ----------------------------------
    # 4. DETALLE POR ACCIÓN Y MENSAJE
    # ----------------------------------

    st.subheader("6.4 Detalle de una acción y mensaje de ejemplo")

    accion = st.selectbox(
        "Elige una acción:",
        list(tablero["Acción"]),
        key="accion_decisiones"
    )

    grupo = df[df["accion"] == accion].sort_values("probabilidad_compra", ascending=False)
    plan = PLAN_POR_ACCION[accion]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Clientes", len(grupo))
    with col2:
        st.metric("Probabilidad promedio", f"{grupo['probabilidad_compra'].mean():.0%}")
    with col3:
        st.metric("Con alerta de saturación", f"{grupo['alerta_saturacion'].mean():.0%}")

    st.markdown(f"""
    **Recomendación:** {plan['Recomendación']}

    **Riesgo:** {plan['Riesgo']}
    """)

    # Mensaje de ejemplo para un cliente real del grupo
    st.write("**Mensaje de ejemplo**")

    cliente_id = st.selectbox(
        "Cliente (ordenados de mayor a menor probabilidad):",
        list(grupo["cliente_id"]),
        key="cliente_decisiones"
    )

    cliente = grupo[grupo["cliente_id"] == cliente_id].iloc[0]
    mensaje = construir_mensaje(accion, cliente)

    if mensaje is None:
        st.warning(
            "Para este grupo **no se envía mensaje**: primero hay que verificar "
            "sus datos."
        )
    else:
        if cliente["alerta_saturacion"]:
            canal = "Otro canal distinto al email (cliente saturado de emails)"
        else:
            canal = CANAL_SUGERIDO.get(cliente["canal_origen"], "Por definir con el equipo")

        st.success(mensaje)

        st.caption(
            f"Canal sugerido: **{canal}** · Datos usados: vehículo de interés "
            f"(`{cliente['categoria_preferida']}`), canal de origen "
            f"(`{cliente['canal_origen']}`) y alerta de saturación."
        )

        st.markdown("""
        **Lo que el mensaje NO incluye a propósito:**
        - ❌ Descuentos o promociones (no hay datos de cómo responden a descuentos)
        - ❌ Urgencia ("últimas unidades", "solo hoy")
        - ❌ Inventario, precios o entregas que no conocemos
        - ❌ Beneficios no confirmados por el negocio
        """)


    # ----------------------------------
    # 5. PLAN DE MEDICIÓN
    # ----------------------------------

    st.subheader("6.5 ¿Cómo sabremos si funcionó?")

    st.write(
        "Separamos al azar un **grupo de comparación** que **no** recibe la acción. "
        "Al final comparamos los resultados de ambos grupos: la diferencia es lo "
        "que realmente logró la acción."
    )

    porcentaje_comparacion = st.slider(
        "¿Qué porcentaje del grupo dejamos sin contactar?",
        min_value=10,
        max_value=50,
        value=20,
        step=5,
        format="%d%%",
        key="comparacion_decisiones"
    )

    sin_contactar = round(len(grupo) * porcentaje_comparacion / 100)
    contactados = len(grupo) - sin_contactar

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Clientes contactados", contactados)
    with col2:
        st.metric("Grupo de comparación", sin_contactar)
    with col3:
        st.metric("KPI a comparar", plan["KPI a mover"])

    if accion == "Verificar datos":
        st.info("Esta acción no necesita grupo de comparación: es una revisión interna.")
    elif sin_contactar < 30:
        st.warning(
            f"El grupo de comparación tiene solo {sin_contactar} clientes. Con tan "
            "pocos, una diferencia puede deberse a la casualidad. Tómalo como una "
            "prueba piloto, no como prueba definitiva."
        )


    # ----------------------------------
    # 6. CIERRE
    # ----------------------------------

    st.subheader("6.6 Para cerrar")

    st.markdown("""
    **Respondiendo la pregunta del proyecto:** los clientes con mayor intención de
    compra son quienes **dejaron un vehículo en el carrito**, sobre todo los de
    probabilidad alta. Para ellos recomendamos un recordatorio con apoyo de un
    asesor, cuidando no saturarlos de emails, y medir el resultado contra un
    grupo sin contactar.

    **Preguntas para discutir en equipo:**
    1. ¿Están de acuerdo con el orden de las reglas? ¿Cambiarían alguna?
    2. ¿Qué dato nuevo les gustaría tener para decidir mejor?
    3. ¿Qué harían si después de 30 días el grupo contactado compra igual que el de comparación?
    """)

    st.warning(
        "Recordatorio: son **datos de práctica**. Este plan muestra el proceso de "
        "decisión, no una recomendación real para GM."
    )
