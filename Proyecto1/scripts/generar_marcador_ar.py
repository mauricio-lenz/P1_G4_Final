"""Semana 6 (AR): genera la imagen de referencia que detecta ARCore.

La imagen es la planta del piso 1 del modelo (vigas de CIELO_1 + columnas) con
la columna ancla E1_260 destacada, sobre un fondo con detalle aleatorio (ARCore
necesita muchos puntos caracteristicos y nada repetitivo).

Salidas:
  edificio_G4/Assets/AR/Marcador_E1_260.png   -> textura de la XRReferenceImageLibrary
  ar/marcador_E1_260_imprimir.pdf             -> hoja A4 para imprimir al 100 %
  ar/marcador_E1_260.png                      -> misma imagen, para el informe

El ancho fisico impreso (MARKER_WIDTH_M) debe coincidir con el ancho declarado
en Unity (ARSetup.MarkerWidth): ARCore usa ese dato para la escala de la pose.
"""
import json
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "estructura_completo_unity.json"
OUT_UNITY = ROOT / "edificio_G4" / "Assets" / "AR" / "Marcador_E1_260.png"
OUT_DIR = ROOT / "ar"

MARKER_WIDTH_M = 0.20          # ancho impreso de la imagen (20 cm)
PX = 1600                      # resolucion de la imagen cuadrada
ANCHOR_TAG = "E1_260"
FLOOR_TOP_Z = 3.96             # vigas del cielo del piso 1


def font(size, bold=False):
    for name in (["arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["arial.ttf", "DejaVuSans.ttf"]):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make_marker():
    model = json.loads(DATA.read_text(encoding="utf-8"))
    nodes = {n["id"]: n for n in model["nodes"]}
    rnd = random.Random(260)

    img = Image.new("L", (PX, PX), 255)
    d = ImageDraw.Draw(img)

    # Fondo: poligonos aleatorios de alto contraste. ARCore busca esquinas
    # nitidas y no repetitivas (arcoreimg eval-img: 25/100 con gris claro,
    # ~90/100 con este fondo; Google recomienda >= 75).
    for _ in range(1500):
        x, y = rnd.uniform(0, PX), rnd.uniform(0, PX)
        r = rnd.uniform(8, 40)
        pts = [(x + rnd.uniform(-r, r), y + rnd.uniform(-r, r)) for _ in range(rnd.randint(3, 6))]
        d.polygon(pts, fill=rnd.randint(0, 230))

    # Planta del piso 1 (x hacia la derecha, y hacia arriba de la imagen)
    margin_top, margin = 230, 110
    xs = [n["x"] for n in nodes.values()]
    ys = [n["y"] for n in nodes.values()]
    sx = (PX - 2 * margin) / (max(xs) - min(xs))
    sy = (PX - margin_top - margin - 160) / (max(ys) - min(ys))
    s = min(sx, sy)
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    ox, oy = PX / 2, margin_top + (PX - margin_top - margin - 160) / 2

    def to_px(x, y):
        return ox + (x - cx) * s, oy - (y - cy) * s

    for e in model["elements"]:
        ni, nj = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        if e["type"] == "viga" and abs(ni["z"] - FLOOR_TOP_Z) < 0.1 and abs(nj["z"] - FLOOR_TOP_Z) < 0.1:
            seg = [*to_px(ni["x"], ni["y"]), *to_px(nj["x"], nj["y"])]
            d.line(seg, fill=255, width=21)   # halo blanco: planta legible sobre el fondo
            d.line(seg, fill=0, width=7)
    for w in model["walls"]:
        if w.get("top") in ("CIELO_1", "E2_Z3.91"):
            ni, nj = nodes[w["nodeI"]], nodes[w["nodeJ"]]
            seg = [*to_px(ni["x"], ni["y"]), *to_px(nj["x"], nj["y"])]
            d.line(seg, fill=255, width=28)
            d.line(seg, fill=0, width=14)

    anchor_xy = None
    for e in model["elements"]:
        if e["type"] != "columna":
            continue
        ni, nj = nodes[e["nodeI"]], nodes[e["nodeJ"]]
        if abs(min(ni["z"], nj["z"])) > 0.1:
            continue
        px, py = to_px(ni["x"], ni["y"])
        h = max(7.0, e.get("width_m", 0.5) * s / 2)
        if e["elementTag"] == ANCHOR_TAG:
            anchor_xy = (px, py)
        else:
            d.rectangle([px - h - 6, py - h - 6, px + h + 6, py + h + 6], fill=255)
            d.rectangle([px - h, py - h, px + h, py + h], fill=0)

    if anchor_xy:
        px, py = anchor_xy
        d.ellipse([px - 58, py - 58, px + 58, py + 58], fill=255)
        d.ellipse([px - 48, py - 48, px + 48, py + 48], outline=0, width=10)
        d.rectangle([px + 50, py - 76, px + 300, py - 8], fill=255)
        d.rectangle([px - 20, py - 20, px + 20, py + 20], fill=0)
        d.text((px + 58, py - 70), ANCHOR_TAG, fill=0, font=font(54, True))

    # Banda superior con titulo y flecha "arriba" (+y del modelo)
    d.rectangle([0, 0, PX, 190], fill=0)
    d.text((40, 30), "MCOC P1_G4  ·  MARCADOR AR", fill=255, font=font(72, True))
    d.text((40, 118), f"Ancla {ANCHOR_TAG} · COL70/70 · eje G / eje 2 · piso 1", fill=255, font=font(44))
    d.polygon([(PX - 110, 30), (PX - 60, 110), (PX - 160, 110)], fill=255)
    d.text((PX - 140, 120), "+Y", fill=255, font=font(44, True))

    # Banda inferior con escala y ejes
    d.rectangle([0, PX - 120, PX, PX], fill=0)
    d.text((40, PX - 95), f"Imprimir al 100 %: ancho = {MARKER_WIDTH_M * 100:.0f} cm", fill=255, font=font(48, True))
    d.line([PX - 360, PX - 60, PX - 160, PX - 60], fill=255, width=10)
    d.polygon([(PX - 160, PX - 85), (PX - 110, PX - 60), (PX - 160, PX - 35)], fill=255)
    d.text((PX - 100, PX - 90), "+X", fill=255, font=font(44, True))

    # Marco exterior
    d.rectangle([0, 0, PX - 1, PX - 1], outline=0, width=16)
    return img


def make_print_sheet(marker):
    dpi = 300
    a4 = (round(21.0 / 2.54 * dpi), round(29.7 / 2.54 * dpi))
    side = round(MARKER_WIDTH_M * 100 / 2.54 * dpi)
    page = Image.new("L", a4, 255)
    left = (a4[0] - side) // 2
    top = 260
    page.paste(marker.resize((side, side), Image.LANCZOS), (left, top))
    d = ImageDraw.Draw(page)
    y = top + side + 80
    d.text((left, y), "Imprimir en tamano real (100 %, sin 'ajustar a la pagina').", fill=0, font=font(48, True))
    d.text((left, y + 80), f"Verificar con regla: el cuadrado mide {MARKER_WIDTH_M * 100:.0f} cm de ancho.", fill=0, font=font(44))
    d.text((left, y + 150), f"Pegar plano y sin brillo en la cara de la columna {ANCHOR_TAG}, centro a 1,20 m del piso.", fill=0, font=font(44))
    d.text((left, y + 220), "Maqueta en mesa: dejar la hoja sobre la mesa.", fill=0, font=font(44))
    page.save(OUT_DIR / "marcador_E1_260_imprimir.pdf", resolution=dpi)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    OUT_UNITY.parent.mkdir(parents=True, exist_ok=True)
    marker = make_marker()
    marker.save(OUT_UNITY)
    marker.save(OUT_DIR / "marcador_E1_260.png")
    make_print_sheet(marker)
    print(f"Marcador: {OUT_UNITY}")
    print(f"PDF para imprimir: {OUT_DIR / 'marcador_E1_260_imprimir.pdf'} (ancho {MARKER_WIDTH_M * 100:.0f} cm)")


if __name__ == "__main__":
    main()
