# Automatizaciones personales — Memoria del proyecto

## Propósito

Repo separado del `finance-dashboard` (`Matias1661/finance-dashboard`) para
alojar automatizaciones personales de Matías que se migran de Relay.app pero
**no tienen relación con el dashboard de finanzas**. Se creó el 22/07/2026
específicamente para el flujo "Documentos importantes"; puede sumar más
flujos no financieros en el futuro (ej. "Articulos Holy Death", pendiente de
migrar).

Se usa infraestructura equivalente a la del finance-dashboard (GitHub
Actions, mismo patrón de script Python + workflow + registro de procesados
en JSON) por conveniencia y consistencia, pero es un repo completamente
independiente: docs, secrets y CI propios.

## Identidad y acceso

- GitHub: cuenta Matias1661, repo `automatizaciones-personales` (privado).
- Notion: mismo workspace que finance-dashboard, pero las DBs que usa este
  repo (`Documentos`) NO están bajo la página "Finance Tracker".
- Secrets del repo (`NOTION_TOKEN`, `ANTHROPIC_API_KEY`,
  `GOOGLE_SERVICE_ACCOUNT`): mismos valores que en finance-dashboard, deben
  cargarse a mano en este repo (Settings → Secrets and variables → Actions)
  porque GitHub no permite copiar secrets entre repos ni leerlos una vez
  guardados.

## Flujo: Documentos importantes

- **Origen:** flujo de Relay "Archivar documentos importantes". Nunca corrió
  en producción en Relay (0 corridas reales) — su mapeo a la DB Notion
  "Documentos" tenía varios campos marcados "Field is no longer available in
  the current schema" (la DB cambió de esquema y Relay quedó desactualizado).
- **Trigger original:** archivo nuevo en la carpeta Drive "Documentos
  importantes" (`1wZlF8vF1OLDMYC1ds1mahG7N9qjXjNdR`).
- **Reemplazo:** `scripts/process_documentos_importantes.py` +
  `.github/workflows/sync-documentos.yml` (cron diario 08:00 + dispatch
  manual). A diferencia de Relay (3 llamadas de IA separadas: título,
  resumen, fecha), este script hace **una sola llamada** a Claude que
  devuelve los 3 datos en JSON — mismo resultado, menos costo/latencia.
- **Escritura:** DB Notion "Documentos" (`19633ce5-0e68-80a6-8ab3-000bfd8682e5`,
  fuera del Finance Tracker). Schema verificado el 22/07/2026: `Nombre`
  (title), `Descripción` (text), `Link` (url), `Fecha de Creación` (date,
  opcional — se deja vacía si Claude no encuentra una fecha clara).
- **Prompt:** embebido directamente en el script (no vive en una DB Notion
  de prompts, a diferencia del finance-dashboard) — este repo no tiene el
  mismo sistema de "Prompts" centralizado.
- **Registro de duplicados:** `processed_documentos_importantes.json`, por
  Drive file ID. Documentos que fallan la extracción (ej. formato no
  soportado, o Claude no devuelve título/resumen) se marcan en
  `requiere_revision` y no se reintentan solos.
- **Prerequisito:** la carpeta Drive tiene que estar compartida con el email
  de la cuenta de servicio de `GOOGLE_SERVICE_ACCOUNT` (Matías la comparte a
  mano, 22/07/2026 — no estaba compartida al momento de implementar).

## Pendiente

- Validar el primer archivo real subido a la carpeta tras compartirla con la
  cuenta de servicio.
- Evaluar si "Articulos Holy Death" (scraper semanal de holydeath.com,
  activo en Relay, sin relación con finanzas) se migra a este mismo repo
  antes de que Relay cierre (15/08/2026 plan gratuito / 14/09/2026 plan de
  pago).
