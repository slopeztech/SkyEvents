"""
Fix translations for the new reports app entries.
Fills empty msgstr and corrects fuzzy translations for all reports-related strings.
Run with: python _fix_reports_translations.py
"""

import re

PO_FILE = "locale/es/LC_MESSAGES/django.po"

# Mapping of msgid → correct Spanish translation
# Key: exact msgid string
# Value: correct msgstr string
TRANSLATIONS = {
    # AppConfig / sidebar / titles
    "Reports": "Informes",

    # Forms — empty labels
    "— Not linked yet —": "— Sin vincular aún —",
    "— None (radio only) —": "— Ninguna (solo radio) —",
    "— None (optical only) —": "— Ninguno (solo óptico) —",

    # Forms — validation errors
    "This camera does not belong to the selected station.": "Esta cámara no pertenece a la estación seleccionada.",
    "This radio receiver does not belong to the selected station.": "Este receptor de radio no pertenece a la estación seleccionada.",

    # Model — ReportStatus choices
    "Pending": "Pendiente",
    "Linked to event": "Vinculado a evento",
    "Archived": "Archivado",

    # Model — FileType choices
    "Video": "Vídeo",
    "Image": "Imagen",
    "Spectrogram": "Espectrograma",
    "Audio": "Audio",
    "Data file": "Archivo de datos",
    "Other": "Otro",

    # Model — StationReport field verbose names
    "event": "evento",
    "station": "estación",
    "camera": "cámara",
    "radio receiver": "receptor de radio",
    "recorded at (UTC)": "registrado a las (UTC)",
    "duration (ms)": "duración (ms)",
    "status": "estado",
    "notes": "notas",

    # Model — StationReport help texts
    "Astronomical event this report is linked to.": "Evento astronómico al que está vinculado este informe.",
    "Station that produced this report.": "Estación que generó este informe.",
    "Camera that recorded this detection (leave blank for radio-only).": "Cámara que registró esta detección (dejar en blanco si es solo radio).",
    "Radio receiver that detected this echo (leave blank for optical-only).": "Receptor de radio que detectó este eco (dejar en blanco si es solo óptico).",
    "UTC timestamp when the device first detected the event.": "Marca de tiempo UTC cuando el dispositivo detectó por primera vez el evento.",
    "Duration of the detection in milliseconds.": "Duración de la detección en milisegundos.",
    "Operator notes or automatic processing remarks.": "Notas del operador o comentarios del procesamiento automático.",

    # Model — StationReport meta
    "station report": "informe de estación",
    "station reports": "informes de estación",
    "unknown device": "dispositivo desconocido",

    # Model — ReportFile field verbose names
    "report": "informe",
    "file type": "tipo de archivo",
    "filename": "nombre de archivo",
    "file size (bytes)": "tamaño de archivo (bytes)",
    "description": "descripción",
    "available": "disponible",

    # Model — ReportFile help texts
    "Original filename or path on the station storage.": "Nombre de archivo original o ruta en el almacenamiento de la estación.",
    "File size in bytes, if known.": "Tamaño del archivo en bytes, si se conoce.",
    "Short description of the file contents.": "Breve descripción del contenido del archivo.",
    "Whether this file can currently be requested or downloaded.": "Si este archivo se puede solicitar o descargar actualmente.",

    # Model — ReportFile meta
    "report file": "archivo de informe",
    "report files": "archivos de informe",

    # Views — messages
    "Report created successfully.": "Informe creado correctamente.",
    "Report updated successfully.": "Informe actualizado correctamente.",
    "Report deleted.": "Informe eliminado.",
    "Files updated.": "Archivos actualizados.",
    "File removed.": "Archivo eliminado.",

    # Views — page titles
    "New report": "Nuevo informe",
    "Create report": "Crear informe",
    "Edit report": "Editar informe",
    "Save changes": "Guardar cambios",

    # Template strings
    "Recorded at (UTC)": "Registrado a las (UTC)",
    "Report detail": "Detalle de informe",
    "No reports found.": "No se encontraron informes.",
    "Create first report": "Crear primer informe",
    "No reports linked.": "Sin informes vinculados.",
    "Add report": "Añadir informe",
    "Not linked yet": "Sin vincular aún",
    "Linked event": "Evento vinculado",
    "View event": "Ver evento",
    "Available files": "Archivos disponibles",
    "No files registered.": "Sin archivos registrados.",
    "Add file": "Añadir archivo",
    "Remove this file?": "¿Eliminar este archivo?",
    "Remove": "Eliminar",
    "Delete report": "Eliminar informe",
    "Are you sure you want to delete the report from station %(station)s recorded on %(date)s UTC? All associated files will also be deleted. This action cannot be undone.": "¿Seguro que deseas eliminar el informe de la estación %(station)s registrado el %(date)s UTC? También se eliminarán todos los archivos asociados. Esta acción no se puede deshacer.",
    "Origin": "Origen",
    "Detection": "Detección",
    "radio": "radio",
    "Unknown device": "Dispositivo desconocido",
}


def fix_entry(content: str, msgid: str, new_msgstr: str) -> tuple[str, bool]:
    """
    Replace msgstr for the given msgid (handles fuzzy entries too).
    Returns (new_content, changed).
    """
    # Pattern: optional fuzzy comment lines, msgid line, msgstr line
    # We want to replace the msgstr and remove the fuzzy marker
    escaped_msgid = re.escape(msgid)

    # Pattern for a fuzzy entry
    fuzzy_pattern = re.compile(
        r'(#, fuzzy\n(?:#[^\n]*\n)*)'
        r'(msgid "' + escaped_msgid + r'"\n)'
        r'(msgstr ")([^"]*)("\n)',
        re.MULTILINE,
    )

    def fuzzy_replacer(m):
        return m.group(2) + m.group(3) + new_msgstr + m.group(5)

    new_content, n1 = fuzzy_pattern.subn(fuzzy_replacer, content)

    # Pattern for a non-fuzzy empty entry
    empty_pattern = re.compile(
        r'(msgid "' + escaped_msgid + r'"\n)'
        r'(msgstr "")(\n)',
        re.MULTILINE,
    )

    def empty_replacer(m):
        return m.group(1) + 'msgstr "' + new_msgstr + '"' + m.group(3)

    new_content, n2 = empty_pattern.subn(empty_replacer, new_content)

    return new_content, (n1 + n2) > 0


with open(PO_FILE, encoding="utf-8") as f:
    content = f.read()

total_fixed = 0
for msgid, msgstr in TRANSLATIONS.items():
    content, changed = fix_entry(content, msgid, msgstr)
    if changed:
        total_fixed += 1
        print(f"  ✓  {msgid!r}")
    else:
        print(f"  ?  NOT FOUND: {msgid!r}")

with open(PO_FILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nFixed {total_fixed} / {len(TRANSLATIONS)} entries.")
