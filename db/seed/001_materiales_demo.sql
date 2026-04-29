BEGIN;

INSERT INTO materiales (nombre, categoria, marca, unidad_base, descripcion)
VALUES
    ('Cemento Portland', 'Materiales de obra', 'Holcim', 'kg', 'Cemento de uso general para construccion')
ON CONFLICT (nombre, unidad_base, marca) DO NOTHING;

INSERT INTO fuentes (nombre, tipo_fuente, descripcion)
VALUES
    ('Factura compra', 'factura', 'Comprobantes cargados desde compras propias'),
    ('Lista de precios proveedor', 'lista_precios', 'Listas comerciales informadas por proveedores'),
    ('Relevamiento manual', 'manual', 'Carga manual tomada de comercios o presupuestos')
ON CONFLICT (nombre) DO NOTHING;

COMMIT;
