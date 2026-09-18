"""
probar_flujo.py

Prueba de punta a punta sin UI todavía: pregunta en lenguaje natural
-> esquema inyectado -> SQL generado -> ejecución segura -> resultado.

Correr desde la raíz del repo, con ANTHROPIC_API_KEY configurada en
el entorno:

    export ANTHROPIC_API_KEY="tu-api-key"
    python probar_flujo.py
"""

from agent_core.schema import build_schema_context
from agent_core.text_to_sql import generar_consulta_sql
from agent_core.executor import ejecutar_consulta, ConsultaNoPermitida

PREGUNTAS_DE_PRUEBA = [
    "¿Cuántos clientes grandes tenemos en el rubro Fintech?",
    "¿Cuál es el monto total pagado por cada tipo de servicio?",
    "¿Qué porcentaje de los pagos están en estado fallido?",
]


def main():
    esquema = build_schema_context()

    for pregunta in PREGUNTAS_DE_PRUEBA:
        print("=" * 70)
        print(f"Pregunta: {pregunta}")

        try:
            sql = generar_consulta_sql(pregunta, esquema)
        except Exception as e:
            print(f"No se pudo generar el SQL (¿configuraste ANTHROPIC_API_KEY?): {e}")
            continue

        print(f"SQL generado:\n  {sql}")

        try:
            resultado = ejecutar_consulta(sql)
            print("Resultado:")
            print(resultado.to_string(index=False))
        except ConsultaNoPermitida as e:
            print(f"Consulta bloqueada por seguridad: {e}")


if __name__ == "__main__":
    main()
