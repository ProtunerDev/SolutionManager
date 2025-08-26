# 📊 ANÁLISIS DE ALMACENAMIENTO - BASE DE DATOS vs S3

## 🏗️ ARQUITECTURA ACTUAL

Tu aplicación SolutionManager usa una **arquitectura híbrida** con:
- **PostgreSQL** (Railway) para metadatos y configuraciones
- **AWS S3** para archivos binarios y datos grandes

---

## 📂 QUÉ SE GUARDA EN LA BASE DE DATOS (PostgreSQL)

### 🚗 **Tabla: `vehicle_info`**
```sql
- id (SERIAL) - ID único del vehículo
- vehicle_type (TEXT) - Tipo: SUV, Car, etc.
- make (TEXT) - Marca: Toyota, BMW, etc.
- model (TEXT) - Modelo del vehículo
- engine (TEXT) - Tipo de motor
- year (INT) - Año del vehículo
- hardware_number (TEXT) - Número de hardware ECU
- software_number (TEXT) - Número de software ECU
- software_update_number (TEXT) - Versión del software
- ecu_type (TEXT) - Tipo de ECU
- transmission_type (TEXT) - Tipo de transmisión
- created_at, updated_at (TIMESTAMP)
```

### 🔧 **Tabla: `solutions`**
```sql
- id (SERIAL) - ID único de la solución
- vehicle_info_id (INTEGER) - FK a vehicle_info
- description (TEXT) - Descripción de la solución
- status (TEXT) - Estado: 'active', etc.
- created_at, updated_at (TIMESTAMP)
```

### ⚙️ **Tabla: `solution_types`**
```sql
- id (SERIAL) - ID único
- solution_id (INTEGER) - FK a solutions
- stage_1, stage_2 (BOOLEAN) - Etapas de modificación
- pop_and_bangs (BOOLEAN) - Pop and bangs activado
- vmax (BOOLEAN) - Limitador de velocidad removido
- dtc_off (BOOLEAN) - Códigos de error desactivados
- full_decat (BOOLEAN) - Descat completo
- immo_off (BOOLEAN) - Inmovilizador desactivado
- evap_off (BOOLEAN) - Sistema EVAP desactivado
- tva (BOOLEAN) - Ajuste de mariposa
- egr_off (BOOLEAN) - EGR desactivado
- dpf_off (BOOLEAN) - DPF desactivado
- egr_dpf_off (BOOLEAN) - EGR + DPF desactivados
- adblue_off (BOOLEAN) - AdBlue desactivado
- egr_dpf_adblue_off (BOOLEAN) - Todo desactivado
- description (TEXT) - Descripción adicional
```

### 📄 **Tabla: `file_metadata`**
```sql
- id (SERIAL) - ID único
- solution_id (INTEGER) - FK a solutions
- file_type (VARCHAR) - Tipo: 'ori1', 'ori2', 'mod1', 'mod2'
- file_name (VARCHAR) - Nombre original del archivo
- file_size (INTEGER) - Tamaño en bytes
- s3_key (VARCHAR) - Ruta del archivo en S3
- uploaded_at (TIMESTAMP) - Fecha de subida
```

### 📊 **Tabla: `differences_metadata`**
```sql
- id (SERIAL) - ID único
- solution_id (INTEGER) - FK a solutions
- total_differences (INTEGER) - Número total de diferencias
- s3_key (VARCHAR) - Ruta del JSON de diferencias en S3
- created_at (TIMESTAMP) - Fecha de creación
```

### 🔗 **Tablas de Configuración:**
- `field_dependencies` - Dependencias entre campos (make→model→engine)
- `field_values` - Valores disponibles para cada campo
- `users` - (No utilizada actualmente, auth por Supabase)

---

## ☁️ QUÉ SE GUARDA EN S3 (AWS)

### 📂 **Estructura de Carpetas:**
```
solutionmanager-files/
├── solutions/
│   ├── {solution_id}/
│   │   ├── ori1/
│   │   │   └── archivo_original_1.bin
│   │   ├── ori2/
│   │   │   └── archivo_original_2.bin
│   │   ├── mod1/
│   │   │   └── archivo_modificado_1.bin
│   │   ├── mod2/
│   │   │   └── archivo_modificado_2.bin
│   │   └── differences/
│   │       └── differences.json
```

### 📁 **Tipos de Archivos en S3:**

#### 🔸 **Archivos Binarios (ECU)**
- **Ubicación**: `solutions/{solution_id}/{file_type}/`
- **Tipos**: ori1, ori2, mod1, mod2
- **Formato**: Archivos binarios (.bin, .hex, etc.)
- **Tamaño**: Generalmente 512KB - 2MB
- **Contenido**: Datos hexadecimales de ECU

#### 🔸 **Archivos de Diferencias**
- **Ubicación**: `solutions/{solution_id}/differences/differences.json`
- **Formato**: JSON
- **Contenido**:
```json
{
  "solution_id": 123,
  "total_differences": 1247,
  "differences": [
    {
      "offset": "0x1000",
      "ori1": "FF",
      "ori2": "FF", 
      "mod1": "00",
      "mod2": "00",
      "description": "Cambio en mapa de combustible"
    }
  ],
  "created_at": "2025-08-25T10:30:00Z"
}
```

---

## 🔄 FLUJO DE ALMACENAMIENTO

### **Al crear una nueva solución:**

1. **Base de Datos**:
   ```
   vehicle_info → solution → solution_types
   ```

2. **S3**: 
   ```
   archivos binarios → carpetas por tipo
   ```

3. **Al comparar archivos**:
   ```
   Base de Datos: differences_metadata
   S3: differences.json con datos completos
   ```

---

## ⚙️ CONFIGURACIÓN ACTUAL

### 🔧 **Storage Type**: `s3` (configurado en .env)
### 🗄️ **Bucket S3**: `solutionmanager-files`
### 🌍 **Región**: `us-east-1`
### 🏛️ **Base de Datos**: PostgreSQL en Railway

---

## 📈 **VENTAJAS DE ESTA ARQUITECTURA**

✅ **PostgreSQL (Metadatos)**:
- Búsquedas rápidas por filtros
- Integridad referencial
- Transacciones ACID
- Reportes y estadísticas

✅ **S3 (Archivos)**:
- Almacenamiento ilimitado
- Alta disponibilidad
- Costo eficiente
- CDN global

---

## 📊 **RESUMEN DE DISTRIBUCIÓN**

| **Tipo de Dato** | **Almacenamiento** | **Tamaño Aprox** |
|------------------|-------------------|------------------|
| Configuraciones vehículo | PostgreSQL | < 1KB |
| Metadatos soluciones | PostgreSQL | < 1KB |
| Archivos binarios ECU | S3 | 512KB - 2MB |
| Diferencias detalladas | S3 | 10KB - 100KB |
| Índices de diferencias | PostgreSQL | < 1KB |

**Total por solución**: ~2-4MB en S3 + ~3KB en PostgreSQL
