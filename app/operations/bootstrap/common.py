from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.auth.infrastructure.models import Usuario
from app.modules.catalog.infrastructure.models import Fuente, Material, Presentacion
from app.modules.pricing.infrastructure.models import PrecioHistorico  # noqa: F401
from app.shared.security.tokens import hash_password, verify_password


def get_or_create_material(
    db: Session,
    *,
    nombre: str,
    categoria: str,
    marca: str,
    unidad_base: str,
    descripcion: str,
) -> Material:
    material = db.scalar(
        select(Material).where(
            Material.nombre == nombre,
            Material.unidad_base == unidad_base,
            Material.marca == marca,
        )
    )
    if material is not None:
        return material

    material = Material(
        nombre=nombre,
        categoria=categoria,
        marca=marca,
        unidad_base=unidad_base,
        descripcion=descripcion,
        activo=True,
    )
    db.add(material)
    db.flush()
    return material


def get_or_create_presentacion(
    db: Session,
    *,
    material: Material,
    nombre_presentacion: str,
    cantidad_base: Decimal,
    unidad_presentacion: str,
) -> Presentacion:
    presentacion = db.scalar(
        select(Presentacion).where(
            Presentacion.material_id == material.id,
            Presentacion.nombre_presentacion == nombre_presentacion,
        )
    )
    if presentacion is not None:
        return presentacion

    presentacion = Presentacion(
        material_id=material.id,
        nombre_presentacion=nombre_presentacion,
        cantidad_base=cantidad_base,
        unidad_presentacion=unidad_presentacion,
        activa=True,
    )
    db.add(presentacion)
    db.flush()
    return presentacion


def get_or_create_fuente(db: Session, *, nombre: str, tipo_fuente: str, descripcion: str) -> Fuente:
    fuente = db.scalar(select(Fuente).where(Fuente.nombre == nombre))
    if fuente is not None:
        return fuente

    fuente = Fuente(nombre=nombre, tipo_fuente=tipo_fuente, descripcion=descripcion)
    db.add(fuente)
    db.flush()
    return fuente


def get_or_create_usuario(db: Session, *, username: str, nombre: str, password: str, rol: str) -> Usuario:
    usuario = db.scalar(select(Usuario).where(Usuario.username == username))
    if usuario is not None:
        usuario.nombre = nombre
        usuario.rol = rol
        usuario.activo = True
        if not verify_password(password, usuario.password_hash):
            usuario.password_hash = hash_password(password)
        return usuario

    usuario = Usuario(
        username=username,
        nombre=nombre,
        password_hash=hash_password(password),
        rol=rol,
        activo=True,
    )
    db.add(usuario)
    db.flush()
    return usuario
