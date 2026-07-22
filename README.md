# Automatizaciones personales

Repo independiente del `finance-dashboard`, para automatizaciones personales
migradas de Relay.app que no tienen relación con el dashboard de finanzas.

Ver `docs/PROJECT_MEMORY.md` para el contexto completo.

## Flujos

- **Documentos importantes** (`scripts/process_documentos_importantes.py`):
  reemplaza el flujo de Relay "Archivar documentos importantes". Ver
  `docs/DECISIONS.md` para el detalle de la migración.

## Setup

Secrets necesarios en este repo (Settings → Secrets and variables → Actions),
mismos valores que ya usás en `finance-dashboard`:
- `NOTION_TOKEN`
- `ANTHROPIC_API_KEY`
- `GOOGLE_SERVICE_ACCOUNT`
