"""
agent_core/text_to_sql.py

Convierte una pregunta en lenguaje natural en una consulta SQL,
usando el esquema real de la base y un system prompt de consultor
analítico (ver prompts/generar_sql.txt).
"""

import re
from pathlib import Path

import anthropic

from agent_core.config import SQL_DIALECT

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "generar_sql.txt"
MODEL = "claude-sonnet-4-6"

# Toma la API key de la variable de entorno ANTHROPIC_API_KEY
client = anthropic.Anthropic()


def _limpiar_sql(texto: str) -> str:
    """Por si el modelo igual devuelve un bloque ```sql ... ``` a pesar de la regla 4."""
    texto = texto.strip()
    texto = re.sub(r"^```sql\s*|^```\s*|```$", "", texto, flags=re.MULTILINE).strip()
    return texto


def generar_consulta_sql(pregunta: str, schema_context: str) -> str:
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").format(
        schema=schema_context, dialecto=SQL_DIALECT
    )

    respuesta = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system_prompt,
        messages=[{"role": "user", "content": pregunta}],
    )
    return _limpiar_sql(respuesta.content[0].text)


if __name__ == "__main__":
    from agent_core.schema import build_schema_context  # ajustar el import según ubiques schema.py

    esquema = build_schema_context()
    pregunta = "¿Cuántos clientes grandes tenemos en el rubro Fintech?"
    print(generar_consulta_sql(pregunta, esquema))
