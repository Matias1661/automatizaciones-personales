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
