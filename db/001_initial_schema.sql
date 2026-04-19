BEGIN;

CREATE TABLE materiales (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    categoria VARCHAR(100),
    marca VARCHAR(100),
    unidad_base VARCHAR(20) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT materiales_nombre_unidad_marca_unique UNIQUE (nombre, unidad_base, marca)
);

CREATE TABLE presentaciones (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_id BIGINT NOT NULL REFERENCES materiales(id) ON DELETE RESTRICT,
    nombre_presentacion VARCHAR(100) NOT NULL,
    cantidad_base NUMERIC(12,4) NOT NULL,
    unidad_presentacion VARCHAR(20) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT presentaciones_id_material_unique UNIQUE (id, material_id),
    CONSTRAINT presentaciones_cantidad_base_positive CHECK (cantidad_base > 0),
    CONSTRAINT presentaciones_material_nombre_unique UNIQUE (material_id, nombre_presentacion)
);

CREATE TABLE fuentes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL UNIQUE,
    tipo_fuente VARCHAR(50),
    descripcion TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE precios_historicos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    material_id BIGINT NOT NULL REFERENCES materiales(id) ON DELETE RESTRICT,
    presentacion_id BIGINT REFERENCES presentaciones(id) ON DELETE RESTRICT,
    fuente_id BIGINT REFERENCES fuentes(id) ON DELETE SET NULL,
    fecha DATE NOT NULL,
    precio_original NUMERIC(14,2) NOT NULL,
    precio_normalizado NUMERIC(14,4) NOT NULL,
    moneda VARCHAR(10) NOT NULL DEFAULT 'ARS',
    observaciones TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT precios_historicos_presentacion_material_fk
        FOREIGN KEY (presentacion_id, material_id)
        REFERENCES presentaciones(id, material_id)
        ON DELETE RESTRICT,
    CONSTRAINT precios_historicos_material_presentacion_fecha_fuente_unique
        UNIQUE (material_id, presentacion_id, fecha, fuente_id),
    CONSTRAINT precios_historicos_precio_original_nonnegative CHECK (precio_original >= 0),
    CONSTRAINT precios_historicos_precio_normalizado_nonnegative CHECK (precio_normalizado >= 0),
    CONSTRAINT precios_historicos_moneda_not_blank CHECK (btrim(moneda) <> '')
);

CREATE INDEX idx_presentaciones_material_id
    ON presentaciones(material_id);

CREATE INDEX idx_precios_historicos_material_fecha
    ON precios_historicos(material_id, fecha DESC);

CREATE INDEX idx_precios_historicos_presentacion_id
    ON precios_historicos(presentacion_id);

CREATE INDEX idx_precios_historicos_fuente_id
    ON precios_historicos(fuente_id);

CREATE INDEX idx_precios_historicos_fecha
    ON precios_historicos(fecha DESC);

COMMIT;
