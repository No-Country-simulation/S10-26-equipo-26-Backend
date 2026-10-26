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

### Problemas clave del proyecto y responsabilidad de este repo

El equipo enfrenta tres problemas técnicos centrales (detalle en `problematica.md` en la raíz del proyecto; plan de trabajo ágil en `PLAN-AGIL.md`). Este repo es el dueño del esquema de datos y los contratos de API:

| Problema | Responsabilidad del Backend | Decisión clave |
|---|---|---|
| **1. Identidad de productos entre tiendas** | Catálogo `productos_canonicos` + catálogo `categorias`. El vínculo producto↔tienda hoy es la fila en `precios_historicos(producto_id, tienda_id)`. | El matching es **curado manualmente** por el equipo. La tabla `store_products` (con `external_id`/`source_url`) **no existe aún** en la BD: decisión #8 de `PLAN-AGIL.md` (HU 1.2/1.4 pospuestas). |
| **2. Promociones, stock y reduflación** | `precio_tachado` y `en_oferta` en `precios_historicos`; clasificación promo vs regular **derivada en lectura** (sin columnas persistidas); **exclusión de ofertas** (`en_oferta = true`) del índice de inflación base. | El índice de inflación base usa **solo precios regulares**. La mediana móvil es el método candidato. Las alertas (reduflación, `anomaly_alerts`) están **pospuestas**: no existe la tabla (decisión #7). |
| **3. Sincronización timestamp ↔ tipo de cambio** | Tabla `historial_divisas` (`timestamp` PK, oficial + paralelo en la misma fila). `precio_usd` y `tipo_cambio_usado` **se persisten** en `precios_historicos`, calculados por el pipeline Data en el momento de la captura. | La BD es **Railway Postgres** (proyecto `s10-26-equipo-26`); en local se conecta vía túnel SSH. |

Flujo de datos y orden de dependencias:

- `data` recolecta (scraper + FX) y entrega observaciones crudas.
- `backend` persiste, calcula indicadores y alertas, y expone la API REST.
- `frontend` consume la API; no recalcula indicadores.
- Orden de implementación: **Backend primero** (define esquema y contratos), **Data en paralelo** (contra el contrato), **Frontend al final** (sobre el API).

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

> **✅ Fuente de verdad = Railway Postgres** (proyecto `s10-26-equipo-26`, servicio `Postgres`, base `railway`; migrado desde Supabase el 2026-10-25). El esquema tiene **5 tablas en español** y los modelos SQLAlchemy de `src/models/` están mapeados 1:1 con ellas (`compare_metadata` = 0 diferencias).
>
> ⚠️ **Host interno:** `postgres.railway.internal` solo es alcanzable desde Railway. Para desarrollo local, levantar el túnel SSH en una terminal:
>
> ```powershell
> ssh -i $env:USERPROFILE\.ssh\id_ed25519_railway -o IdentitiesOnly=yes -N -L 55432:localhost:5432 railway-postgres
> ```
>
> y usar `DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:55432/railway` (ver `.env.example`).
>
> ℹ️ La migración Alembic `0001` es la fuente del esquema: se aplica en el deploy (`alembic upgrade head` en el Procfile) y localmente vía túnel. La BD local Docker (`docker-compose up db`, puerto 5435) queda como alternativa offline.

### `categorias`

Catálogo de categorías.

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | integer | PK |
| `nombre` | varchar(100) | NOT NULL, UNIQUE (`categorias_nombre_key`) |

### `tiendas`

Catálogo de tiendas.

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | integer | PK |
| `nombre` | varchar(100) | NOT NULL, UNIQUE (`tiendas_nombre_key`) |
| `url_base` | varchar(255) | nullable |

### `productos_canonicos`

Catálogo de productos normalizados (el problema 1 se resuelve aquí como referencia canónica).

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | integer | PK |
| `nombre_universal` | varchar(255) | NOT NULL |
| `categoria_id` | integer | FK → `categorias(id)`, nullable |
| `unidad_medida` | varchar(50) | nullable (p. ej. `1 kg`, `500 G`, `unidad`) |
| `marca` | text | nullable |

### `precios_historicos`

Historial de precios observados: une producto y tienda directamente (no existe tabla intermedia).

| Columna | Tipo | Restricción |
|---|---|---|
| `id` | bigint | PK |
| `timestamp` | timestamptz | NOT NULL, DEFAULT `now()` (momento de la captura) |
| `producto_id` | integer | FK → `productos_canonicos(id)`, nullable |
| `tienda_id` | integer | FK → `tiendas(id)`, nullable |
| `precio_local` | numeric(12,2) | NOT NULL |
| `precio_tachado` | numeric(12,2) | nullable (precio antes de la promo) |
| `en_oferta` | boolean | DEFAULT `false` |
| `tipo_cambio_usado` | numeric(12,4) | NOT NULL (FX aplicado en la captura) |
| `precio_usd` | numeric(12,2) | NOT NULL (**persistido**, no es una vista) |

Índices: `idx_precios_prod_tiempo (producto_id, timestamp DESC)` · `idx_precios_tienda_tiempo (tienda_id, timestamp DESC)`.

**Reglas:**

- Cada lectura genera una fila nueva; nunca se sobrescribe el historial.
- `precio_usd` y `tipo_cambio_usado` los calcula y persiste el **pipeline Data** en el momento de la captura; el backend solo los lee.
- No existen columnas `currency_code`, `is_available`, `is_promotion` ni `price_regular`: la clasificación de promo se **deriva en lectura** desde `en_oferta` + `precio_tachado`.

### `historial_divisas`

Historial de tipos de cambio: una fila por instante con ambas cotizaciones.

| Columna | Tipo | Restricción |
|---|---|---|
| `timestamp` | timestamptz | **PK**, DEFAULT `now()` |
| `tipo_cambio_oficial` | numeric(12,4) | NOT NULL |
| `tipo_cambio_paralelo` | numeric(12,4) | NOT NULL |

Sin `id`, sin `base_currency`/`quote_currency` y sin `source`. El "FX as of" se resuelve con `WHERE timestamp <= :ts ORDER BY timestamp DESC LIMIT 1` (la PK ya indexa `timestamp`); el upsert es por `timestamp`.

### Tablas **no existentes** (pospuestas)

- `store_products` — requeriría cambio de BD (decisión #8; bloquea HU 1.2 y HU 1.4).
- `anomaly_alerts` — requeriría cambio de BD (decisión #7; bloquea HU 2.4 y HU 3.5).

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

Cada registro de precio debería contener como mínimo (para mapear a `precios_historicos`):

- Tienda (`tiendas.nombre`, ya sembrada: Carrefour, Cetrogar, Coto).
- Producto canónico (`productos_canonicos.id`), tras el mapeo curado.
- Precio actual (`precio_local`).
- Precio tachado o anterior (`precio_tachado`) cuando exista.
- Señal de oferta (`en_oferta`; badge, `2x1`, etc.).
- Momento de la captura (`timestamp`).
- Presentación/gramaje crudo, si la tienda lo expone (aún **sin columna de persistencia**: base futura de reduflación, decisión #7).

Y para el job FX (para mapear a `historial_divisas`):

- `timestamp`, `tipo_cambio_oficial` y `tipo_cambio_paralelo`.

Reglas de integración:

- El pipeline **calcula y persiste** `precio_usd` y `tipo_cambio_usado` en la misma fila de `precios_historicos`, usando el FX vigente en el `timestamp` de la captura (no un FX futuro).
- **La BD (Railway) es del equipo**: las migraciones de esquema viven en este repo y se aplican en el deploy o localmente vía túnel, coordinadas con el equipo.
- La identidad canónica es `productos_canonicos`; mientras no exista `store_products` (decisión #8), el scraping no persiste `external_id`/`source_url` en esta BD.

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

DATABASE_URL=postgresql+psycopg://pricescope:pricescope@localhost:5435/pricescope
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

Configurar `.env` (apunta a Railway vía túnel), levantar el túnel SSH y ejecutar las migraciones:

```powershell
# Terminal 1 — túnel a Railway Postgres (mantener abierto)
ssh -i $env:USERPROFILE\.ssh\id_ed25519_railway -o IdentitiesOnly=yes -N -L 55432:localhost:5432 railway-postgres
```

```bash
alembic upgrade head
```

> ⚠️ El `DATABASE_URL` local apunta a **localhost:55432 (túnel a Railway Postgres)** — sin túnel, nada conecta. El túnel usa la clave `~/.ssh/id_ed25519_railway` (registrada en Railway como `opencode-automation`).
>
> ℹ️ Sin red, usa la BD local Docker: `docker-compose up db` (puerto 5435) y la URL alternativa del `.env.example`.

Seed (idempotente; el catálogo de 3 tiendas / 5 categorías / 15 productos ya está en Railway):

```bash
python scripts/seed.py
```

Iniciar el servidor:

```bash
uvicorn src.main:app --reload
```

El comando de inicio depende de la ruta de importación definitiva del proyecto.

### Backup de la base de datos

`scripts/backup_db.py` genera un `.sql` restaurable (DDL + datos `COPY` + secuencias) de la BD indicada en `DATABASE_URL`:

```bash
python scripts/backup_db.py                      # → backups/pricescope_backup_<fecha>.sql
python scripts/backup_db.py --out backups/mi.sql
```

- **Solo lectura garantizada:** corre en una transacción `REPEATABLE READ READ ONLY` (el servidor rechaza cualquier escritura) y verifica `SHOW transaction_read_only = on`.
- Snapshot consistente: todas las tablas del mismo instante.
- Restore probado: `psql -U <user> -d <db> -f backups/<archivo>.sql`.
- La carpeta `backups/` está en `.gitignore` (no commitear volcados de BD).
- Requiere el túnel SSH activo (usa el `DATABASE_URL` del `.env`); por ejemplo para regenerar el backup contra Railway.

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
3. ~~Esquema final de PostgreSQL~~ **✅ Resuelto: Railway Postgres, 5 tablas en español (migrado desde Supabase 2026-10-25).**
4. Endpoints y formatos de respuesta acordados con frontend.
5. Fuente y convención de los tipos de cambio (debe entregar oficial + paralelo).
6. Método y umbrales iniciales de detección.
7. Disponibilidad y calidad del historial.
8. Ejecución de tareas periódicas.
9. Configuración de despliegue y demostración.
10. Cambios de BD pendientes: tabla `store_products` (#8) y `anomaly_alerts` (#7) — a plantear al equipo técnico (ver `PLAN-AGIL.md`).

La prioridad es completar un flujo end-to-end pequeño y confiable. Toda funcionalidad adicional debe justificarse por su contribución a la demo o por una necesidad concreta del MVP.
