## 2026-07-22 — Creación del repo + flujo Documentos importantes

- Repo `automatizaciones-personales` creado (privado), independiente de
  `finance-dashboard`.
- Implementado `scripts/process_documentos_importantes.py` +
  `.github/workflows/sync-documentos.yml`: reemplazo del flujo de Relay
  "Archivar documentos importantes" (nunca corrió en producción por un
  mapeo de Notion roto). Una sola llamada a Claude en vez de las 3 que usaba
  Relay.
- Pendiente: compartir la carpeta Drive con la cuenta de servicio (en curso),
  cargar los 3 secrets del repo, validar con un archivo real.
