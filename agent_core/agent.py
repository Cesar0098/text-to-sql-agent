"""
agent_core/agent.py

Orquesta el flujo completo: genera SQL, lo ejecuta, y si la base
devuelve un error, se lo pasa de vuelta al modelo para que corrija su
propia consulta (self-healing) sin que el usuario se entere.
"""

from agent_core.config import SQL_DIALECT
from agent_core.executor import ejecutar_consulta
from agent_core.text_to_sql import PROMPT_PATH, MODEL, client, _limpiar_sql

MAX_INTENTOS = 2  # intento inicial + 1 reintento de autocorrección


def _system_prompt(schema_context: str) -> str:
    return PROMPT_PATH.read_text(encoding="utf-8").format(
        schema=schema_context, dialecto=SQL_DIALECT
    )


def responder_pregunta(pregunta: str, schema_context: str):
    """
    Devuelve (sql_final, resultado, intentos, se_autocorrigio).
    Si ni el intento inicial ni la autocorrección funcionan, relanza
    el último error.
    """
    system_prompt = _system_prompt(schema_context)
    mensajes = [{"role": "user", "content": pregunta}]

    ultimo_error = None
    for intento in range(1, MAX_INTENTOS + 1):
        respuesta = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=mensajes,
        )
        sql = _limpiar_sql(respuesta.content[0].text)
        mensajes.append({"role": "assistant", "content": sql})

        try:
            resultado = ejecutar_consulta(sql)
            return sql, resultado, intento, intento > 1
        except Exception as e:
            ultimo_error = e
            if intento < MAX_INTENTOS:
                mensajes.append({
                    "role": "user",
                    "content": (
                        f"Esa consulta falló al ejecutarse con este error:\n{e}\n\n"
                        "Corregí la consulta SQL. Devolvé SOLO el SQL corregido, "
                        "sin explicaciones ni bloques de markdown."
                    ),
                })

    raise ultimo_error


if __name__ == "__main__":
    from agent_core.schema import build_schema_context

    esquema = build_schema_context()
    sql, resultado, intentos, se_corrigio = responder_pregunta(
        "¿Cuántos clientes grandes tenemos en el rubro Fintech?", esquema
    )
    print(f"SQL final (intento {intentos}, autocorregido={se_corrigio}):\n{sql}")
    print(resultado.to_string(index=False))
