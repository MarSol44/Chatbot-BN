"""
Backend local para el Repositorio QA (Banco de la Nación).

Qué hace distinto a la versión anterior:

 1. EL CONTEXTO VIVE EN EL SERVIDOR, NO EN EL NAVEGADOR.
    Al arrancar, este archivo lee asistenteqabn.html, extrae toda la base de
    conocimiento (módulos 02–11, las 387 transacciones SaraWeb, el índice de
    módulos) y la convierte en texto plano. El navegador ya no manda 36 KB de
    contexto en cada pregunta: solo manda la pregunta.

 2. PROMPT ESTABLE = CACHÉ DE PREFIJO DE OLLAMA.
    El system prompt se construye UNA sola vez al arrancar y no cambia nunca
    (byte por byte). Ollama reutiliza el KV-cache de ese prefijo, así que la
    documentación completa se procesa una única vez; cada pregunta posterior
    solo evalúa los tokens nuevos. Esto es lo que evita las esperas de minutos.

 3. WARMUP + KEEP-ALIVE.
    Un hilo en segundo plano carga el modelo y calienta el caché apenas
    arranca el servidor, y lo revisa cada 3 minutos. El modelo se queda en RAM
    (keep_alive=8h) en vez de descargarse a los 5 minutos y tener que recargar
    2.5 GB en la siguiente consulta.

 4. RESPUESTA EN STREAMING (SSE).
    El texto llega token a token. La interfaz nunca se queda "colgada" ni
    depende de un timeout de 120 s.

 5. TOLERANCIA A FALLOS.
    Reintentos con backoff, arranque automático de `ollama serve` si no
    responde, verificación del modelo, y una sola generación a la vez (evita
    que dos peticiones en paralelo se desalojen el caché mutuamente).

SEGURIDAD: el módulo 01 (enlaces y credenciales del banco) se EXCLUYE del
contexto que ve el modelo, igual que antes. Solo se le dice qué servicios
existen por nombre, nunca URLs internas, usuarios ni claves.

Requisitos:
  1. Ollama corriendo            https://ollama.com/download
  2. ollama pull qwen2.5:1.5b-instruct
  3. pip install flask requests

Uso:
  python server.py          →  http://localhost:5000

Nota de rendimiento: por defecto se usa qwen2.5:1.5b-instruct en modo "smart"
(~1.5k tokens de prompt en vez de ~10k) porque este equipo tiene poca RAM libre
(14.8 GB totales, <1-4 GB libres con el resto de apps abiertas) y sin GPU
dedicada. Con phi4-mini + modo "full" el sistema entraba en swapping y una
respuesta tardaba 2-8+ minutos. Si en tu equipo sobra RAM y quieres más calidad
de respuesta, puedes volver a QA_MODEL=phi4-mini QA_CTX_MODE=full QA_NUM_CTX=12288.

Variables de entorno útiles:
  QA_MODEL=qwen2.5:1.5b-instruct  modelo de Ollama
  QA_CTX_MODE=full|smart    full = toda la doc en el prompt
                            smart = solo índice + fichas relevantes (por defecto,
                            más rápido en equipos lentos o con poca RAM)
  QA_NUM_CTX=4096           ventana de contexto
  QA_HOST=127.0.0.1         cámbialo a 0.0.0.0 SOLO dentro de la red interna
  QA_PORT=5000
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from html import unescape
from pathlib import Path

import requests
from flask import (Flask, Response, jsonify, request, send_from_directory,
                   stream_with_context)
from werkzeug.utils import secure_filename

import ingest

# --------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_FILE = "asistenteqabn.html"
HTML_PATH = os.path.join(BASE_DIR, HTML_FILE)
ADMIN_KB_PATH = os.path.join(BASE_DIR, "admin_kb.json")
ADMIN_UPLOADS_DIR = os.path.join(BASE_DIR, "admin_uploads")
os.makedirs(ADMIN_UPLOADS_DIR, exist_ok=True)

MAX_UPLOAD_MB = 80
ALLOWED_UPLOAD_EXT = {".txt", ".csv", ".docx", ".xlsx", ".xlsm", ".pptx",
                      ".pdf", ".zip", ".png", ".jpg", ".jpeg", ".bmp",
                      ".tif", ".tiff", ".webp"}


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


OLLAMA = _env("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
CHAT_URL = f"{OLLAMA}/api/chat"
TAGS_URL = f"{OLLAMA}/api/tags"
PS_URL = f"{OLLAMA}/api/ps"

MODEL = _env("QA_MODEL", "qwen2.5:1.5b-instruct")
CTX_MODE = _env("QA_CTX_MODE", "smart").lower()          # full | smart
NUM_CTX = int(_env("QA_NUM_CTX", "4096"))   # índice + fichas relevantes + pregunta + respuesta
NUM_PREDICT = int(_env("QA_NUM_PREDICT", "200"))   # este modelo no siempre emite
                                                     # un token de fin: si lo dejamos
                                                     # correr se pone a repetir pasos
                                                     # ya dichos. Un límite corto lo
                                                     # corta justo después de la
                                                     # respuesta útil (más rápido
                                                     # y sin relleno repetido).
TEMPERATURE = float(_env("QA_TEMPERATURE", "0"))
KEEP_ALIVE = _env("QA_KEEP_ALIVE", "8h")
AUTOSTART_OLLAMA = _env("QA_AUTOSTART_OLLAMA", "1") == "1"
HOST = _env("QA_HOST", "127.0.0.1")
PORT = int(_env("QA_PORT", "5000"))

MAX_HISTORY_MSGS = 6        # 3 turnos de ida y vuelta
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 900          # el streaming manda datos constantemente

GUARDRAIL = ("No dispongo de información documentada en mi versión actual "
             "para este tema. Por favor, consulta con un analista senior.")

app = Flask(__name__, static_folder=".")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024


# --------------------------------------------------------------------------
# 1. Extracción del conocimiento desde el HTML
# --------------------------------------------------------------------------
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(s: str) -> str:
    """HTML → texto plano legible para el modelo."""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n- ", s, flags=re.I)
    s = re.sub(r"</(p|h[1-6]|tr|div|ul|ol|table|pre)>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)
    s = _TAG_RE.sub("", s)
    s = unescape(s)
    s = re.sub(r"[ \t ]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _drop_interpolations(s: str) -> str:
    """Elimina los `${ ... }` que queden, respetando llaves anidadas."""
    out, i, n = [], 0, len(s)
    while i < n:
        if s[i] == "$" and i + 1 < n and s[i + 1] == "{":
            depth, i = 1, i + 2
            while i < n and depth:
                if s[i] == "{":
                    depth += 1
                elif s[i] == "}":
                    depth -= 1
                i += 1
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def _template_literal(raw: str) -> str:
    """
    Devuelve el contenido del primer template literal de `raw`.

    No sirve un rfind(backtick): fichas como la 10.1 traen después del cuerpo un
    handler `after:(root)=>{...}` con sus propios templates anidados. Hay que
    escanear respetando las interpolaciones `${ }`.
    """
    first = raw.find("`")
    if first == -1:
        return raw
    i, depth, n = first + 1, 0, len(raw)
    while i < n:
        c = raw[i]
        if c == "\\":
            i += 2
            continue
        if c == "$" and raw[i + 1:i + 2] == "{":
            depth += 1
            i += 2
            continue
        if depth:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
        elif c == "`":
            return raw[first + 1:i]
        i += 1
    return raw[first + 1:]


def _clean_js_body(raw: str, n_trx: int, n_links: int) -> str:
    """Extrae el template literal de `body:` y lo convierte en texto plano."""
    body = _template_literal(raw)

    # interpolaciones que sí sabemos resolver
    body = body.replace("${GUARDRAIL}", GUARDRAIL)
    body = body.replace("${DATA.trx.length}", str(n_trx))
    body = body.replace("${DATA.links.length}", str(n_links))
    body = re.sub(r"\$\{\s*trxTable\([^{}]*\)\s*\}",
                  "[tabla completa de transacciones SaraWeb: se consulta aparte]", body)
    body = re.sub(r"\$\{\s*linksTable\(\)\s*\}",
                  "[tabla de accesos y credenciales: no disponible para la IA]", body)

    body = _drop_interpolations(body)
    body = body.replace("`", "")
    return strip_html(body)


_ENTRY_RE = re.compile(
    r'id\s*:\s*"([^"]+)"\s*,\s*mod\s*:\s*"([^"]+)"\s*,\s*title\s*:\s*"([^"]*)"')


# Palabras genéricas que no deben contar como coincidencia de búsqueda: sin
# esto, una ficha ruidosa (sacada de OCR de una captura de pantalla) termina
# ganándole a la ficha correcta solo por compartir "que", "del" o "día" con
# la pregunta.
_QUERY_STOPWORDS = {
    "que", "de", "la", "el", "en", "con", "un", "una", "unos", "unas",
    "para", "los", "las", "del", "y", "o", "al", "es", "su", "sus", "se",
    "por", "como", "lo", "si", "no", "mas", "este", "esta", "estos",
    "estas", "ese", "esa", "ya", "le", "les", "fue", "son", "ser", "hay",
    "cual", "donde", "cuando", "quien", "me", "mi", "tu", "te", "he", "ha",
    "han", "sobre", "desde", "hasta", "porque", "dia", "dias", "muy", "uno",
}


class Knowledge:
    """Todo el conocimiento de la página, ya en texto plano."""

    def __init__(self) -> None:
        self.modules: list[dict] = []
        self.entries: list[dict] = []
        self.trx: list[dict] = []
        self.link_names: list[str] = []
        self.system_prompt: str = ""
        self.loaded_at: float = 0.0
        self.error: str | None = None

    # -- carga ------------------------------------------------------------
    def load(self) -> None:
        try:
            html = open(HTML_PATH, encoding="utf-8").read()
        except OSError as e:
            self.error = f"No se pudo leer {HTML_FILE}: {e}"
            return

        # load() es re-invocable (cada subida en Admin dispara una recarga):
        # hay que vaciar antes de volver a parsear o cada llamada duplica
        # todo lo anterior.
        self.modules = []
        self.entries = []
        self.trx = []
        self.link_names = []

        self._parse_dataset(html)
        self._parse_modules(html)
        self._parse_kb(html)
        self._load_admin()
        self.system_prompt = self._build_system_prompt()
        self.loaded_at = time.time()
        self.error = None

    def _parse_dataset(self, html: str) -> None:
        m = re.search(r'<script id="dataset"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            return
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            return
        self.trx = data.get("trx", [])
        # SOLO nombres. Nunca URLs internas, usuarios ni claves.
        self.link_names = [l.get("n", "") for l in data.get("links", []) if l.get("n")]

    def _parse_modules(self, html: str) -> None:
        m = re.search(r"const MODULES\s*=\s*\[(.*?)\];", html, re.S)
        if not m:
            return
        for mm in re.finditer(
                r'id\s*:\s*"([^"]+)"\s*,\s*name\s*:\s*"([^"]*)"\s*,\s*status\s*:\s*"([^"]*)"',
                m.group(1)):
            self.modules.append({"id": mm.group(1), "name": mm.group(2),
                                 "status": mm.group(3)})

    def _parse_kb(self, html: str) -> None:
        start = html.find("const KB = [")
        if start == -1:
            return
        end = html.find("\n];", start)
        block = html[start:end if end != -1 else len(html)]

        hits = list(_ENTRY_RE.finditer(block))
        for i, h in enumerate(hits):
            tail = hits[i + 1].start() if i + 1 < len(hits) else len(block)
            raw = block[h.end():tail]
            body = _clean_js_body(raw, len(self.trx), len(self.link_names))
            kw = re.search(r"kw\s*:\s*\[([^\]]*)\]", raw)
            src = re.search(r'src\s*:\s*"([^"]*)"', raw)
            self.entries.append({
                "id": h.group(1),
                "mod": h.group(2),
                "title": h.group(3),
                "body": body,
                "kw": re.findall(r'"([^"]+)"', kw.group(1)) if kw else [],
                "src": src.group(1) if src else "",
                "source": "html",
            })

    def _load_admin(self) -> None:
        """Fichas agregadas desde el modo ADMINISTRADOR (admin_kb.json)."""
        if not os.path.isfile(ADMIN_KB_PATH):
            return
        try:
            data = json.loads(Path(ADMIN_KB_PATH).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for e in data:
            self.entries.append({
                "id": e["id"],
                "mod": e.get("mod", "13"),
                "title": e.get("title", "(sin título)"),
                "body": e.get("body", ""),
                "kw": e.get("kw", []),
                "src": e.get("source_filename", ""),
                "source": "admin",
            })

    # -- texto para el prompt ---------------------------------------------
    @property
    def public_entries(self) -> list[dict]:
        """Todo menos el módulo 01 (credenciales) del HTML original.
        Las credenciales subidas por un ADMINISTRADOR sí entran: el equipo
        de QA decidió que todo el área debe poder consultarlas por chat."""
        return [e for e in self.entries
                if e["mod"] != "01" or e.get("source") == "admin"]

    def entry_text(self, e: dict) -> str:
        head = f"### FICHA {e['id']} — {e['title']}"
        if e["src"]:
            head += f"  (fuente: {e['src']})"
        return f"{head}\n{e['body']}"

    def index_text(self) -> str:
        # El 12 es un modo de la interfaz (chat directo), no documentación:
        # no entra en el índice para no confundir al modelo.
        lines = [f"- {m['id']}_{m['name']} ({m['status']})"
                 for m in self.modules if m["id"] != "12"]
        fichas = [f"  · {e['id']} {e['title']}" for e in self.public_entries]
        return ("MÓDULOS DEL REPOSITORIO:\n" + "\n".join(lines) +
                "\n\nFICHAS DISPONIBLES:\n" + "\n".join(fichas))

    def _build_system_prompt(self) -> str:
        reglas = f"""Eres el asistente interno del área de Control de Calidad (QA) del Banco de la Nación.
Hablas con analistas de QA del banco. Respondes en español, en pocas líneas, directo y sin rodeos.

REGLAS DURAS:
1. Respondes ÚNICAMENTE con lo que está en la DOCUMENTACIÓN de abajo. Es tu única fuente.
2. LOS COMANDOS SE COPIAN LETRA POR LETRA. Nunca los escribes de memoria ni los abrevias:
   los lees de la documentación y los reproduces idénticos. Un nombre como CCICSFOR o
   TOLDVINI con una sola letra distinta es un error grave, peor que no responder.
   Si no puedes copiar un comando con total exactitud, no lo escribas.
3. No inventas procedimientos, transacciones, rutas, servidores ni credenciales.
4. NO CITES números de ficha, de módulo ni nombres de archivo fuente. La interfaz ya le
   muestra al analista la ficha verificada junto a tu respuesta; si los inventas, lo
   confundes. Habla del procedimiento, no de dónde está guardado.
   NUNCA copies literalmente encabezados como "### FICHA ... — ... (fuente: ...)": esos
   son marcas internas para ti, no contenido para el analista. Si una parte de la
   documentación se ve como texto ilegible, cortado o sin sentido (típico de una foto o
   una captura de pantalla mal escaneada), NO la repitas ni la parafrasees palabra por
   palabra esperando que tenga sentido: ignórala y usa solo las partes que sí se entienden
   con claridad. Repetir texto que ni tú puedes leer no ayuda al analista, lo confunde más.
5. Cuando expliques un procedimiento con varios pasos, respétalos en orden y no te saltes
   ninguno. Si la documentación indica una verificación intermedia, la incluyes.
6. Si la pregunta NO está cubierta por la documentación, respondes exactamente esto y nada más:
   "{GUARDRAIL}"
7. Enlaces, usuarios y contraseñas internos (BDUC, WebSphere, SaraWeb, etc.): NO son un tema
   de privacidad para ti. El área de QA del banco ya autorizó que todo el equipo los consulte
   por este chat — es exactamente para eso que están en la documentación. Si la documentación
   adjunta los incluye, los entregas y los copias exactos, letra por letra (regla 2), SIN
   negarte, SIN advertencias de privacidad y SIN redirigir a "un analista" o "la autoridad
   nacional" — nada de eso existe aquí, es información interna de trabajo del propio analista
   que te está preguntando. Negarte a darlos cuando SÍ están documentados es un error, igual de
   grave que inventarlos. Si NO aparecen en la documentación adjunta, ahí sí dices que no están
   en tu contexto y que revisen el módulo 01_Links — pero nunca inventes un motivo de política
   o privacidad que no está en estas reglas.
8. Si la pregunta es ambigua, respondes con lo más cercano que sí esté documentado y dices
   qué parte no está cubierta.
9. Sé breve. En cuanto termines los pasos o la respuesta, PARAS. Nunca repites un paso ya
   dicho ni reformulas lo mismo con otras palabras para "completar" la respuesta: repetirte
   es un error, no una forma de ser más completo.

Accesos registrados en el repositorio (solo nombres, sin URL ni credenciales):
{", ".join(self.link_names) if self.link_names else "—"}

Hay {len(self.trx)} transacciones SaraWeb registradas. Cuando la consulta involucre alguna,
te las adjuntan en el mensaje del usuario bajo el encabezado "TRANSACCIONES RELACIONADAS".
"""
        indice = self.index_text()

        if CTX_MODE == "smart":
            cuerpo = ("=== ÍNDICE DE LA DOCUMENTACIÓN ===\n" + indice +
                      "\n=== FIN ÍNDICE ===\n"
                      "Las fichas relevantes a cada consulta se te adjuntan en el mensaje "
                      "del usuario bajo 'DOCUMENTACIÓN RELEVANTE'.")
        else:
            fichas = "\n\n".join(self.entry_text(e) for e in self.public_entries)
            cuerpo = ("=== ÍNDICE ===\n" + indice +
                      "\n\n=== DOCUMENTACIÓN COMPLETA ===\n" + fichas +
                      "\n=== FIN DOCUMENTACIÓN ===")

        return reglas + "\n" + cuerpo

    # -- recuperación por consulta ----------------------------------------
    @staticmethod
    def _norm(s: str) -> str:
        s = s.lower()
        for a, b in zip("áéíóúüñ", "aeiouun"):
            s = s.replace(a, b)
        return s

    @staticmethod
    def _raw_words(nq: str) -> set[str]:
        return {w for w in re.split(r"[^a-z0-9ñ]+", nq) if w}

    def score_entry(self, e: dict, q: str) -> float:
        nq = self._norm(q)
        nq_words = self._raw_words(nq)
        toks = [t for t in re.split(r"[^a-z0-9]+", nq)
                if len(t) > 2 and t not in _QUERY_STOPWORDS]
        if not toks:
            return 0.0
        kw = e["kw"]
        # Una ficha ruidosa (sacada de OCR de una captura de pantalla) puede
        # traer 200+ "palabras clave" basura. Sin este freno, el solo volumen
        # de esa lista le gana a una ficha pequeña y precisa que sí tiene la
        # respuesta ("03_Canales" perdía contra un trozo cualquiera de la
        # guía de inicio de día). El aporte de cada coincidencia se diluye
        # cuando la lista de keywords es enorme.
        dampen = min(1.0, 25.0 / (len(kw) or 1))
        s = 0.0
        matched_toks: set[str] = set()
        for k in kw:
            nk = self._norm(k)
            if not nk or nk in _QUERY_STOPWORDS or len(nk) <= 2:
                continue
            is_phrase = " " in nk
            # Coincidencia por PALABRA COMPLETA, no por substring: si no, una
            # keyword corta como "ato" o "cuenta" hace match dentro de
            # cualquier palabra que la contenga ("gATOs", "cuentame") y trae
            # fichas que no tienen nada que ver con la pregunta.
            hit = (nk in nq_words) if not is_phrase else (
                re.search(r"\b" + re.escape(nk) + r"\b", nq) is not None
            )
            if hit:
                s += 9 * (1.0 if is_phrase else dampen)
                matched_toks.update(t for t in toks if t in nk or nk in t)
        nt = self._norm(e["title"])
        for t in toks:
            if len(t) >= 3 and t in nt:
                s += 8
                matched_toks.add(t)
        # Una ficha larga (p.ej. sacada de un docx grande) acumula keywords de
        # sobra y puede ganarle a la ficha correcta con una sola palabra suelta
        # en común ("bduc" aparece tanto en el manual de links como en uno de
        # apertura de cuenta que nada tiene que ver). Premiar que la ficha
        # cubra VARIAS palabras distintas de la pregunta, no solo una,
        # corrige justo ese caso.
        if len(toks) >= 2:
            s += 6 * max(0, len(matched_toks) - 1)
        # Las fichas curadas a mano (módulos 02-11 del propio HTML) son de
        # fiar; las admin son texto crudo de OCR/ingesta automática, más
        # ruidoso. Ante un empate, gana la curada.
        if e.get("source") == "html":
            s *= 1.25
        return round(s, 1)

    def relevant_entries(self, q: str, k: int = 3) -> list[dict]:
        scored = [(e, self.score_entry(e, q)) for e in self.public_entries]
        scored.sort(key=lambda p: -p[1])
        if not scored or scored[0][1] < 6:
            return []
        top = scored[0][1]
        # Antes se metían hasta 5 fichas al contexto aunque solo una fuera
        # realmente relevante (p.ej. preguntar por el link de BDUC traía
        # también un manual de apertura de cuentas que solo comparte esa
        # palabra suelta). Un modelo chico, con varios documentos distintos
        # delante, tiende a hacerle caso al que quede más cerca de la
        # pregunta en vez de al más relevante — así que en vez de rellenar
        # con lo que sea que llegue a un piso fijo, solo se incluye lo que
        # esté realmente compitiendo con la mejor ficha (score cercano al
        # de la mejor), y como mucho `k`.
        picked = [e for e, s in scored[:k] if s >= max(6, top * 0.6)]
        # La ficha más relevante va AL FINAL (más cerca de la pregunta):
        # es la parte del prompt a la que más caso le hace el modelo.
        return list(reversed(picked))

    def relevant_trx(self, q: str, limit: int = 25) -> list[dict]:
        nq = self._norm(q)
        nums = re.findall(r"\b(\d{4})\b", nq)
        hits = [t for t in self.trx if t.get("t") in nums]
        if len(hits) < limit:
            toks = [t for t in re.split(r"[^a-z0-9]+", nq) if len(t) > 3]
            for t in self.trx:
                if t in hits:
                    continue
                blob = self._norm(f"{t.get('d','')} {t.get('b','')}")
                if any(tok in blob for tok in toks):
                    hits.append(t)
                if len(hits) >= limit:
                    break
        return hits[:limit]

    @staticmethod
    def trx_text(rows: list[dict]) -> str:
        out = []
        for t in rows:
            extra = " · ".join(filter(None, [
                t.get("b"), f"HOST {t['host']}" if t.get("host") else "",
                t.get("open"), f"impacto {t['imp']}" if t.get("imp") else "",
                f"requisitos: {t['req']}" if t.get("req") else "",
            ]))
            out.append(f"- TXN {t.get('t')}: {t.get('d')} ({extra})")
        return "\n".join(out)

    def stats(self) -> dict:
        return {
            "modulos": len(self.modules),
            "fichas": len(self.entries),
            "fichas_en_contexto": len(self.public_entries),
            "transacciones": len(self.trx),
            "accesos": len(self.link_names),
            "system_prompt_chars": len(self.system_prompt),
            "system_prompt_tokens_aprox": len(self.system_prompt) // 3,
            "ctx_mode": CTX_MODE,
        }


KB = Knowledge()


# --------------------------------------------------------------------------
# 2. Construcción de mensajes
# --------------------------------------------------------------------------
def build_messages(question: str, history: list[dict]) -> list[dict]:
    """El system prompt es SIEMPRE idéntico → Ollama reutiliza su caché."""
    msgs = [{"role": "system", "content": KB.system_prompt}]

    for h in history[-MAX_HISTORY_MSGS:]:
        role = h.get("role")
        content = (h.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content[:2000]})

    partes = []
    if CTX_MODE == "smart":
        rel = KB.relevant_entries(question, k=3)
        if rel:
            partes.append("DOCUMENTACIÓN RELEVANTE:\n" +
                          "\n\n".join(KB.entry_text(e) for e in rel))
    else:
        rel = KB.relevant_entries(question, k=3)
        if rel:
            partes.append("FICHAS MÁS PROBABLES PARA ESTA CONSULTA (ya están arriba "
                          "completas, se listan como pista): " +
                          ", ".join(f"{e['id']} {e['title']}" for e in rel))

    trx = KB.relevant_trx(question)
    if trx:
        partes.append("TRANSACCIONES RELACIONADAS:\n" + KB.trx_text(trx))

    partes.append(f"PREGUNTA DEL ANALISTA: {question}")
    msgs.append({"role": "user", "content": "\n\n".join(partes)})
    return msgs


def chat_payload(messages: list[dict], stream: bool, num_predict: int | None = None) -> dict:
    return {
        "model": MODEL,
        "messages": messages,
        "stream": stream,
        "keep_alive": KEEP_ALIVE,
        "options": {
            "num_ctx": NUM_CTX,
            "num_predict": NUM_PREDICT if num_predict is None else num_predict,
            # temperature 0 y repeat_penalty 1.0 a propósito: con 0.15/1.05 el
            # modelo escribió "/c ccicfor" en vez de "/c ccicsfor". La penalización
            # por repetición castiga justo los nombres que más se repiten en la
            # documentación (CCICSFOR, TOLDVINI...) y le come letras. Aquí un
            # comando mal copiado es peor que no responder.
            "temperature": TEMPERATURE,
            "top_p": 1.0,
            "repeat_penalty": 1.0,
        },
    }


# --------------------------------------------------------------------------
# 3. Estado del motor / warmup / auto-arranque
# --------------------------------------------------------------------------
class Engine:
    def __init__(self) -> None:
        self.lock = threading.Lock()      # una generación a la vez
        self.state = "iniciando"          # iniciando|calentando|listo|error
        self.detail = ""
        self.warm_seconds = 0.0
        self.last_check = 0.0

    def snapshot(self) -> dict:
        return {"state": self.state, "detail": self.detail,
                "warm_seconds": round(self.warm_seconds, 1),
                "model": MODEL, "num_ctx": NUM_CTX}


ENGINE = Engine()


def ollama_up() -> bool:
    try:
        return requests.get(TAGS_URL, timeout=4).ok
    except requests.RequestException:
        return False


def try_start_ollama() -> bool:
    """Levanta `ollama serve` si el binario existe y el puerto no responde."""
    if not AUTOSTART_OLLAMA or ollama_up():
        return ollama_up()
    try:
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        subprocess.Popen(["ollama", "serve"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         creationflags=flags)
    except (OSError, ValueError):
        return False
    for _ in range(20):
        time.sleep(1)
        if ollama_up():
            return True
    return False


def model_present() -> bool:
    try:
        tags = requests.get(TAGS_URL, timeout=5).json().get("models", [])
    except (requests.RequestException, ValueError):
        return False
    want = MODEL.split(":")[0]
    return any(m.get("name", "").split(":")[0] == want for m in tags)


def model_loaded() -> bool:
    try:
        ps = requests.get(PS_URL, timeout=4).json().get("models", [])
    except (requests.RequestException, ValueError):
        return False
    want = MODEL.split(":")[0]
    return any(m.get("name", "").split(":")[0] == want for m in ps)


def warm_up(reason: str = "arranque") -> None:
    """Carga el modelo y calienta el caché de prefijo del system prompt."""
    ENGINE.state = "calentando"
    ENGINE.detail = f"procesando la documentación ({reason})"
    t0 = time.time()
    payload = chat_payload(
        [{"role": "system", "content": KB.system_prompt},
         {"role": "user", "content": "ok"}],
        stream=False, num_predict=1)
    try:
        with ENGINE.lock:
            r = requests.post(CHAT_URL, json=payload,
                              timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        r.raise_for_status()
        ENGINE.warm_seconds = time.time() - t0
        ENGINE.state = "listo"
        ENGINE.detail = ""
        print(f"[QA] IA local lista en {ENGINE.warm_seconds:.1f}s "
              f"({KB.stats()['system_prompt_tokens_aprox']} tokens de doc en caché)")
    except requests.RequestException as e:
        ENGINE.state = "error"
        ENGINE.detail = str(e)
        print(f"[QA] Warmup falló: {e}")


def boot_thread() -> None:
    if not try_start_ollama():
        ENGINE.state = "error"
        ENGINE.detail = ("Ollama no responde en " + OLLAMA +
                         ". Abre otra terminal y ejecuta: ollama serve")
        print("[QA] " + ENGINE.detail)
        return
    if not model_present():
        ENGINE.state = "error"
        ENGINE.detail = f"El modelo '{MODEL}' no está descargado. Ejecuta: ollama pull {MODEL}"
        print("[QA] " + ENGINE.detail)
        return
    warm_up("arranque")

    # vigilancia: si el modelo se descarga de RAM, se vuelve a calentar
    while True:
        time.sleep(180)
        ENGINE.last_check = time.time()
        if not ollama_up():
            ENGINE.state = "error"
            ENGINE.detail = "Ollama dejó de responder."
            try_start_ollama()
            continue
        if not model_loaded() and ENGINE.state != "calentando":
            warm_up("el modelo se descargó de memoria")


# --------------------------------------------------------------------------
# 4. Rutas
# --------------------------------------------------------------------------
@app.after_request
def no_store(resp):
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route("/")
def home():
    return send_from_directory(BASE_DIR, HTML_FILE)


@app.route("/api/health")
def health():
    return jsonify({**ENGINE.snapshot(), "kb": KB.stats(), "kb_error": KB.error,
                    "ollama": OLLAMA})


@app.route("/api/debug-relevant")
def debug_relevant():
    """TEMPORAL: para depurar qué fichas se están usando como contexto."""
    q = request.args.get("q", "")
    rel = KB.relevant_entries(q, k=5)
    anchored = has_documental_anchor(q, [])
    return jsonify({
        "question": q,
        "anchored": anchored,
        "best_score": max((KB.score_entry(e, q) for e in KB.public_entries), default=0),
        "relevant": [{"id": e["id"], "title": e["title"], "mod": e["mod"],
                      "score": KB.score_entry(e, q), "kw_count": len(e["kw"])}
                    for e in rel],
    })


@app.route("/api/reload-kb", methods=["POST"])
def reload_kb():
    """Re-lee el HTML y vuelve a calentar. Útil tras editar la documentación."""
    KB.load()
    threading.Thread(target=warm_up, args=("recarga de la KB",), daemon=True).start()
    return jsonify({"ok": KB.error is None, "kb": KB.stats(), "error": KB.error})


# --------------------------------------------------------------------------
# 4b. Modo ADMINISTRADOR: subir documentos/fotos o escribir notas que pasan
#     a formar parte de la base de conocimiento del chat.
# --------------------------------------------------------------------------
def _read_admin_kb() -> list[dict]:
    if not os.path.isfile(ADMIN_KB_PATH):
        return []
    try:
        return json.loads(Path(ADMIN_KB_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _write_admin_kb(rows: list[dict]) -> None:
    Path(ADMIN_KB_PATH).write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


_MODPFX_RE = re.compile(r"^(\d{2})[_\-]")


def _guess_mod(filename: str) -> str:
    m = _MODPFX_RE.match(filename)
    if m and any(mm["id"] == m.group(1) for mm in KB.modules):
        return m.group(1)
    return "13"


def _reload_and_rewarm() -> None:
    KB.load()
    threading.Thread(target=warm_up, args=("actualización desde Admin",), daemon=True).start()


_STOPWORDS = {"de", "la", "el", "los", "las", "un", "una", "y", "en", "para",
             "con", "del", "al", "por", "que", "su", "a", "o", "the", "and",
             # ruido que nosotros mismos inyectamos al extraer el texto:
             # si no se excluye, hace que TODAS las fichas "matcheen" un poco
             # con cualquier pregunta y diluye la búsqueda real.
             "pagina", "página", "hoja", "texto", "imagen", "incrustada",
             "diapositiva"}


def _humanize_title(raw: str) -> str:
    t = re.sub(r"[_\-]+", " ", raw).strip()
    return re.sub(r"\s{2,}", " ", t)


def _auto_keywords(*texts: str) -> list[str]:
    """Palabras clave para retrieval: NO solo del título — si solo miráramos
    el título, una ficha como '01 Links Certi' nunca matchearía "bduc" o
    "websphere" aunque esas palabras estén en el cuerpo (p.ej. una fila de
    una tabla), y la pregunta se queda sin ficha real de respaldo."""
    blob = " ".join(texts).lower()
    words = re.findall(r"[a-záéíóúñ0-9]{3,}", blob)
    return sorted({w for w in words if w not in _STOPWORDS})


def _add_entries(title_base: str, mod: str, chunks: list[str],
                 source_filename: str) -> int:
    rows = _read_admin_kb()
    added = 0
    clean_title = _humanize_title(title_base)
    for i, chunk in enumerate(chunks, 1):
        if not chunk.strip():
            continue
        suffix = f" ({i}/{len(chunks)})" if len(chunks) > 1 else ""
        rows.append({
            "id": f"ADM-{uuid.uuid4().hex[:8]}",
            "mod": mod,
            "title": f"{clean_title}{suffix}",
            "body": chunk.strip(),
            "kw": _auto_keywords(clean_title, chunk),
            "source_filename": source_filename,
            "added_at": time.strftime("%Y-%m-%d %H:%M"),
        })
        added += 1
    _write_admin_kb(rows)
    return added


@app.route("/api/admin/public")
def admin_public():
    """Fichas admin en el mismo formato que usa el frontend (KB) para poder
    mostrarlas verbatim (renderEntry) en vez de depender solo de la lectura
    del modelo, que puede parafrasear mal un comando."""
    rows = _read_admin_kb()
    out = [{"id": r["id"], "mod": r.get("mod", "13"), "title": r["title"],
           "kw": r.get("kw", []), "body": r["body"], "src": r.get("source_filename", "")}
          for r in rows]
    return jsonify({"entries": out})


@app.route("/api/admin/list")
def admin_list():
    rows = _read_admin_kb()
    rows_sorted = sorted(rows, key=lambda r: r.get("added_at", ""), reverse=True)
    return jsonify({"entries": rows_sorted, "count": len(rows_sorted)})


@app.route("/api/admin/entry/<entry_id>", methods=["DELETE"])
def admin_delete(entry_id):
    rows = _read_admin_kb()
    new_rows = [r for r in rows if r["id"] != entry_id]
    if len(new_rows) == len(rows):
        return jsonify({"error": "No existe esa ficha"}), 404
    _write_admin_kb(new_rows)
    _reload_and_rewarm()
    return jsonify({"ok": True})


@app.route("/api/admin/note", methods=["POST"])
def admin_note():
    data = request.get_json(force=True, silent=True) or {}
    text = (data.get("text") or "").strip()
    title = (data.get("title") or "").strip() or f"Nota admin {time.strftime('%Y-%m-%d %H:%M')}"
    if not text:
        return jsonify({"error": "Falta el texto de la nota"}), 400
    mod = data.get("mod") or "13"
    chunks = ingest.chunk_text(text)
    added = _add_entries(title, mod, chunks, "(nota escrita en Admin)")
    _reload_and_rewarm()
    return jsonify({"ok": True, "entries_added": added})


@app.route("/api/admin/upload", methods=["POST"])
def admin_upload():
    if "file" not in request.files:
        return jsonify({"error": "No se recibió ningún archivo"}), 400
    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Nombre de archivo vacío"}), 400

    safe_name = secure_filename(f.filename) or f"archivo-{uuid.uuid4().hex[:6]}"
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXT:
        return jsonify({"error": f"Formato no permitido: {ext}"}), 400

    stamped = f"{time.strftime('%Y%m%d-%H%M%S')}_{safe_name}"
    saved_path = os.path.join(ADMIN_UPLOADS_DIR, stamped)
    f.save(saved_path)

    results = []  # (title, text, warning)
    if ext == ".zip":
        with tempfile.TemporaryDirectory() as tmp:
            for inner_name, text, warn in ingest.extract_from_zip(saved_path, tmp):
                results.append((f"{safe_name}/{inner_name}", text, warn))
    else:
        text, warn = ingest.extract_text(saved_path)
        results.append((safe_name, text, warn))

    mod = _guess_mod(safe_name)
    total_added, warnings = 0, []
    for title, text, warn in results:
        if warn:
            warnings.append(f"{title}: {warn}")
        if text and text.strip():
            chunks = ingest.chunk_text(text)
            total_added += _add_entries(Path(title).stem, mod, chunks, title)

    if total_added:
        _reload_and_rewarm()

    return jsonify({
        "ok": total_added > 0,
        "filename": safe_name,
        "entries_added": total_added,
        "warnings": warnings,
        "ocr_available": ingest.ocr_available(),
    })


def sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


# El modelo NO tiene las credenciales en su contexto, pero igual se las inventa:
# a "¿cuál es la clave de WebSphere Apps?" respondió "a p42.+". Una clave falsa
# con pinta de real es peligrosa, así que estas preguntas ni siquiera llegan al
# modelo: se responden con texto fijo.
_CRED_RE = re.compile(
    r"\b(clave|claves|contrasen|contraseñ|password|passwd|pwd|credencial|"
    r"credenciales|usuario y clave|user y pass|login de|acceso a)\b", re.I)

CRED_ANSWER = (
    "No manejo usuarios ni contraseñas: quedan fuera de mi contexto a propósito.\n\n"
    "Los accesos están en el módulo 01_Links de esta misma interfaz. Ábrelo en el "
    "menú lateral y busca el servicio que necesitas — cada uno tiene su enlace, "
    "usuario y contraseña por separado.\n\n"
    "Si te doy una clave, es inventada. No la uses."
)


def is_credential_question(q: str) -> bool:
    return bool(_CRED_RE.search(Knowledge._norm(q)))


# Segunda defensa determinista. A "¿cómo configuro un router Cisco en Miraflores?"
# el modelo se inventó seis pasos de configuración de routers y les pegó encima un
# particionado del inicio de día. La regla dura del asistente es no responder lo que
# no está documentado, y un 3.8B no la sostiene solo con el prompt: si la consulta no
# tiene anclaje en la KB, no se le pregunta al modelo.
#
# Umbral medido sobre consultas reales: lo documentado puntúa 11-48, lo ajeno 0-8.
ANCHOR_MIN = 10


def has_documental_anchor(question: str, history: list[dict]) -> bool:
    best = max((KB.score_entry(e, question) for e in KB.public_entries), default=0)
    if best >= ANCHOR_MIN:
        return True

    # número de transacción exacto (las 387 del mapa SaraWeb)
    nums = set(re.findall(r"\b(\d{4})\b", question))
    if nums and any(t.get("t") in nums for t in KB.trx):
        return True

    # seguimiento de una conversación ya anclada ("¿y eso por qué?")
    prev = " ".join(h.get("content", "") for h in history[-4:]
                    if h.get("role") == "user")
    if prev:
        combo = max((KB.score_entry(e, prev + " " + question)
                     for e in KB.public_entries), default=0)
        if combo >= ANCHOR_MIN:
            return True
    return False


def canned_stream(text: str, guard: str) -> Response:
    """Respuesta fija con el mismo formato SSE que usa el modelo."""
    def gen():
        yield sse({"event": "start", "state": ENGINE.state, "warming": False})
        for word in text.split(" "):
            yield sse({"event": "delta", "text": word + " "})
        yield sse({"event": "done", "empty": False, "guard": guard})
    return Response(stream_with_context(gen()), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/ai", methods=["POST"])
def api_ai():
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    history = data.get("history") or []
    if not question:
        return jsonify({"error": "Falta la pregunta"}), 400
    if KB.error:
        return jsonify({"error": KB.error}), 500

    # Cortocircuitos deterministas. Las preguntas de credenciales solo se
    # bloquean si NO hay una ficha real que las respalde (evita que el modelo
    # invente una clave); si el admin subió un documento real con esos datos,
    # se deja pasar como cualquier otra consulta documentada.
    anchored = has_documental_anchor(question, history)
    if is_credential_question(question) and not anchored:
        return canned_stream(CRED_ANSWER, "credenciales")
    if not anchored:
        return canned_stream(GUARDRAIL, "fuera-de-alcance")

    messages = build_messages(question, history)

    def generate():
        yield sse({"event": "start", "state": ENGINE.state,
                   "warming": ENGINE.state in ("iniciando", "calentando")})

        last_err = None
        for intento in range(3):
            try:
                with ENGINE.lock:
                    with requests.post(CHAT_URL, json=chat_payload(messages, True),
                                       stream=True,
                                       timeout=(CONNECT_TIMEOUT, READ_TIMEOUT)) as r:
                        r.raise_for_status()
                        ENGINE.state = "listo"
                        got = False
                        for line in r.iter_lines(decode_unicode=True):
                            if not line:
                                continue
                            try:
                                chunk = json.loads(line)
                            except json.JSONDecodeError:
                                continue
                            if chunk.get("error"):
                                yield sse({"event": "error",
                                           "message": chunk["error"]})
                                return
                            piece = (chunk.get("message") or {}).get("content", "")
                            if piece:
                                got = True
                                yield sse({"event": "delta", "text": piece})
                            if chunk.get("done"):
                                yield sse({
                                    "event": "done",
                                    "empty": not got,
                                    "eval_count": chunk.get("eval_count"),
                                    "prompt_eval_count": chunk.get("prompt_eval_count"),
                                    "total_ms": round(
                                        (chunk.get("total_duration") or 0) / 1e6),
                                })
                                return
                        yield sse({"event": "done", "empty": not got})
                        return

            except requests.exceptions.ConnectionError as e:
                last_err = ("No se pudo conectar con Ollama en " + OLLAMA +
                            ". Verifica que esté corriendo ('ollama serve').")
                yield sse({"event": "retry", "intento": intento + 1,
                           "message": "Reconectando con la IA local..."})
                try_start_ollama()
                time.sleep(1.5 * (intento + 1))
            except requests.exceptions.ReadTimeout:
                last_err = "El modelo tardó demasiado en responder."
                break
            except requests.RequestException as e:
                last_err = f"Error llamando al modelo local: {e}"
                break

        ENGINE.state = "error"
        ENGINE.detail = last_err or "desconocido"
        yield sse({"event": "error", "message": last_err or "Error desconocido."})

    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    # Sin "Connection: keep-alive": PEP 3333 prohíbe los headers
                    # hop-by-hop y waitress aborta la petición con AssertionError.
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


@app.route("/api/ai-fallback", methods=["POST"])
def ai_fallback_compat():
    """Compatibilidad con la versión anterior (sin streaming)."""
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Falta la pregunta"}), 400
    try:
        with ENGINE.lock:
            r = requests.post(
                CHAT_URL,
                json=chat_payload(build_messages(question, data.get("history") or []), False),
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT))
        r.raise_for_status()
    except requests.exceptions.ConnectionError:
        return jsonify({"error": "No se pudo conectar con Ollama. Ejecuta 'ollama serve'."}), 503
    except requests.RequestException as e:
        return jsonify({"error": f"Error llamando al modelo local: {e}"}), 500
    answer = (r.json().get("message") or {}).get("content", "(sin respuesta)")
    return jsonify({"answer": answer})


# --------------------------------------------------------------------------
# 5. Arranque
# --------------------------------------------------------------------------
def main() -> None:
    KB.load()
    if KB.error:
        print(f"[QA] ERROR leyendo la documentación: {KB.error}")
    else:
        s = KB.stats()
        print(f"[QA] Documentación cargada: {s['fichas_en_contexto']} fichas, "
              f"{s['transacciones']} transacciones, {s['modulos']} módulos "
              f"(~{s['system_prompt_tokens_aprox']} tokens, modo {s['ctx_mode']})")

    threading.Thread(target=boot_thread, daemon=True).start()

    print(f"[QA] Abre http://localhost:{PORT}")
    print("[QA] La primera consulta puede tardar mientras el modelo se calienta; "
          "la interfaz te lo indica.")

    try:
        from waitress import serve   # servidor de producción, más estable
        serve(app, host=HOST, port=PORT, threads=8, channel_timeout=1200)
    except ImportError:
        # Servidor de desarrollo de Flask. debug/reloader DESACTIVADOS a
        # propósito: el reloader reinicia el proceso y corta las conexiones.
        app.run(host=HOST, port=PORT, debug=False, threaded=True,
                use_reloader=False)


if __name__ == "__main__":
    # host 127.0.0.1: SOLO accesible desde esta misma PC. Este proyecto contiene
    # credenciales internas del banco en el HTML. Si otras PCs del equipo deben
    # usarlo, arranca con QA_HOST=0.0.0.0 solo dentro de la red interna, nunca
    # expuesto a internet, e idealmente con autenticación agregada.
    main()
