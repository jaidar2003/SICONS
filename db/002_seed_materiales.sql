BEGIN;

INSERT INTO materiales (nombre, categoria, marca, unidad_base, descripcion)
VALUES
    ('Cemento Portland', 'Materiales de obra', 'Holcim', 'kg', 'Cemento de uso general para construccion'),
    ('Pastina 6 kg', 'Revestimientos', 'Klaukol', 'kg', 'Pastina para juntas de revestimientos'),
    ('Cano PVC 20 mm x 3 m', 'Instalaciones sanitarias', 'Generica', 'metro', 'Cano de PVC de 20 mm en tramo comercial')
ON CONFLICT (nombre, unidad_base, marca) DO NOTHING;

INSERT INTO presentaciones (material_id, nombre_presentacion, cantidad_base, unidad_presentacion)
SELECT id, 'Bolsa 50 kg', 50, 'bolsa'
FROM materiales
WHERE nombre = 'Cemento Portland'
ON CONFLICT (material_id, nombre_presentacion) DO NOTHING;

INSERT INTO presentaciones (material_id, nombre_presentacion, cantidad_base, unidad_presentacion)
SELECT id, 'Bolsa 25 kg', 25, 'bolsa'
FROM materiales
WHERE nombre = 'Cemento Portland'
ON CONFLICT (material_id, nombre_presentacion) DO NOTHING;

INSERT INTO presentaciones (material_id, nombre_presentacion, cantidad_base, unidad_presentacion)
SELECT id, 'Unidad 6 kg', 6, 'unidad'
FROM materiales
WHERE nombre = 'Pastina 6 kg'
ON CONFLICT (material_id, nombre_presentacion) DO NOTHING;

INSERT INTO presentaciones (material_id, nombre_presentacion, cantidad_base, unidad_presentacion)
SELECT id, 'Cano 3 m', 3, 'unidad'
FROM materiales
WHERE nombre = 'Cano PVC 20 mm x 3 m'
ON CONFLICT (material_id, nombre_presentacion) DO NOTHING;

INSERT INTO fuentes (nombre, tipo_fuente, descripcion)
VALUES
    ('Factura corralon propio', 'factura', 'Comprobantes cargados desde compras propias'),
    ('Lista de precios proveedor', 'lista_precios', 'Listas comerciales informadas por proveedores'),
    ('Relevamiento manual', 'manual', 'Carga manual tomada de comercios o presupuestos')
ON CONFLICT (nombre) DO NOTHING;

INSERT INTO precios_historicos (
    material_id,
    presentacion_id,
    fuente_id,
    fecha,
    precio_original,
    precio_normalizado,
    moneda,
    observaciones
)
SELECT
    m.id,
    p.id,
    f.id,
    DATE '2025-06-01',
    10000,
    200,
    'ARS',
    'Ejemplo: bolsa de cemento 50 kg'
FROM materiales m
JOIN presentaciones p ON p.material_id = m.id AND p.nombre_presentacion = 'Bolsa 50 kg'
JOIN fuentes f ON f.nombre = 'Factura corralon propio'
WHERE m.nombre = 'Cemento Portland'
ON CONFLICT (material_id, presentacion_id, fecha, fuente_id) DO NOTHING;

INSERT INTO precios_historicos (
    material_id,
    presentacion_id,
    fuente_id,
    fecha,
    precio_original,
    precio_normalizado,
    moneda,
    observaciones
)
SELECT
    m.id,
    p.id,
    f.id,
    DATE '2025-09-01',
    5500,
    220,
    'ARS',
    'Ejemplo: bolsa de cemento 25 kg'
FROM materiales m
JOIN presentaciones p ON p.material_id = m.id AND p.nombre_presentacion = 'Bolsa 25 kg'
JOIN fuentes f ON f.nombre = 'Factura corralon propio'
WHERE m.nombre = 'Cemento Portland'
ON CONFLICT (material_id, presentacion_id, fecha, fuente_id) DO NOTHING;

INSERT INTO precios_historicos (
    material_id,
    presentacion_id,
    fuente_id,
    fecha,
    precio_original,
    precio_normalizado,
    moneda,
    observaciones
)
SELECT
    m.id,
    p.id,
    f.id,
    DATE '2025-09-15',
    4200,
    700,
    'ARS',
    'Ejemplo: unidad de pastina 6 kg'
FROM materiales m
JOIN presentaciones p ON p.material_id = m.id AND p.nombre_presentacion = 'Unidad 6 kg'
JOIN fuentes f ON f.nombre = 'Lista de precios proveedor'
WHERE m.nombre = 'Pastina 6 kg'
ON CONFLICT (material_id, presentacion_id, fecha, fuente_id) DO NOTHING;

INSERT INTO precios_historicos (
    material_id,
    presentacion_id,
    fuente_id,
    fecha,
    precio_original,
    precio_normalizado,
    moneda,
    observaciones
)
SELECT
    m.id,
    p.id,
    f.id,
    DATE '2025-10-01',
    3600,
    1200,
    'ARS',
    'Ejemplo: cano de 3 metros normalizado por metro'
FROM materiales m
JOIN presentaciones p ON p.material_id = m.id AND p.nombre_presentacion = 'Cano 3 m'
JOIN fuentes f ON f.nombre = 'Relevamiento manual'
WHERE m.nombre = 'Cano PVC 20 mm x 3 m'
ON CONFLICT (material_id, presentacion_id, fecha, fuente_id) DO NOTHING;

COMMIT;
