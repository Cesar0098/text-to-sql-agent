"""
data_generation/glosario_demo.py

Ejemplo de glosario opcional para enriquecer el esquema de la base de
demo con contexto de negocio que el inspector de SQLAlchemy no puede
inferir. Es opcional: build_schema_context() funciona perfectamente
sin esto, pasándole `glosario=None`.

Uso:
    from agent_core.schema import build_schema_context
    from data_generation.glosario_demo import GLOSARIO

    esquema = build_schema_context(glosario=GLOSARIO)
"""

GLOSARIO = {
    "clientes": "Empresas que contratan servicios digitales.",
    "servicios": "Catálogo de planes que se pueden contratar.",
    "pagos": "Historial de transacciones asociadas a un cliente y un servicio.",
    ("clientes", "fecha_alta"): "Fecha en la que el cliente empezó a operar con nosotros.",
    ("servicios", "precio_mensual"): "Precio de lista mensual, en USD.",
    ("pagos", "estado"): "Resultado de la transacción.",
    ("pagos", "pasarela"): "Medio por el cual se procesó el pago.",
}
