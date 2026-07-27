"""
Reemplazo del flujo de Relay "Archivar documentos importantes".

Trigger original: archivo nuevo en la carpeta Drive "Documentos importantes".
El flujo de Relay nunca corrio en produccion (0 corridas reales) porque su
mapeo a la DB Notion "Documentos" habia quedado roto (varios campos
marcados "Field is no longer available in the current schema" tras un
cambio de esquema de la DB). Este script usa el schema actual y real de
esa DB, verificado directamente el 22/07/2026:
  Nombre (title), Descripcion (text), Link (url), Fecha de Creacion (date).

Este script:
1. Lista los archivos de la carpeta Drive "Documentos importantes".
2. Descarta los que ya estan en processed_documentos_importantes.json
   (registro por Drive file ID).
3. Para cada archivo nuevo, le pide a Claude (una sola llamada, a
   diferencia de las 3 llamadas separadas que usaba Relay) que genere:
   - Titulo: descripcion de hasta 5 palabras en español.
   - Resumen: hasta 50 palabras en español, incluyendo costos/pagos si
     los hay y fecha de fin si es un contrato.
   - Fecha: fecha de creacion/emision del documento en formato YYYY-MM-DD,
     o vacia si no hay una fecha clara.
4. Crea la pagina en la DB Notion "Documentos" con esos datos + el link a
   Drive.

A diferencia de los flujos del finance-dashboard, el prompt de extraccion
va embebido en este script (no vive en una DB Notion) -- este repo es
independiente del sistema de Prompts del finance-dashboard.

Variables de entorno requeridas (secrets del repo):
  NOTION_TOKEN
  ANTHROPIC_API_KEY
  GOOGLE_SERVICE_ACCOUNT

Prerequisito manual: la carpeta Drive "Documentos importantes"
(1wZlF8vF1OLDMYC1ds1mahG7N9qjXjNdR) tiene que estar compartida (Viewer
alcanza) con el email de la cuenta de servicio de GOOGLE_SERVICE_ACCOUNT.

Ver docs/DECISIONS.md de este repo para el contexto completo de la migracion.
"""

import os, json, base64, re
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SERVICE_ACCOUNT_JSON = os.environ["GOOGLE_SERVICE_ACCOUNT"]

NOTION_VERSION = "2025-09-03"
DOCUMENTOS_DS_ID = "19633ce5-0e68-80a6-8ab3-000bfd8682e5"
DRIVE_FOLDER_ID = "1wZlF8vF1OLDMYC1ds1mahG7N9qjXjNdR"  # "Documentos importantes"
STATE_FILE = "processed_documentos_importantes.json"

CLAUDE_MODEL = "claude-sonnet-5"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

FECHA_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Marcadores de errores transitorios: si el mensaje de error contiene alguno
# de estos, se considera "reintentable" (se vuelve a intentar solo en la
# proxima corrida, sin intervencion manual). Cualquier otro error (ej. PDF
# invalido, tipo de archivo no soportado, extraccion incompleta) se considera
# NO reintentable y requiere carga manual en Notion.
ERRORES_REINTENTABLES = (
    "credit balance is too low",
    "insufficient_quota",
    "rate_limit_error",
    "overloaded_error",
    "429",
)


def es_error_reintentable(error_msg):
    msg = (error_msg or "").lower()
    return any(marca in msg for marca in ERRORES_REINTENTABLES)

EXTRACCION_PROMPT = """Analiza el documento adjunto y devolve tres datos:

1. titulo: una descripcion de hasta 5 palabras en español (no una oracion completa, solo las palabras clave que identifican el documento).

2. resumen: los datos mas importantes del documento en no mas de 50 palabras, en español. Incluí los costos o pagos que mencione el documento si los hay; si no hubiera, no aclares que es gratuito. Si es un contrato con fecha de finalizacion, aclara cual es.

3. fecha: la fecha de creacion o emision del documento, en formato YYYY-MM-DD. Si el documento tiene una fecha de inicio o alguna fecha claramente determinada, usa esa. Si no encontras una fecha clara, dejala como cadena vacia "".

El documento puede ser una imagen, PDF con o sin texto seleccionable, u otro formato de oficina; en cualquier caso, lee el contenido visualmente si hace falta.

Respondé UNICAMENTE con un JSON valido, sin texto adicional, sin backticks, con este formato exacto:
{"titulo": "...", "resumen": "...", "fecha": "2026-06-30"}"""

# Mimetypes que se pueden mandar como bloque "image" a la API de Claude.
IMAGE_MIME_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
    "image/webp": "image/webp",
    "image/heic": "image/jpeg",
}


def get_drive_access_token():
    from google.oauth2 import service_account
    import google.auth.transport.requests

    info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    creds = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def list_new_files(drive_token, already_processed):
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "q": f"'{DRIVE_FOLDER_ID}' in parents and trashed = false",
        "fields": "files(id,name,mimeType,createdTime)",
        "orderBy": "createdTime",
        "pageSize": 200,
    }
    headers = {"Authorization": f"Bearer {drive_token}"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if not resp.ok:
        print(f"  Error de la API de Drive ({resp.status_code}): {resp.text}")
    resp.raise_for_status()
    files = resp.json().get("files", [])
    return [f for f in files if f["id"] not in already_processed]


def download_file(drive_token, file_id):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    headers = {"Authorization": f"Bearer {drive_token}"}
    resp = requests.get(url, headers=headers, params={"alt": "media"}, timeout=60)
    resp.raise_for_status()
    return resp.content


def extraer_datos_documento(file_bytes, mime_type):
    file_b64 = base64.b64encode(file_bytes).decode("utf-8")

    if mime_type == "application/pdf":
        content_block = {"type": "document", "source": {
            "type": "base64", "media_type": "application/pdf", "data": file_b64
        }}
    elif mime_type in IMAGE_MIME_TYPES:
        content_block = {"type": "image", "source": {
            "type": "base64", "media_type": IMAGE_MIME_TYPES[mime_type], "data": file_b64
        }}
    else:
        # Otros formatos de oficina (docx, xlsx, etc.) no tienen bloque
        # nativo en la API de mensajes; se maneja como documento genérico
        # solo si es PDF/imagen. Para el resto, se registra como error.
        raise ValueError(f"tipo de archivo no soportado para extraccion: {mime_type}")

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": CLAUDE_MODEL,
            "max_tokens": 1024,
            "system": EXTRACCION_PROMPT,
            "messages": [{
                "role": "user",
                "content": [
                    content_block,
                    {"type": "text", "text": "Analiza este documento."}
                ]
            }]
        },
        timeout=120,
    )
    if not resp.ok:
        raise RuntimeError(f"Anthropic API {resp.status_code}: {resp.text[:500]}")
    data = resp.json()
    text = "".join(b["text"] for b in data["content"] if b["type"] == "text")
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def crear_documento_notion(titulo, resumen, fecha, drive_file_id):
    archivo_url = f"https://drive.google.com/file/d/{drive_file_id}/view"
    properties = {
        "Nombre": {"title": [{"text": {"content": titulo}}]},
        "Descripción": {"rich_text": [{"text": {"content": resumen}}]},
        "Link": {"url": archivo_url},
    }
    if fecha and FECHA_RE.match(fecha):
        properties["Fecha de Creación"] = {"date": {"start": fecha}}

    payload = {
        "parent": {"data_source_id": DOCUMENTOS_DS_ID},
        "properties": properties,
    }
    resp = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS,
                          json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Notion API {resp.status_code}: {resp.text[:500]}")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
            state.setdefault("requiere_revision", [])
            return state
    return {"processed_file_ids": [], "requiere_revision": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    state = load_state()

    # Compatibilidad con entradas viejas de requiere_revision que no tienen
    # el campo "retryable" todavia: se clasifican con la misma heuristica.
    for r in state["requiere_revision"]:
        r.setdefault("retryable", es_error_reintentable(r.get("error", "")))

    processed_ids = set(state["processed_file_ids"])
    # Solo los NO reintentables (ej. PDF invalido) bloquean el archivo para
    # siempre. Los reintentables (ej. bloqueo de credito) vuelven a aparecer
    # como "nuevos" en cada corrida hasta que se resuelvan.
    no_reintentables = {r["file_id"] for r in state["requiere_revision"]
                         if not r["retryable"]}

    print("Autenticando con Google Drive (cuenta de servicio)...")
    drive_token = get_drive_access_token()

    print("Buscando documentos nuevos en Drive...")
    new_files = [f for f in list_new_files(drive_token, processed_ids)
                 if f["id"] not in no_reintentables]
    print(f"  {len(new_files)} archivo(s) nuevo(s) o pendiente(s) de reintento")

    if not new_files:
        print("Nada que procesar.")
    else:
        resultados = {}  # file_id -> dict de requiere_revision, o None si se resolvio
        for f in new_files:
            print(f"Procesando {f['name']} ({f['id']}, {f['mimeType']})...")
            try:
                file_bytes = download_file(drive_token, f["id"])
                datos = extraer_datos_documento(file_bytes, f["mimeType"])
                titulo = datos.get("titulo")
                resumen = datos.get("resumen")
                fecha = datos.get("fecha") or ""

                if not titulo or not resumen:
                    raise ValueError(f"extraccion incompleta (titulo={titulo!r} resumen={resumen!r})")

                print(f"  Titulo={titulo!r} Fecha={fecha or '(sin fecha)'}")
                crear_documento_notion(titulo, resumen, fecha, f["id"])
                print("  Creado en Notion.")
                processed_ids.add(f["id"])
                resultados[f["id"]] = None

            except Exception as e:
                error_msg = str(e)
                retryable = es_error_reintentable(error_msg)
                print(f"  ::warning::No se pudo procesar {f['name']} ({f['id']}): {error_msg}")
                resultados[f["id"]] = {
                    "file_id": f["id"], "name": f["name"],
                    "error": error_msg, "retryable": retryable,
                }

        # Reconstruir requiere_revision: sacar las entradas de archivos que
        # se tocaron en esta corrida (se resolvieron o se reintentaron) y
        # agregar los resultados nuevos, para no duplicar entradas.
        revision_restante = [r for r in state["requiere_revision"]
                              if r["file_id"] not in resultados]
        revision_nueva = [r for r in resultados.values() if r is not None]

        state["processed_file_ids"] = sorted(processed_ids)
        state["requiere_revision"] = revision_restante + revision_nueva
        save_state(state)
        print("processed_documentos_importantes.json actualizado.")

        manuales = [r for r in revision_nueva if not r["retryable"]]
        reintentables = [r for r in revision_nueva if r["retryable"]]
        if manuales:
            print(f"::warning::{len(manuales)} documento(s) requieren carga manual "
                  f"(ver 'requiere_revision' en {STATE_FILE}).")
        if reintentables:
            print(f"::warning::{len(reintentables)} documento(s) fallaron de nuevo "
                  f"pero son reintentables (se probaran en la proxima corrida).")
