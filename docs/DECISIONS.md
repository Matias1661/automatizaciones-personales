## [2026-07-27] Fix: DB Documentos duplicada — dedupe contra Notion, no solo contra el JSON local

**Contexto:** Matías notó que la página de Notion "Documentos" tenía 124
entradas para 68 archivos en Drive — no era un espejo exacto de la carpeta.

**Hallazgo:** el 24/04/2026 (y en fechas posteriores, coincidiendo con cada
subida de archivo nuevo hasta el 29/05/2026), un proceso no documentado y
anterior a este proyecto ya había creado una página en Notion por cada
archivo de la carpeta "Documentos importantes". No hay rastro de este
proceso en `docs/`. Cuando este script empezó a correr (22/07/2026),
dedupeaba únicamente contra `processed_documentos_importantes.json` —que
no tenía ningún registro de esas páginas previas—, así que volvió a crear
una página para cada archivo que logró procesar. Resultado: 56 archivos
quedaron con 2 páginas (la previa + la del script), 6 (los PDFs inválidos)
quedaron con 1 sola página (la previa, ya que el script nunca llegó a
crearles una), y 6 archivos subidos más tarde (sin página previa) quedaron
con 1 sola página (la del script). 62 + 62 duplicados − 6 sin duplicar = 124.

**Decisión:** mantener las páginas creadas por este script (trazables en
`processed_documentos_importantes.json`) y descartar las 56 previas
duplicadas. Como el conector de Notion disponible no permite borrar/archivar
páginas, se renombraron las 56 con el prefijo "🗑️ DUPLICADO - BORRAR - " y
se creó una vista de tabla "Duplicados a borrar" (filtro: Nombre contiene
"DUPLICADO - BORRAR") en la DB Documentos, para que Matías las seleccione
todas y las borre manualmente en un solo paso desde la UI de Notion.

**Fix de fondo:** se agregó `ya_existe_en_notion()` en
`scripts/process_documentos_importantes.py`, que consulta la DB Documentos
por `Link` antes de crear una página nueva (vía `POST
/v1/data_sources/{id}/query`). Si ya existe una página con ese link, el
archivo se marca como procesado sin crear duplicado ni gastar una llamada a
Claude. Esto cubre tanto páginas creadas por este script en corridas
previas como cualquier página preexistente de otro origen — la DB de
Notion pasa a ser la fuente de verdad para deduplicar, no solo el JSON
local.

**Pendiente de acción manual del usuario:** abrir la vista "Duplicados a
borrar" en la DB Documentos, seleccionar todas las filas y borrarlas.

## [2026-07-27] Fix: reintento automático de fallos por crédito en Documentos importantes

**Contexto:** al resolverse el bloqueo de crédito de Anthropic (ver entrada
del 22/07 más abajo), se disparó `sync-documentos.yml` manualmente para
procesar los 41 documentos pendientes. El workflow terminó en verde, pero
el log real mostró `0 archivo(s) nuevo(s). Nada que procesar.` — no había
reintentado ninguno.

**Hallazgo:** `processed_documentos_importantes.json` tenía 47 entradas en
`requiere_revision` (41 por el bloqueo de crédito + 6 por PDF inválido). El
script excluía **todas** las entradas de `requiere_revision` de la búsqueda
de archivos nuevos, sin distinguir el motivo del fallo — trataba un fallo
transitorio de crédito igual que un PDF corrupto (permanente). Esto
contradecía la intención original: los fallos de crédito debían reintentarse
solos una vez resuelto el bloqueo; solo los PDFs inválidos requerían carga
manual permanente.

**Decisión:** agregar un campo `retryable` (bool) a cada entrada de
`requiere_revision`, clasificado por el mensaje de error (marcadores como
"credit balance is too low", "rate_limit_error", "429" → reintentable;
cualquier otro error, ej. PDF inválido → no reintentable). El filtro de
"archivos nuevos" ahora solo excluye los `retryable: false`; los
`retryable: true` vuelven a aparecer como candidatos en cada corrida hasta
que se resuelvan (éxito) o cambien de motivo. Entradas viejas sin el campo
se clasifican automáticamente con la misma heurística al cargar el estado
(compatibilidad hacia atrás, sin necesidad de migrar el JSON a mano).

**Implementado:** edición quirúrgica de
`scripts/process_documentos_importantes.py` (función
`es_error_reintentable` + reescritura del bloque principal para no duplicar
entradas de `requiere_revision` al reintentar). Sin cambios en el schema de
Notion ni en el workflow de GitHub Actions.

## [2026-07-22] Creación del repo + implementación de Documentos importantes

**Contexto:** al revisar el backup completo de Relay (14 workflows), Matías
pidió mantener el flujo "Archivar documentos importantes" tras el cierre de
Relay. No tiene relación con el finance-dashboard, así que se decidió crear
un repo nuevo en vez de sumarlo a `finance-dashboard` (que es específicamente
el dashboard de finanzas).

**Hallazgo:** el flujo nunca corrió en producción en Relay (0 corridas
reales según el backup). Al inspeccionar el `workflow.json` exportado, el
step final de Notion tenía varios inputs deshabilitados con la descripción
"Field is no longer available in the current schema" — la DB Notion
"Documentos" cambió de esquema en algún momento y el mapeo de Relay quedó
roto (título/link/resumen/fecha referenciaban campos que ya no existían).
Se verificó el esquema real y actual de la DB directamente vía Notion antes
de implementar: `Nombre` (title), `Descripción` (text), `Link` (url),
`Fecha de Creación` (date).

**Decisión de repo:** nuevo repo privado `Matias1661/automatizaciones-personales`,
creado vía API. Privado (a diferencia de `finance-dashboard`, que es público
por los minutos gratis de Actions) porque los documentos que procesa este
flujo pueden ser sensibles (contratos, comprobantes personales) y no hay el
mismo incentivo de minutos ilimitados que en el dashboard de finanzas.

**Implementado:**
1. `scripts/process_documentos_importantes.py`: mismo patrón que los scripts
   del finance-dashboard (Drive vía cuenta de servicio, registro de
   procesados por file ID, manejo de errores por archivo sin frenar el
   batch — aplicando la misma lección del incidente de Talho Argentino del
   22/07). Simplificación respecto a Relay: una sola llamada a Claude en vez
   de 3 (título + resumen + fecha en un mismo JSON).
2. `.github/workflows/sync-documentos.yml`: cron diario 08:00 + dispatch
   manual.
3. Prompt de extracción embebido en el script (este repo no tiene un sistema
   de Prompts centralizado en Notion como el finance-dashboard).

**Pendiente de acción manual del usuario:**
1. Compartir la carpeta Drive "Documentos importantes"
   (`1wZlF8vF1OLDMYC1ds1mahG7N9qjXjNdR`) con el email de la cuenta de
   servicio de `GOOGLE_SERVICE_ACCOUNT` — en curso durante esta misma sesión.
2. Cargar los 3 secrets del repo (`NOTION_TOKEN`, `ANTHROPIC_API_KEY`,
   `GOOGLE_SERVICE_ACCOUNT`) con los mismos valores que ya usa
   `finance-dashboard` — no se pueden copiar automáticamente entre repos.
3. Validar con el primer archivo real.
