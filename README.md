# 🛡️ script-auditoria-preventiva

Herramienta de auditoría y validación previa de facturación, diseñada específicamente para el área de **Mecanismo de Integración** (Ley 24.901 / SSSalud).

---

### ⚠️ El Problema
En el circuito tradicional, la presentación de expedientes ante el portal FTP de la **SSSalud** presenta grandes demoras operativas:
* Las devoluciones de errores generales (`DEV.ERR`) suelen demorar horas.
* Los cruces de validación fiscal con **AFIP** (`WS.ERR`) y las proyecciones de subsidios (`DS.SUBSIDIOS`) recién se conocen **al cierre de la presentación**, cuando ya no hay margen de tiempo para realizar correcciones, lo que deriva en rechazos, pérdidas económicas o demoras críticas.

---

### 💡 La Solución
Este script actúa como un **auditor preventivo local**. Permite procesar y auditar los archivos antes de subirlos al FTP oficial, ofreciendo tres instancias de control configurables según la necesidad del operador:

1. **`DS.DEVERR` (Control de Errores Generales):**
   * Analiza la estructura de los datos cargados en busca de inconsistencias formales (cantidades o prestaciones incompatibles, duplicidad en los registros, etc.).
2. **`DS_WS.DEVERR` (Cruce con AFIP):**
   * Realiza un cruce automatizado contra los Libros de IVA digitales, verificando que las facturas a presentar se encuentren debidamente declaradas y validadas en AFIP.
3. **`DS.SUBSIDIOS` (Proyección y Tope de Subsidios):**
   * Cruza la información contra bases de datos actualizadas con los valores del nomenclador nacional, proyectando los montos de subsidios que otorgará la SSSalud para cada prestación.

---

### 📈 Impacto Operativo
* **Cero sorpresas al cierre:** Detecta y permite corregir errores de forma anticipada antes de la presentación formal.
* **Reducción de costos y tiempos:** Ahorra horas de revisión manual y evita el rechazo de lotes enteros por inconsistencias evitables.
* **Previsibilidad financiera:** Asegura que cada expediente ingrese saneado, optimizando el circuito de cobros y reintegros.

---

### 🛠️ Tecnologías
* **Python** (Procesamiento de datos, lógica de validación y manejo de archivos).
