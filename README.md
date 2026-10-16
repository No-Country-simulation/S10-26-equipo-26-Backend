# PriceScope — Backend API

Backend de PriceScope, una plataforma B2B de monitoreo de precios e inflación real multimoneda.

Este repositorio expone una API REST para consultar precios históricos, tipos de cambio, indicadores de variación y alertas de posibles anomalías. También contiene la lógica de negocio y el componente analítico encargado de identificar movimientos inusuales en los precios.

## 1. Objetivo

Implementar el backend de un MVP que permita:

- Consultar productos, tiendas y precios históricos.
- Calcular variaciones de precios y tipos de cambio.
- Comparar la evolución de precios en una moneda de referencia.
- Generar indicadores por producto, tienda y categoría.
- Detectar posibles anomalías mediante métodos estadísticos.
- Exponer alertas y métricas al dashboard.
- Mantener resultados reproducibles y trazables.

El objetivo es demostrar un flujo completo desde la recolección de datos hasta la visualización de indicadores y alertas.

## 2. Alcance del MVP

### Incluido

- API REST documentada.
- Persistencia en PostgreSQL.
- Consultas históricas de precios.
- Cálculo de variaciones porcentuales.
- Integración con datos de tipos de cambio.
- Indicadores básicos de precios.
- Detección estadística de anomalías.
- Consulta de alertas.
- Validaciones y manejo de errores.
- Pruebas automatizadas.

### Fuera del alcance inicial

- Arquitectura de microservicios.
- Kafka y procesamiento distribuido.
- Predicción avanzada de inflación.
- Agentes autónomos de IA.
- Matching semántico avanzado de productos.
- Notificaciones externas.
- Cobertura de 10.000 productos y 15 tiendas.
- Infraestructura de producción de alta disponibilidad.

## 3. Stack tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | Python |
| Framework API | FastAPI |
| Validación | Pydantic |
| Base de datos | PostgreSQL |
| Acceso a datos | SQLAlchemy |
| Migraciones | Alembic |
| Análisis | Pandas / NumPy |
| Machine learning opcional | scikit-learn |
| Pruebas | Pytest |
| Documentación | OpenAPI / Swagger |

Las versiones definitivas de Python y las dependencias deben quedar fijadas en los archivos de configuración del proyecto.

## 4. Arquitectura

El backend se implementará como un **monolito modular**. Esto permite mantener una arquitectura sencilla para el MVP, separando las responsabilidades sin añadir servicios ni infraestructura innecesarios.

```text
backend/
├── src/
│   ├── main.py
│   ├── api/
│   │   ├── router.py
│   │   └── v1/
│   │       ├── products.py
│   │       ├── prices.py
│   │       ├── indicators.py
│   │       ├── exchange_rates.py
│   │       └── alerts.py
│   ├── core/
│   │   ├── config.py
│   │   └── exceptions.py
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── services/
│   │   ├── price_service.py
│   │   ├── indicator_service.py
│   │   ├── exchange_rate_service.py
│   │   └── anomaly_service.py
│   └── analytics/
│       ├── inflation.py
│       └── anomaly_detection.py
├── tests/
├── migrations/
├── .env.example
├── requirements.txt
└── README.md
```

La estructura es una propuesta inicial y puede ajustarse al código existente.

### Responsabilidades

- **API:** maneja las solicitudes HTTP, parámetros y respuestas.
- **Schemas:** define y valida los contratos de entrada y salida.
- **Services:** implementa los casos de uso y coordina las operaciones.
- **Repositories:** encapsula las consultas a PostgreSQL.
- **Models:** representa las entidades persistidas.
- **Analytics:** contiene cálculos estadísticos y algoritmos de detección.
- **Tests:** verifica las reglas de negocio, los contratos y los casos límite.

Los endpoints no deben contener directamente consultas SQL ni implementar algoritmos estadísticos.

## 5. Modelo de datos

El esquema definitivo se debe acordar con el repositorio `data` antes de implementar la integración.

### `products`

Catálogo de productos normalizados.

Campos propuestos: `id`, `name`, `brand`, `category`, `reference_unit`, `created_at`.

### `stores`

Catálogo de tiendas.

Campos propuestos: `id`, `name`, `base_url`, `country_code`, `currency_code`.

### `store_products`

Relación entre un producto normalizado y su publicación en una tienda.

Campos propuestos: `id`, `product_id`, `store_id`, `external_id`, `source_url`, `source_name`.

### `price_observations`

Historial de precios observados.

Campos propuestos: `id`, `store_product_id`, `price`, `currency_code`, `is_promotion`, `observed_at`, `fetched_at`.

Cada observación debe conservar su precio y moneda originales. Los nuevos precios deben generar nuevas observaciones, sin sobrescribir el historial.

### `exchange_rates`

Historial de tipos de cambio.

Campos propuestos: `id`, `base_currency`, `quote_currency`, `rate`, `observed_at`, `fetched_at`.

### `anomaly_alerts`

Registro de posibles anomalías.

Campos propuestos: `id`, `price_observation_id`, `anomaly_type`, `severity`, `score`, `description`, `created_at`, `status`.

Los campos y restricciones definitivos deben reflejar las necesidades reales del MVP. Las migraciones de esquema deben gestionarse desde este repositorio.

## 6. API REST

Prefijo propuesto: `/api/v1`.

Los siguientes endpoints son contratos iniciales de referencia. Deben confirmarse con el frontend antes de implementarlos.

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/health` | Estado de la API |
| `GET` | `/products` | Listar y filtrar productos |
| `GET` | `/products/{id}` | Obtener detalle de un producto |
| `GET` | `/prices/history` | Consultar historial de precios |
| `GET` | `/indicators/inflation` | Consultar indicadores de variación |
| `GET` | `/exchange-rates/history` | Consultar tipos de cambio históricos |
| `GET` | `/alerts` | Consultar alertas |
| `GET` | `/dashboard/summary` | Obtener métricas resumidas |

### Parámetros de consulta

Según el endpoint, se podrán utilizar:

- `start_date` y `end_date`: rango de fechas.
- `product_id`: filtro por producto.
- `store_id`: filtro por tienda.
- `category`: filtro por categoría.
- `currency`: moneda de visualización.
- `page` y `page_size`: paginación.

### Convenciones

- Utilizar códigos HTTP apropiados.
- Validar los parámetros de entrada.
- Mantener formatos consistentes de fechas y monedas.
- Definir respuestas de error uniformes.
- Aplicar paginación cuando sea necesario.
- Evitar exponer detalles internos o credenciales en los errores.
- Documentar los contratos mediante OpenAPI.

## 7. Indicadores de precios y tipos de cambio

### Variación porcentual del precio

\[
\Delta P(\%) =
\left(\frac{P_t}{P_{t-1}}-1\right)\times100
\]

### Variación porcentual del tipo de cambio

\[
\Delta FX(\%) =
\left(\frac{FX_t}{FX_{t-1}}-1\right)\times100
\]

Para comparar precios en distintas monedas, se debe utilizar una moneda de referencia y documentar la convención de cada tipo de cambio.

Por ejemplo, si la tasa está expresada en CLP por USD:

\[
P_{\mathrm{USD}}=\frac{P_{\mathrm{CLP}}}{FX_{\mathrm{CLP/USD}}}
\]

La conversión debe utilizar una tasa válida para el momento de la observación. No se deben usar tasas futuras para recalcular el pasado.

### Índice de precios

Para el MVP se puede construir un índice simple sobre una canasta fija de productos. La metodología debe especificar:

- Período base.
- Productos incluidos.
- Método de agregación.
- Tratamiento de promociones.
- Ponderaciones, si existen.
- Tratamiento de datos faltantes.

El índice debe presentarse como un indicador experimental de la canasta analizada, no como una medición oficial de la inflación nacional.

## 8. Detección de anomalías

El módulo de detección es una de las responsabilidades centrales del backend.

### Enfoque inicial

1. Obtener observaciones históricas comparables.
2. Calcular la variación porcentual del precio.
3. Comparar el cambio con una línea base histórica.
4. Aplicar un método estadístico robusto cuando exista historial suficiente.
5. Comparar el movimiento del precio con la variación del tipo de cambio.
6. Generar una alerta con su explicación y datos de referencia.

Se recomienda comenzar con reglas estadísticas y una línea base basada en mediana móvil y desviación absoluta mediana (MAD), cuando los datos lo permitan.

Isolation Forest puede evaluarse posteriormente si aporta valor medible. No es necesario utilizar machine learning complejo para cumplir el MVP.

### Evaluación

El módulo debe probarse con escenarios controlados:

- Variaciones normales.
- Aumentos bruscos.
- Caídas de precios.
- Promociones.
- Variaciones asociadas al tipo de cambio.
- Datos incompletos y duplicados.

Cuando existan etiquetas de referencia, evaluar precisión, recall y falsos positivos. Los datos sintéticos deben identificarse como tales.

**Una anomalía no demuestra por sí sola manipulación de precios ni inflación injustificada.** Es una señal que requiere interpretación.

## 9. Integración con `data`

El repositorio `data` se encarga de recolectar y validar observaciones. El backend se encarga de la persistencia central, los casos de uso, los indicadores y las alertas.

Antes de implementar la integración, ambos repositorios deben acordar un único contrato de observación.

Cada registro debería contener como mínimo:

- Fuente o tienda.
- Identificador de la publicación, cuando exista.
- Nombre del producto.
- Precio original.
- Código de moneda.
- URL de origen.
- `observed_at`.
- `fetched_at`.
- Información de promoción cuando esté disponible.

### Estrategia recomendada para el MVP

Permitir que el pipeline escriba directamente en PostgreSQL mediante una capa de persistencia acordada, si esa es la opción elegida por el equipo. El backend debe ser el responsable de las migraciones y del esquema compartido.

Si el equipo prefiere desacoplar la escritura, se puede implementar una API de ingesta. No es necesario mantener ambos mecanismos para el MVP.

La integración debe evitar modelos duplicados, esquemas incompatibles y cambios de base de datos sin coordinación.

## 10. Configuración del entorno

Ejemplo de `.env.example`:

```dotenv
APP_NAME=PriceScope API
APP_ENV=development
API_V1_PREFIX=/api/v1
LOG_LEVEL=INFO

DATABASE_URL=postgresql+psycopg://pricescope:pricescope@localhost:5432/pricescope
```

Las variables deben ajustarse a la configuración implementada.

No subir archivos `.env` reales, credenciales, tokens ni claves al repositorio.

## 11. Instalación y ejecución local

Los comandos siguientes son orientativos y deben coincidir con la estructura real del proyecto.

### Requisitos

- Python 3.11 o la versión acordada.
- PostgreSQL.
- Git.

### Instalación

```bash
git clone <URL_DEL_REPOSITORIO_BACKEND>
cd <CARPETA_DEL_REPOSITORIO>

python -m venv .venv
```

Activar el entorno virtual.

**Windows PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
source .venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

Configurar `.env`, crear la base de datos y ejecutar las migraciones:

```bash
alembic upgrade head
```

Iniciar el servidor:

```bash
uvicorn src.main:app --reload
```

El comando de inicio depende de la ruta de importación definitiva del proyecto.

### Documentación interactiva

Si se utiliza la configuración predeterminada de FastAPI:

- Swagger UI: `/docs`
- Especificación OpenAPI: `/openapi.json`

## 12. Pruebas

Las pruebas deben cubrir, como mínimo:

- Validación de parámetros y respuestas.
- Cálculo de variaciones porcentuales.
- Conversión de monedas.
- Alineación temporal de los tipos de cambio.
- Consultas históricas.
- Manejo de valores faltantes y duplicados.
- Detección de anomalías con casos controlados.
- Persistencia y recuperación de alertas.
- Errores de integración.

Comando propuesto:

```bash
pytest
```

Las pruebas unitarias del detector deben ejecutarse independientemente de FastAPI para facilitar su evaluación y experimentación.

## 13. Plan de trabajo de tres semanas

### Semana 1 — Base técnica

- Crear la aplicación FastAPI.
- Definir el contrato compartido con `data`.
- Configurar PostgreSQL y Alembic.
- Implementar modelos, schemas y endpoint de salud.
- Integrar las primeras observaciones.
- Definir los contratos con el frontend.

**Resultado:** datos persistidos y consultables.

### Semana 2 — Indicadores e IA

- Implementar consultas de historial.
- Calcular variaciones e indicadores.
- Integrar tipos de cambio.
- Implementar el primer detector de anomalías.
- Persistir y exponer alertas.
- Conectar el dashboard.

**Resultado:** flujo funcional de consulta, análisis y visualización.

### Semana 3 — Validación y demo

- Ejecutar pruebas de integración.
- Evaluar falsos positivos y casos límite.
- Corregir problemas de calidad de datos.
- Documentar la metodología analítica.
- Preparar una ejecución reproducible.
- Completar el flujo de demostración.

**Resultado:** MVP integrado, medible y demostrable.

## 14. Criterios de aceptación

- [ ] La API arranca con instrucciones documentadas.
- [ ] La base de datos se configura mediante variables de entorno.
- [ ] Las migraciones se pueden ejecutar desde un entorno limpio.
- [ ] Los productos y el historial de precios se pueden consultar.
- [ ] Los indicadores utilizan una metodología documentada.
- [ ] Las conversiones utilizan tipos de cambio temporalmente válidos.
- [ ] El detector genera resultados reproducibles.
- [ ] Las alertas se pueden consultar desde el frontend.
- [ ] Los errores y datos faltantes se manejan explícitamente.
- [ ] Las pruebas críticas pasan.
- [ ] Las limitaciones del análisis están documentadas.

## 15. Decisiones pendientes

Antes de ampliar el alcance, confirmar:

1. Versión definitiva de Python y dependencias.
2. Contrato de datos con el repositorio `data`.
3. Esquema final de PostgreSQL.
4. Endpoints y formatos de respuesta acordados con frontend.
5. Fuente y convención de los tipos de cambio.
6. Método y umbrales iniciales de detección.
7. Disponibilidad y calidad del historial.
8. Ejecución de tareas periódicas.
9. Configuración de despliegue y demostración.

La prioridad es completar un flujo end-to-end pequeño y confiable. Toda funcionalidad adicional debe justificarse por su contribución a la demo o por una necesidad concreta del MVP.