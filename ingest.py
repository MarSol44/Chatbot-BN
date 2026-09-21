"""
Extracción de texto para el modo ADMINISTRADOR del Repositorio QA.

Convierte cualquier archivo que suba un analista (foto, docx, xlsx, pptx, pdf,
txt, zip) en texto plano que luego se guarda como "ficha" en admin_kb.json y
entra al mismo pipeline de retrieval que usa el resto de la documentación.

Las fotos y los PDF escaneados pasan por OCR (Tesseract, español + inglés).
Si Tesseract no está instalado, el resto de formatos sigue funcionando: solo
se pierde la lectura de imágenes.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESSDATA_DIR = os.path.join(BASE_DIR, "tessdata")

TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]

_OCR_READY = False
try:
    import pytesseract
    from PIL import Image

    for _cand in TESSERACT_CANDIDATES:
        if os.path.isfile(_cand):
            pytesseract.pytesseract.tesseract_cmd = _cand
            _OCR_READY = True
            break
    if os.path.isdir(TESSDATA_DIR):
        os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
except ImportError:
    pytesseract = None
    Image = None

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
OCR_LANG = "spa+eng"


def ocr_available() -> bool:
    return _OCR_READY


def _ocr_image(path_or_img) -> str:
    if not _OCR_READY:
        return ""
    try:
        img = path_or_img if hasattr(path_or_img, "size") else Image.open(path_or_img)
        return pytesseract.image_to_string(img, lang=OCR_LANG).strip()
    except Exception as e:
        return f"[OCR falló: {e}]"


def _extract_txt(path: str) -> str:
    for enc in ("utf-8", "latin-1"):
        try:
            return Path(path).read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return Path(path).read_bytes().decode("utf-8", errors="replace")


def _extract_docx(path: str) -> str:
    import docx
    d = docx.Document(path)
    parts = [p.text for p in d.paragraphs if p.text.strip()]
    for tbl in d.tables:
        for row in tbl.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    # imágenes incrustadas (capturas de pantalla, diagramas con texto)
    for rel in d.part.rels.values():
        if "image" in rel.reltype:
            try:
                img = Image.open(__import__("io").BytesIO(rel.target_part.blob))
                txt = _ocr_image(img)
                if txt:
                    parts.append(f"[Texto de imagen incrustada] {txt}")
            except Exception:
                pass
    return "\n".join(parts)


def _extract_xlsx(path: str) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    parts = []
    for ws in wb.worksheets:
        parts.append(f"[Hoja: {ws.title}]")
        for row in ws.iter_rows(values_only=True):
            vals = [str(c) for c in row if c is not None]
            if vals:
                parts.append(" | ".join(vals))
    return "\n".join(parts)


def _extract_pptx(path: str) -> str:
    from pptx import Presentation
    prs = Presentation(path)
    parts = []
    for i, slide in enumerate(prs.slides, 1):
        parts.append(f"[Diapositiva {i}]")
        for shape in slide.shapes:
            if shape.has_text_frame and shape.text_frame.text.strip():
                parts.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        parts.append(" | ".join(cells))
            if shape.shape_type == 13:  # PICTURE
                try:
                    img = Image.open(__import__("io").BytesIO(shape.image.blob))
                    txt = _ocr_image(img)
                    if txt:
                        parts.append(f"[Texto de imagen] {txt}")
                except Exception:
                    pass
    return "\n".join(parts)


def _extract_pdf(path: str) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            txt = (page.extract_text() or "").strip()
            if len(txt) < 20 and _OCR_READY:
                try:
                    im = page.to_image(resolution=200).original
                    ocr_txt = _ocr_image(im)
                    if ocr_txt:
                        txt = (txt + "\n" + ocr_txt).strip()
                except Exception:
                    pass
            if txt:
                parts.append(f"[Página {i}]\n{txt}")
    return "\n\n".join(parts)


def _extract_image(path: str) -> str:
    if not _OCR_READY:
        return "[Imagen subida sin OCR disponible: instala Tesseract-OCR para leer su texto]"
    txt = _ocr_image(path)
    return txt or "[No se detectó texto legible en la imagen]"


_DISPATCH = {
    ".txt": _extract_txt,
    ".csv": _extract_txt,
    ".docx": _extract_docx,
    ".xlsx": _extract_xlsx,
    ".xlsm": _extract_xlsx,
    ".pptx": _extract_pptx,
    ".pdf": _extract_pdf,
}


def extract_text(path: str) -> tuple[str, str | None]:
    """Devuelve (texto, advertencia|None) para un único archivo (no zip)."""
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXT:
        return _extract_image(path), (None if _OCR_READY else
                                       "OCR no disponible: instala Tesseract-OCR")
    fn = _DISPATCH.get(ext)
    if not fn:
        return "", f"Formato no soportado: {ext or '(sin extensión)'}"
    try:
        return fn(path), None
    except Exception as e:
        return "", f"No se pudo leer el archivo: {e}"


def extract_from_zip(path: str, tmp_dir: str) -> list[tuple[str, str, str | None]]:
    """Extrae y procesa cada archivo soportado dentro de un .zip.
    Devuelve una lista de (nombre_interno, texto, advertencia)."""
    out = []
    try:
        zf = zipfile.ZipFile(path)
    except zipfile.BadZipFile as e:
        return [("(archivo completo)", "", f"El .zip está corrupto/incompleto: {e}")]
    with zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = info.filename
            ext = Path(name).suffix.lower()
            if ext not in _DISPATCH and ext not in IMAGE_EXT:
                continue
            safe_name = os.path.basename(name)
            if not safe_name:
                continue
            dest = os.path.join(tmp_dir, safe_name)
            try:
                with zf.open(info) as src, open(dest, "wb") as dst:
                    dst.write(src.read())
                txt, warn = extract_text(dest)
                out.append((name, txt, warn))
            except Exception as e:
                out.append((name, "", f"No se pudo leer: {e}"))
            finally:
                if os.path.exists(dest):
                    try:
                        os.remove(dest)
                    except OSError:
                        pass
    return out


def chunk_text(text: str, max_chars: int = 4000) -> list[str]:
    """Parte texto largo en trozos por párrafo, respetando max_chars."""
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []
    chunks, buf = [], []
    size = 0
    for para in text.split("\n"):
        if size + len(para) + 1 > max_chars and buf:
            chunks.append("\n".join(buf))
            buf, size = [], 0
        buf.append(para)
        size += len(para) + 1
    if buf:
        chunks.append("\n".join(buf))
    return chunks
