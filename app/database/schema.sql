-- Función para actualizar el campo updated_at
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- LIMPIAR TABLAS PROBLEMÁTICAS ANTES DE RECREAR
DROP TABLE IF EXISTS solution_types CASCADE;
DROP TABLE IF EXISTS file_metadata CASCADE;
DROP TABLE IF EXISTS differences_metadata CASCADE;
DROP TABLE IF EXISTS solutions CASCADE;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS vehicle_info (
    id SERIAL PRIMARY KEY,
    vehicle_type TEXT NOT NULL,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    engine TEXT NOT NULL,
    year INT NOT NULL,
    hardware_number TEXT NOT NULL,
    software_number TEXT NOT NULL,
    software_update_number TEXT,
    ecu_type TEXT,
    transmission_type TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS field_dependencies (
    id SERIAL PRIMARY KEY,
    parent_field TEXT NOT NULL,
    child_field TEXT NOT NULL,
    UNIQUE(parent_field, child_field)
);

CREATE TABLE IF NOT EXISTS field_values (
    id SERIAL PRIMARY KEY,
    field_name TEXT NOT NULL,
    field_value TEXT NOT NULL,
    parent_field TEXT,
    parent_value TEXT,
    UNIQUE(field_name, field_value, parent_field, parent_value)
);

-- CAMBIO PRINCIPAL: solutions ahora usa SERIAL en lugar de UUID
CREATE TABLE solutions (
    id SERIAL PRIMARY KEY,
    vehicle_info_id INTEGER NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vehicle_info_id) REFERENCES vehicle_info(id) ON DELETE CASCADE
);

-- CAMBIO: solution_id ahora es INTEGER
CREATE TABLE solution_types (
    id SERIAL PRIMARY KEY,
    solution_id INTEGER UNIQUE NOT NULL,
    stage_1 BOOLEAN DEFAULT FALSE,
    stage_2 BOOLEAN DEFAULT FALSE,
    pop_and_bangs BOOLEAN DEFAULT FALSE,
    vmax BOOLEAN DEFAULT FALSE,
    dtc_off BOOLEAN DEFAULT FALSE,
    full_decat BOOLEAN DEFAULT FALSE,
    immo_off BOOLEAN DEFAULT FALSE,
    evap_off BOOLEAN DEFAULT FALSE,
    tva BOOLEAN DEFAULT FALSE,
    egr_off BOOLEAN DEFAULT FALSE,
    dpf_off BOOLEAN DEFAULT FALSE,
    egr_dpf_off BOOLEAN DEFAULT FALSE,
    adblue_off BOOLEAN DEFAULT FALSE,
    egr_dpf_adblue_off BOOLEAN DEFAULT FALSE,
    description TEXT,
    FOREIGN KEY (solution_id) REFERENCES solutions(id) ON DELETE CASCADE
);

-- CAMBIO: solution_id ahora es INTEGER
CREATE TABLE file_metadata (
    id SERIAL PRIMARY KEY,
    solution_id INTEGER NOT NULL,
    file_type VARCHAR(10) NOT NULL, -- 'ori1', 'ori2', 'mod1', 'mod2'
    file_name VARCHAR(255) NOT NULL,
    file_size INTEGER NOT NULL,
    s3_key VARCHAR(500) NOT NULL, -- Ruta en S3
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solution_id) REFERENCES solutions(id) ON DELETE CASCADE,
    UNIQUE(solution_id, file_type)
);

-- CAMBIO: solution_id ahora es INTEGER
CREATE TABLE differences_metadata (
    id SERIAL PRIMARY KEY,
    solution_id INTEGER NOT NULL,
    total_differences INTEGER NOT NULL,
    s3_key VARCHAR(500) NOT NULL, -- Ruta del JSON en S3
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (solution_id) REFERENCES solutions(id) ON DELETE CASCADE,
    UNIQUE(solution_id)
);

-- ELIMINAR TABLAS DE ALMACENAMIENTO DE ARCHIVOS (si existen)
DROP TABLE IF EXISTS file_differences;
DROP TABLE IF EXISTS file_storage;
DROP TABLE IF EXISTS ori1_files;

-- Índices para las nuevas tablas de metadatos
CREATE INDEX IF NOT EXISTS idx_file_metadata_solution ON file_metadata(solution_id);
CREATE INDEX IF NOT EXISTS idx_file_metadata_solution_type ON file_metadata(solution_id, file_type);
CREATE INDEX IF NOT EXISTS idx_differences_metadata_solution ON differences_metadata(solution_id);

-- Eliminar triggers existentes antes de recrear
DROP TRIGGER IF EXISTS update_users_timestamp ON users;
DROP TRIGGER IF EXISTS update_vehicle_info_timestamp ON vehicle_info;
DROP TRIGGER IF EXISTS update_solutions_timestamp ON solutions;
DROP TRIGGER IF EXISTS update_solution_types_timestamp ON solution_types;

-- Triggers para actualizar updated_at
CREATE TRIGGER update_users_timestamp
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_vehicle_info_timestamp
    BEFORE UPDATE ON vehicle_info
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_solutions_timestamp
    BEFORE UPDATE ON solutions
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER update_solution_types_timestamp
    BEFORE UPDATE ON solution_types
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Datos iniciales
INSERT INTO field_dependencies (parent_field, child_field)
VALUES
    ('vehicle_type', 'make'),
    ('make', 'model'),
    ('model', 'engine'),
    ('model', 'year'),
    ('model', 'transmission_type'),
    ('model', 'ecu_type'),
    ('engine', 'hardware_number'),
    ('hardware_number', 'software_number'),
    ('software_number', 'software_update_number'),
    ('model', 'hardware_number'),
    ('model', 'software_number'),
    ('model', 'software_update_number')
ON CONFLICT DO NOTHING;

INSERT INTO field_values (field_name, field_value, parent_field, parent_value)
VALUES
    ('vehicle_type', 'SUV', NULL, NULL),
    ('vehicle_type', 'Car', NULL, NULL),

    ('make', 'TestMake', 'vehicle_type', 'SUV'),
    ('make', 'Toyota', 'vehicle_type', 'Car'),

    ('model', 'TestModel_8', 'make', 'TestMake'),
    ('model', 'TestModel_16', 'make', 'TestMake'),
    ('model', 'TestModel_32', 'make', 'TestMake'),
    ('model', 'Camry', 'make', 'Toyota'),

    ('engine', 'V6', 'model', 'TestModel_8'),
    ('engine', 'V6', 'model', 'TestModel_16'),
    ('engine', 'V6', 'model', 'TestModel_32'),
    ('engine', '2.5L', 'model', 'Camry'),

    ('year', '2023', 'model', 'TestModel_8'),
    ('year', '2024', 'model', 'TestModel_16'),
    ('year', '2025', 'model', 'TestModel_32'),
    ('year', '2022', 'model', 'Camry'),

    ('ecu_type', 'ECU_A', 'model', 'TestModel_8'),
    ('ecu_type', 'ECU_A', 'model', 'TestModel_16'),
    ('ecu_type', 'ECU_A', 'model', 'TestModel_32'),
    ('ecu_type', 'Type A', 'model', 'Camry'),

    ('transmission_type', 'AUTO', 'model', 'TestModel_8'),
    ('transmission_type', 'AUTO', 'model', 'TestModel_16'),
    ('transmission_type', 'AUTO', 'model', 'TestModel_32'),
    ('transmission_type', 'Automatic', 'model', 'Camry'),

    ('hardware_number', 'HW008', 'engine', 'V6'),
    ('hardware_number', 'HW016', 'engine', 'V6'),
    ('hardware_number', 'HW032', 'engine', 'V6'),
    ('hardware_number', 'HW008', 'model', 'TestModel_8'),
    ('hardware_number', 'HW016', 'model', 'TestModel_16'),
    ('hardware_number', 'HW032', 'model', 'TestModel_32'),
    ('hardware_number', 'HW002', 'engine', '2.5L'),

    ('software_number', 'SW008', 'hardware_number', 'HW008'),
    ('software_number', 'SW016', 'hardware_number', 'HW016'),
    ('software_number', 'SW032', 'hardware_number', 'HW032'),
    ('software_number', 'SW008', 'model', 'TestModel_8'),
    ('software_number', 'SW016', 'model', 'TestModel_16'),
    ('software_number', 'SW032', 'model', 'TestModel_32'),
    ('software_number', 'SW002', 'hardware_number', 'HW002'),

    ('software_update_number', 'SWU008', 'software_number', 'SW008'),
    ('software_update_number', 'SWU016', 'software_number', 'SW016'),
    ('software_update_number', 'SWU032', 'software_number', 'SW032'),
    ('software_update_number', 'SWU008', 'model', 'TestModel_8'),
    ('software_update_number', 'SWU016', 'model', 'TestModel_16'),
    ('software_update_number', 'SWU032', 'model', 'TestModel_32'),
    ('software_update_number', 'UPDATE001', 'software_number', 'SW002')
ON CONFLICT DO NOTHING;

-- Crear vehicle_info base para las foreign keys
INSERT INTO vehicle_info (id, vehicle_type, make, model, engine, year, hardware_number, software_number, ecu_type, transmission_type)
VALUES (1, 'Test', 'Test', 'Test', 'Test', 2023, 'TEST001', 'TEST001', 'Test', 'Test')
ON CONFLICT (id) DO NOTHING;
