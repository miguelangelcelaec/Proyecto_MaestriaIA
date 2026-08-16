"""
Dashboard de resultados LSTM - Pronóstico de carga a corto plazo (STLF)
Alimentadores de distribución EEASA - Tungurahua, Ecuador

Visualiza métricas de los modelos LSTM v1 (línea base) y LSTM v4 (corrector
residual), evaluados ambos sobre el mismo horizonte corto de 1h (4 pasos de
15 min), para los 5 alimentadores evaluados.

Nota: el modelo v5 fue evaluado pero no mejoró las métricas frente a v4, así
que no se integra en el dashboard — solo queda v1 vs. v4 como comparativo.
La fuente de métricas agregadas es data/comparacion_v1_v4_1h.csv (se
ignoran sus columnas "V5"); las curvas real vs. predicho se leen de
data/predicciones/predicciones_v{1,4}_<CODIGO>.csv.gz.
"""
import csv
import gzip
from functools import lru_cache
from pathlib import Path
from collections import defaultdict
from flask import Flask, abort, jsonify, render_template, request

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PRED_DIR = DATA_DIR / "predicciones"
COMPARACION_CSV = DATA_DIR / "comparacion_v1_v4_1h.csv"

app = Flask(__name__)

# Descripciones cortas de cantón por prefijo de código (informativo, ajustable)
CANTON_MAP = {
    "ALIN": "Ambato",
    "ALUC": "Ambato",
    "ALUR": "Ambato",
    "ALRA": "Pelileo",
    "ALRG": "Pelileo",
}


def _localizar_archivo(codigo, version):
    """Prueba ambos esquemas de nombre de archivo que hemos usado:
      - predicciones_<version>_<codigo>.csv.gz
      - predicciones_<codigo>_<version>.csv.gz
    """
    candidatos = [
        PRED_DIR / f"predicciones_{version}_{codigo}.csv.gz",
        PRED_DIR / f"predicciones_{codigo}_{version}.csv.gz",
    ]
    for p in candidatos:
        if p.exists():
            return p
    return None


def _leer_csv_gz(path):
    with gzip.open(path, "rt", newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def _num(valor):
    """Convierte '5.683' o '12.0%' a float; deja pasar None / 'N/A' tal cual."""
    if valor is None:
        return None
    v = valor.strip()
    if not v or v.upper().startswith("N/A"):
        return None
    return float(v.rstrip("%"))


def _bool(valor):
    if valor is None:
        return None
    v = valor.strip().lower()
    if v in ("true", "1", "sí", "si"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


@lru_cache(maxsize=1)
def cargar_alimentadores():
    """Carga las métricas agregadas de los 5 alimentadores desde
    data/comparacion_v1_v4_v5_1h.csv.

    Ese CSV trae MAPE/RMSE/MAE/R² para v1, v4 y v5, pero v5 ya no se usa
    (no mejoró frente a v4), así que sus columnas se leen y se descartan.
    También trae el umbral práctico (el que se usa para aceptar/rechazar
    el alimentador) y, cuando aplica, un umbral teórico adicional.

    Devuelve {codigo: {codigo, descripcion, umbral_mape, umbral_teorico,
    v1: {...}, v4: {...}, acepta_umbral, acepta_teorico}}.
    """
    alimentadores = {}
    if not COMPARACION_CSV.exists():
        return alimentadores

    with open(COMPARACION_CSV, encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            codigo = row["Alimentador"].strip()
            alimentadores[codigo] = {
                "codigo": codigo,
                "descripcion": row["Descripción"].strip(),
                "umbral_mape": _num(row["Umbral práctico"]),
                "umbral_teorico": _num(row["Umbral teórico"]),
                "v1": {
                    "modelo": "LSTM v1",
                    "mape": _num(row["MAPE V1 (%)"]),
                    "rmse": _num(row["RMSE V1 (kW)"]),
                    "mae": _num(row["MAE V1 (kW)"]),
                    "r2": _num(row["R² V1"]),
                },
                "v4": {
                    "modelo": "LSTM v4",
                    "mape": _num(row["MAPE V4 (%)"]),
                    "rmse": _num(row["RMSE V4 (kW)"]),
                    "mae": _num(row["MAE V4 (kW)"]),
                    "r2": _num(row["R² V4"]),
                },
                "acepta_umbral": _bool(row["V4 ¿cumple práctico?"]),
                "acepta_teorico": _bool(row["V4 ¿cumple teórico?"]),
            }

    return alimentadores


@lru_cache(maxsize=10)
def cargar_predicciones(codigo, version):
    """Carga (y cachea en memoria) el CSV comprimido de predicciones de un
    alimentador/version: columnas ventana,paso_horizonte,real,pred_v1|pred_v4.

    Ya no hay timestamp (el navegador de fechas se retiró) ni persistencia
    (ya no se distribuye ese archivo); la navegación es por número de
    ventana. Cada ventana cubre un horizonte corto de 1h (4 pasos de 15 min).

    Devuelve un dict con:
      - ventanas: {ventana_int: [fila, ...]} (filas ya ordenadas por paso_horizonte)
      - orden: lista de ventanas en orden ascendente
      - ventana_min / ventana_max
    """
    path = _localizar_archivo(codigo, version)
    if path is None:
        return None

    _, filas_csv = _leer_csv_gz(path)

    ventanas = defaultdict(list)
    orden = set()

    for row in filas_csv:
        ventana = int(row["ventana"])
        orden.add(ventana)
        fila = {
            "paso_horizonte": int(row["paso_horizonte"]),
            "real": round(float(row["real"]), 2),
            f"pred_{version}": round(float(row[f"pred_{version}"]), 2),
        }
        ventanas[ventana].append(fila)

    for v in ventanas:
        ventanas[v].sort(key=lambda f: f["paso_horizonte"])

    orden = sorted(orden)
    return {
        "ventanas": dict(ventanas),
        "orden": orden,
        "ventana_min": min(orden) if orden else 0,
        "ventana_max": max(orden) if orden else 0,
    }


def cargar_csv_comparativo():
    """Filas crudas de comparacion_v1_v4_v5_1h.csv, para la tabla/galería
    de la portada si se quiere mostrar el detalle tal cual viene del CSV."""
    filas = []
    if COMPARACION_CSV.exists():
        with open(COMPARACION_CSV, encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                filas.append(row)
    return filas


@app.route("/")
def index():
    alimentadores = cargar_alimentadores()
    csv_rows = cargar_csv_comparativo()

    labels = list(alimentadores.keys())
    mape_v1 = [alimentadores[k]["v1"]["mape"] for k in labels]
    mape_v4 = [alimentadores[k]["v4"]["mape"] for k in labels]
    umbrales = [alimentadores[k]["umbral_mape"] for k in labels]

    n_total = len(alimentadores)
    n_aceptados = sum(1 for a in alimentadores.values() if a["acepta_umbral"])
    mejora_promedio = sum(
        alimentadores[k]["v1"]["mape"] - alimentadores[k]["v4"]["mape"] for k in labels
    ) / n_total if n_total else 0

    return render_template(
        "index.html",
        alimentadores=alimentadores,
        csv_rows=csv_rows,
        chart_labels=labels,
        chart_v1=mape_v1,
        chart_v4=mape_v4,
        chart_umbrales=umbrales,
        n_total=n_total,
        n_aceptados=n_aceptados,
        mejora_promedio=mejora_promedio,
        canton_map=CANTON_MAP,
    )


@app.route("/alimentador/<codigo>")
def detalle(codigo):
    alimentadores = cargar_alimentadores()
    codigo = codigo.upper()
    if codigo not in alimentadores:
        abort(404)
    datos = alimentadores[codigo]

    otros = [k for k in alimentadores.keys() if k != codigo]

    metricas_keys = ["mape", "rmse", "mae", "r2"]
    metricas_labels = {
        "mape": "MAPE (%)",
        "rmse": "RMSE (kW)",
        "mae": "MAE (kW)",
        "r2": "R²",
    }

    return render_template(
        "detalle.html",
        codigo=codigo,
        datos=datos,
        otros=otros,
        metricas_keys=metricas_keys,
        metricas_labels=metricas_labels,
        canton=CANTON_MAP.get(codigo, ""),
    )


@app.route("/alimentador/<codigo>/predicciones")
def predicciones(codigo):
    codigo = codigo.upper()
    alimentadores = cargar_alimentadores()
    if codigo not in alimentadores:
        abort(404)

    tiene_v1 = _localizar_archivo(codigo, "v1") is not None
    tiene_v4 = _localizar_archivo(codigo, "v4") is not None

    return render_template(
        "predicciones.html",
        codigo=codigo,
        datos=alimentadores[codigo],
        tiene_v1=tiene_v1,
        tiene_v4=tiene_v4,
        canton=CANTON_MAP.get(codigo, ""),
    )


@app.route("/api/prediccion/<codigo>/<version>")
def api_prediccion(codigo, version):
    codigo = codigo.upper()
    if version not in ("v1", "v4"):
        abort(404)
    datos = cargar_predicciones(codigo, version)
    if datos is None:
        abort(404)

    ventana_param = request.args.get("ventana")
    ventana = int(ventana_param) if ventana_param is not None else datos["orden"][0]

    filas = datos["ventanas"].get(ventana)
    if not filas:
        return jsonify({"error": "ventana no encontrada"}), 404

    payload = {
        "codigo": codigo,
        "version": version,
        "ventana": ventana,
        "pasos": [f["paso_horizonte"] for f in filas],
        "real": [f["real"] for f in filas],
        f"pred_{version}": [f[f"pred_{version}"] for f in filas],
        "ventana_min": datos["ventana_min"],
        "ventana_max": datos["ventana_max"],
    }
    return jsonify(payload)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
