# Panel STLF — EEASA (LSTM v1 vs v4)

Interfaz web (Flask) para visualizar los resultados del pronóstico de carga
a corto plazo (STLF) sobre 5 alimentadores de EEASA: comparación de
**LSTM v1** (línea base) y **LSTM v4** (corrector residual), ambos evaluados
sobre el mismo horizonte corto de 1h (4 pasos de 15 min).

> **Nota sobre v5:** se evaluó una versión LSTM v5, pero sus métricas no
> mejoraron frente a v4, así que no se integra en el dashboard. El CSV
> fuente (`comparacion_v1_v4_v5_1h.csv`) sí trae columnas "V5" (se
> conservan por trazabilidad del experimento) pero `app.py` las ignora
> por completo al cargar los datos.

## Contenido

- Resumen general: KPIs (alimentadores aceptados bajo su umbral práctico,
  mejora promedio v4 vs v1), gráfico comparativo de MAPE por alimentador,
  tabla con estado de aceptación, galería con las figuras ya generadas.
- Detalle por alimentador: gauge tipo panel de control con el MAPE de v4
  frente a su umbral práctico (y el teórico, cuando existe), tabla de
  métricas (MAPE, RMSE, MAE, R²) y gráfico radar comparativo v1 vs v4.
- **Curvas de predicción real vs. predicho** (`/alimentador/<COD>/predicciones`):
  navegador de ventanas (500 por alimentador, deslizantes) con el pronóstico
  real vs. LSTM v1 o real vs. LSTM v4, cada una a 1h/4 pasos. Los datos se
  sirven desde `data/predicciones/*.csv.gz` vía una API interna
  (`/api/prediccion/...`).

  Nota: estos CSV de predicciones ya no traen columna `timestamp` ni
  `persistencia` — la navegación es por número de ventana (0 a 499), no por
  fecha, y el eje horizontal del gráfico muestra el paso del horizonte
  (+15, +30, +45, +60 min) en vez de una hora del día.

  El backend lee los CSV comprimidos con la librería estándar (`csv` +
  `gzip`), sin depender de `pandas`.

## Fuente de métricas agregadas

`data/comparacion_v1_v4_v5_1h.csv` es la única fuente de métricas por
alimentador (ya no hay `metricas_<CODIGO>.json` ni resúmenes ejecutivos).
Columnas usadas por `app.py` (las "V5" se leen y se descartan):

```
Alimentador, Descripción,
MAPE V1 (%), MAPE V4 (%),
RMSE V1 (kW), RMSE V4 (kW),
MAE V1 (kW), MAE V4 (kW),
R² V1, R² V4,
Umbral práctico, Umbral teórico,
V4 ¿cumple práctico?, V4 ¿cumple teórico?
```

`Umbral práctico` es el que determina el badge "Acepta / No acepta" en toda
la app. `Umbral teórico` (cuando no es "N/A") se muestra como dato
adicional en la página de detalle.

## Instalación y ejecución

```bash
python -m venv venv
source venv/bin/activate      # En Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre http://127.0.0.1:5000 en el navegador.

## Estructura

```
proyecto/
├── app.py                          # Rutas y carga de datos
├── data/
│   ├── comparacion_v1_v4_v5_1h.csv # métricas agregadas (fuente única)
│   └── predicciones/               # predicciones_v{1,4}_<CODIGO>.csv.gz
├── templates/                      # index.html, detalle.html, predicciones.html, base.html, 404.html
├── static/
│   ├── css/style.css
│   ├── js/gauge.js                 # gauge SVG tipo panel de control
│   └── img/                        # figuras del análisis original
└── requirements.txt
```

## Agregar/actualizar alimentadores

Actualiza la fila correspondiente en `comparacion_v1_v4_v5_1h.csv` (o añade
una fila nueva con el mismo formato de columnas) y aparecerá automáticamente
en el resumen y su página de detalle en `/alimentador/<CODIGO>`. Para las
curvas de predicción, coloca `predicciones_v1_<CODIGO>.csv.gz` y/o
`predicciones_v4_<CODIGO>.csv.gz` en `data/predicciones/` con columnas
`ventana,paso_horizonte,real,pred_v1` (o `pred_v4`).
