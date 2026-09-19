"""
app.py

Interfaz del agente: chat a la izquierda, consola "detrás de escena"
a la derecha con el SQL exacto que se generó y ejecutó para cada
pregunta.

Correr desde la raíz del repo:
    streamlit run app.py
"""

import os

import streamlit as st

from agent_core.agent import responder_pregunta
from agent_core.config import SQL_DIALECT
from agent_core.interpreter import interpretar_resultado
from agent_core.schema import build_schema_context

st.set_page_config(page_title="Agente Analítico Text-to-SQL", layout="wide")

PREGUNTAS_DE_EJEMPLO = [
    "¿Cuántos clientes grandes tenemos en el rubro Fintech?",
    "¿Cuál es el monto total pagado por cada tipo de servicio?",
    "¿Qué porcentaje de los pagos están en estado fallido?",
]


@st.cache_resource(show_spinner="Leyendo el esquema de la base...")
def _esquema() -> str:
    return build_schema_context()


if "chat" not in st.session_state:
    st.session_state.chat = []  # [{"role": "user"|"assistant", "content": str}]
if "consola" not in st.session_state:
    st.session_state.consola = []  # eventos con el SQL de cada pregunta
if "pregunta_pendiente" not in st.session_state:
    st.session_state.pregunta_pendiente = None


with st.sidebar:
    st.subheader("Estado")
    st.caption(f"Base conectada: **{SQL_DIALECT}**")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        st.warning("Falta ANTHROPIC_API_KEY en tu .env — el agente no va a poder responder todavía.")

    st.subheader("Preguntas de ejemplo")
    for ejemplo in PREGUNTAS_DE_EJEMPLO:
        if st.button(ejemplo, width="stretch"):
            st.session_state.pregunta_pendiente = ejemplo

    st.divider()
    if st.button("🗑️ Nueva conversación", width="stretch"):
        st.session_state.chat = []
        st.session_state.consola = []
        st.rerun()


col_chat, col_consola = st.columns([3, 2])

with col_chat:
    st.title("💬 Preguntale a tus datos")
    st.caption("Agente analítico sobre una base B2B de servicios digitales.")

    for mensaje in st.session_state.chat:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    pregunta = st.chat_input("Escribí tu pregunta...") or st.session_state.pregunta_pendiente
    st.session_state.pregunta_pendiente = None

    if pregunta:
        st.session_state.chat.append({"role": "user", "content": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)

        with st.chat_message("assistant"):
            try:
                with st.spinner("Generando y ejecutando la consulta..."):
                    sql, resultado, intentos, se_corrigio = responder_pregunta(pregunta, _esquema())
            except Exception as e:
                error_texto = (
                    "No pude generar una consulta que se ejecutara correctamente para esa "
                    f"pregunta. Detalle técnico: {e}"
                )
                st.markdown(error_texto)
                st.session_state.chat.append({"role": "assistant", "content": error_texto})
                st.session_state.consola.append({
                    "pregunta": pregunta, "sql": None, "intentos": None,
                    "se_corrigio": None, "filas": None, "error": str(e),
                })
            else:
                with st.spinner("Interpretando el resultado..."):
                    explicacion = interpretar_resultado(pregunta, sql, resultado)

                st.markdown(explicacion)
                with st.expander("Ver tabla de resultados"):
                    st.dataframe(resultado, width="stretch")

                st.session_state.chat.append({"role": "assistant", "content": explicacion})
                st.session_state.consola.append({
                    "pregunta": pregunta, "sql": sql, "intentos": intentos,
                    "se_corrigio": se_corrigio, "filas": len(resultado), "error": None,
                })

with col_consola:
    st.subheader("🔍 Detrás de escena")
    st.caption("El SQL exacto que generó y ejecutó el agente para cada pregunta.")

    if not st.session_state.consola:
        st.info("Todavía no hiciste ninguna pregunta.")

    for i, evento in enumerate(reversed(st.session_state.consola)):
        with st.expander(evento["pregunta"], expanded=(i == 0)):
            if evento["error"]:
                st.error(f"No se pudo ejecutar: {evento['error']}")
                continue

            st.code(evento["sql"], language="sql")

            etiquetas = f"{evento['filas']} fila" if evento["filas"] == 1 else f"{evento['filas']} filas"
            if evento["se_corrigio"]:
                etiquetas += f" · ⚠️ se autocorrigió (intento {evento['intentos']})"
            st.caption(etiquetas)
