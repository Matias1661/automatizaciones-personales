# Roadmap

## En curso
- [x] Compartir la carpeta Drive "Documentos importantes" con la cuenta de
      servicio de `GOOGLE_SERVICE_ACCOUNT`.
- [x] Cargar secrets del repo (`NOTION_TOKEN`, `ANTHROPIC_API_KEY`,
      `GOOGLE_SERVICE_ACCOUNT`).
- [x] Validar `process_documentos_importantes.py` con un archivo real.
- [x] Resolver el bloqueo de crédito de Anthropic y reintentar los 41
      documentos pendientes (27/07/2026 — resuelto con el fix de
      `retryable` en el script, ver `docs/DECISIONS.md`).
- [ ] Cargar a mano en Notion los 6 PDFs inválidos que quedan en
      `requiere_revision` (`processed_documentos_importantes.json`).
- [ ] Borrar en Notion las 56 páginas duplicadas marcadas con
      "🗑️ DUPLICADO - BORRAR - " (vista "Duplicados a borrar" en la DB
      Documentos) — el conector no permite borrarlas automáticamente.

## Futuro
- [ ] Evaluar migrar "Articulos Holy Death" (scraper semanal de
      holydeath.com) a este mismo repo antes del cierre de Relay
      (15/08/2026 plan gratuito / 14/09/2026 plan de pago).
