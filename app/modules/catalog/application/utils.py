import re
import unicodedata


def derive_material_key(nombre: str) -> str:
    """
    Deriva una clave estable (slug) a partir del nombre del material.
    Ej: 'Cemento Portland' -> 'cemento-portland'
    """
    n = nombre.strip().lower()
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode('ascii')
    n = re.sub(r'[^a-z0-9]+', '-', n)
    return n.strip('-')
