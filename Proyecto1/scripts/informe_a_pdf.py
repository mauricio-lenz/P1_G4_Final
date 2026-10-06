#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""reports/final.md -> reports/final.pdf (portada, indice con enlaces y figuras).

Convierte el Markdown a HTML (paquete markdown) y lo imprime a PDF con Edge o Chrome
sin interfaz. El PDF es para revisar y compartir; no va al repositorio.

Uso:
  python -X utf8 Proyecto1/scripts/informe_a_pdf.py [--md reports/final.md] [--pdf reports/final.pdf]
"""
import argparse
import datetime as dt
import html
import re
import subprocess
from pathlib import Path

import markdown

REPO = Path(__file__).resolve().parents[2]
NAVEGADORES = [
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
]

CSS = """
@page { size: A4; margin: 15mm 14mm 15mm 14mm; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 9.7pt; line-height: 1.42; color: #1b2430; }
.portada { height: 255mm; display: flex; flex-direction: column; justify-content: center; page-break-after: always; }
.portada .curso { font-size: 10pt; letter-spacing: .08em; text-transform: uppercase; color: #2b5d8c; margin-bottom: 10pt; }
.portada h1 { font-size: 25pt; line-height: 1.15; margin: 0 0 8pt 0; color: #0f2a44; border: 0; }
.portada .sub { font-size: 13pt; color: #3d4b59; margin-bottom: 28pt; }
.portada table { width: auto; font-size: 10pt; border: 0; margin: 0; }
.portada td { border: 0; padding: 2pt 14pt 2pt 0; }
.portada td:first-child { color: #6a7884; }
.portada .nota { margin-top: 34pt; font-size: 8.5pt; color: #6a7884; max-width: 150mm; }
.indice { page-break-after: always; }
.indice h2 { border: 0; }
.indice ul { columns: 2; column-gap: 10mm; margin-left: 0; list-style: none; font-size: 10pt; }
.indice li { margin: 2.5pt 0; break-inside: avoid; }
.indice a { color: #1b2430; text-decoration: none; }
h1 { font-size: 16pt; margin: 0 0 6pt 0; color: #0f2a44; }
h2 { font-size: 13pt; margin: 18pt 0 5pt 0; padding-bottom: 2pt; border-bottom: 1.2pt solid #2b5d8c; color: #0f2a44; page-break-after: avoid; }
h3 { font-size: 10.6pt; margin: 11pt 0 3pt 0; color: #2b5d8c; page-break-after: avoid; }
p, li { margin: 3.5pt 0; }
ul, ol { margin: 3pt 0 3pt 16pt; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 8pt 0; font-size: 8.6pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 0.6pt solid #b9c4cf; padding: 2.6pt 4.5pt; vertical-align: top; text-align: left; }
th { background: #e8eef4; font-weight: 600; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.4pt; background: #f1f4f7; padding: 0 2pt; border-radius: 2pt; }
pre { background: #f4f6f9; border: 0.6pt solid #d5dde5; padding: 5pt 7pt; font-size: 8.2pt; line-height: 1.35; page-break-inside: avoid; white-space: pre-wrap; }
pre code { background: none; padding: 0; }
img { max-width: 100%; max-height: 105mm; display: block; margin: 8pt auto 2pt auto; page-break-inside: avoid; }
p.figura { text-align: center; font-size: 8.4pt; color: #52514e; margin: 0 8mm 10pt 8mm; page-break-before: avoid; }
hr { border: 0; border-top: 0.6pt solid #c7d0da; margin: 10pt 0; }
strong { color: #0f2a44; }
a { color: #2b5d8c; }
.pie { margin-top: 16pt; font-size: 8pt; color: #6a7884; border-top: 0.6pt solid #c7d0da; padding-top: 4pt; }
"""


def commit_actual():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO, capture_output=True, text=True).stdout.strip()
    except OSError:
        return ""


def main():
    ap = argparse.ArgumentParser(description="Informe final Markdown -> PDF")
    ap.add_argument("--md", type=Path, default=REPO / "reports" / "final.md")
    ap.add_argument("--pdf", type=Path, default=REPO / "reports" / "final.pdf")
    ap.add_argument("--titulo", default="Laboratorio estructural OpenSees + Unity + AR")
    ap.add_argument("--subtitulo", default="Informe final · Grupo 4 (P1_G4)")
    args = ap.parse_args()
    args.md, args.pdf = args.md.resolve(), args.pdf.resolve()

    texto = args.md.read_text(encoding="utf-8")
    # la portada reemplaza el titulo y el encabezado del Markdown (hasta la primera linea ---)
    cuerpo_md = texto.split("\n---\n", 1)[1] if "\n---\n" in texto else texto
    encabezado = texto.split("\n---\n", 1)[0]
    rubrica = encabezado[encabezado.find("**Dónde está cada criterio"):] if "**Dónde está cada criterio" in encabezado else ""

    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists", "toc"],
                           extension_configs={"toc": {"toc_depth": "2"}})
    cuerpo = md.convert(cuerpo_md)
    # pies de figura: parrafos que solo tienen <em>Figura ...</em>
    cuerpo = re.sub(r"<p><em>(Figura [^<]*(?:<[^>]+>[^<]*)*?)</em></p>", r'<p class="figura">\1</p>', cuerpo)
    indice = "".join(f'<li><a href="#{t["id"]}">{html.escape(t["name"])}</a></li>' for t in md.toc_tokens)
    rubrica_html = markdown.markdown(rubrica, extensions=["tables"]) if rubrica else ""

    commit = commit_actual()
    portada = f"""
<div class="portada">
  <div class="curso">MCOC · Universidad de los Andes · Proyecto 1</div>
  <h1>{html.escape(args.titulo)}</h1>
  <div class="sub">{html.escape(args.subtitulo)}</div>
  <table>
    <tr><td>Integrantes</td><td>Matías Campos · Iván González · Mauricio Lenz</td></tr>
    <tr><td>Entrega</td><td>semana 7 · 8 de octubre de 2026</td></tr>
    <tr><td>Repositorio</td><td>github.com/mauricio-lenz/P1_G4_Final</td></tr>
    <tr><td>Versión</td><td>commit {html.escape(commit or "—")} · PDF generado el {dt.date.today():%d-%m-%Y}</td></tr>
  </table>
  <div class="nota">Este PDF se genera desde <code>reports/{args.md.name}</code> con <code>Proyecto1/scripts/informe_a_pdf.py</code>.
  El documento de la entrega es el Markdown del repositorio; las cifras se regeneran con
  <code>exportar_resultados_unity.py</code> y <code>figuras_informe_final.py</code>.</div>
</div>
<div class="indice"><h2>Contenido</h2><ul>{indice}</ul>{rubrica_html}</div>
"""
    pagina = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>{html.escape(args.subtitulo)}</title>
<style>{CSS}</style></head><body>{portada}{cuerpo}
<div class="pie">reports/{args.md.name} · github.com/mauricio-lenz/P1_G4_Final · commit {html.escape(commit or "—")}</div>
</body></html>"""

    html_tmp = args.md.parent / f"_{args.md.stem}_print.html"      # junto al .md para que resuelvan las rutas img/...
    html_tmp.write_text(pagina, encoding="utf-8")
    nav = next((p for p in NAVEGADORES if p.exists()), None)
    if nav is None:
        raise SystemExit("No encontre Edge ni Chrome para imprimir el PDF.")
    try:
        subprocess.run([str(nav), "--headless", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={args.pdf}",
                        html_tmp.as_uri()], check=True, timeout=180, capture_output=True)
    finally:
        html_tmp.unlink(missing_ok=True)
    print(f"{args.pdf} ({args.pdf.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
