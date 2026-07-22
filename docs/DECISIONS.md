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
