"""
Genera una base de datos SQLite sintética que simula una empresa B2B
de servicios digitales (hosting, dominios, seguridad, email).

Uso (desde la raíz del repo):
    python -m data_generation.generate_db
"""

import random
from datetime import datetime, timedelta

from faker import Faker
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker

from agent_core.config import DEFAULT_DEMO_DB

DB_PATH = DEFAULT_DEMO_DB
N_CLIENTES = 150
N_PAGOS_POR_CLIENTE = (3, 24)  # rango de pagos históricos por cliente

fake = Faker("es_AR")
Faker.seed(42)
random.seed(42)

Base = declarative_base()


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True)
    nombre_empresa = Column(String, nullable=False)
    tamano_empresa = Column(String, nullable=False)  # Pyme / Mediana / Grande
    industria = Column(String, nullable=False)
    fecha_alta = Column(Date, nullable=False)
    email_contacto = Column(String, nullable=False)


class Servicio(Base):
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # hosting / dominio / seguridad / email
    precio_mensual = Column(Float, nullable=False)


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    servicio_id = Column(Integer, ForeignKey("servicios.id"), nullable=False)
    fecha_pago = Column(Date, nullable=False)
    monto = Column(Float, nullable=False)
    estado = Column(String, nullable=False)  # completado / fallido / pendiente
    pasarela = Column(String, nullable=False)  # transferencia / tarjeta / pasarela_automatica


TAMANOS = ["Pyme", "Mediana", "Grande"]
INDUSTRIAS = [
    "E-commerce", "Fintech", "Salud", "Educación", "Logística",
    "Turismo", "Retail", "Manufactura",
]
TIPOS_SERVICIO = {
    "Hosting Básico": ("hosting", 15.0),
    "Hosting Pro": ("hosting", 45.0),
    "Hosting Enterprise": ("hosting", 120.0),
    "Registro de Dominio": ("dominio", 12.0),
    "Certificado SSL": ("seguridad", 8.0),
    "Email Corporativo": ("email", 6.0),
    "Backup Automático": ("seguridad", 10.0),
}
ESTADOS_PAGO = ["completado"] * 8 + ["fallido"] + ["pendiente"]  # ~80/10/10
PASARELAS = ["transferencia", "tarjeta", "pasarela_automatica"]


def generar_clientes(n):
    clientes = []
    for _ in range(n):
        clientes.append(
            Cliente(
                nombre_empresa=fake.company(),
                tamano_empresa=random.choice(TAMANOS),
                industria=random.choice(INDUSTRIAS),
                fecha_alta=fake.date_between(start_date="-3y", end_date="-1M"),
                email_contacto=fake.company_email(),
            )
        )
    return clientes


def generar_servicios():
    return [
        Servicio(nombre=nombre, tipo=tipo, precio_mensual=precio)
        for nombre, (tipo, precio) in TIPOS_SERVICIO.items()
    ]


def generar_pagos(clientes, servicios):
    pagos = []
    hoy = datetime.now().date()
    for cliente in clientes:
        n_pagos = random.randint(*N_PAGOS_POR_CLIENTE)
        servicio = random.choice(servicios)
        fecha = cliente.fecha_alta
        for _ in range(n_pagos):
            if fecha > hoy:
                break
            variacion = servicio.precio_mensual * random.uniform(-0.05, 0.05)
            pagos.append(
                Pago(
                    cliente_id=cliente.id,
                    servicio_id=servicio.id,
                    fecha_pago=fecha,
                    monto=round(servicio.precio_mensual + variacion, 2),
                    estado=random.choice(ESTADOS_PAGO),
                    pasarela=random.choice(PASARELAS),
                )
            )
            fecha = fecha + timedelta(days=30)
    return pagos


def main():
    engine = create_engine(DB_PATH, echo=False)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    servicios = generar_servicios()
    session.add_all(servicios)
    session.commit()  # necesitamos los ids de servicios generados

    clientes = generar_clientes(N_CLIENTES)
    session.add_all(clientes)
    session.commit()  # necesitamos los ids de clientes generados

    pagos = generar_pagos(clientes, servicios)
    session.add_all(pagos)
    session.commit()

    print(f"Base generada: {len(clientes)} clientes, {len(servicios)} servicios, {len(pagos)} pagos")
    session.close()


if __name__ == "__main__":
    main()
