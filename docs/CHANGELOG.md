## 2026-07-27 — Fix: reintento automático de fallos por crédito

- `scripts/process_documentos_importantes.py`: las entradas de
  `requiere_revision` ahora tienen un campo `retryable` que distingue
  fallos transitorios (crédito, rate-limit) de fallos permanentes (PDF
  inválido). Los reintentables se vuelven a intentar solos en cada
  corrida; antes, el workflow los ignoraba para siempre una vez
  marcados, aunque terminara en verde.
- Hallazgo detectado al disparar `sync-documentos.yml` manualmente tras
  resolverse el bloqueo de crédito: la corrida dio "0 archivos nuevos"
  cuando debía reintentar 41 documentos. Detalle completo en
  `docs/DECISIONS.md`.

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
