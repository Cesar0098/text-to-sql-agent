"""
agent_core/interpreter.py

Toma el resultado crudo de una consulta y lo convierte en una
explicación de negocio: qué significa, qué tendencia destaca y qué
hacer con esa información (ver prompts/interpretar_resultado.txt).
"""

from pathlib import Path

import pandas as pd

from agent_core.text_to_sql import MODEL, client

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "interpretar_resultado.txt"


def _resumen_estadistico(resultado: pd.DataFrame) -> str:
    """Agregaciones simples sobre las columnas numéricas, si las hay."""
    numericas = resultado.select_dtypes(include="number")
    if numericas.empty:
        return "(sin columnas numéricas para resumir)"
    return numericas.describe().round(2).to_string()


def interpretar_resultado(pregunta: str, sql: str, resultado: pd.DataFrame) -> str:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    tabla = resultado.to_markdown(index=False) if not resultado.empty else "(sin filas)"
    estadisticas = _resumen_estadistico(resultado)

    contenido_usuario = (
        f"Pregunta original: {pregunta}\n\n"
        f"Consulta SQL ejecutada:\n{sql}\n\n"
        f"Resultado ({len(resultado)} filas):\n{tabla}\n\n"
        f"Resumen estadístico de columnas numéricas:\n{estadisticas}"
    )

    respuesta = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=system_prompt,
        messages=[{"role": "user", "content": contenido_usuario}],
    )
    return respuesta.content[0].text.strip()


if __name__ == "__main__":
    from agent_core.agent import responder_pregunta
    from agent_core.schema import build_schema_context

    esquema = build_schema_context()
    pregunta = "¿Cuál es el monto total pagado por cada tipo de servicio?"
    sql, resultado, intentos, se_corrigio = responder_pregunta(pregunta, esquema)
    explicacion = interpretar_resultado(pregunta, sql, resultado)

    print(f"SQL: {sql}\n")
    print(resultado.to_string(index=False))
    print(f"\nInterpretación:\n{explicacion}")
