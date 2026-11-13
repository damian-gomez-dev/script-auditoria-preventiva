import html
import io
import os
import glob
import zipfile
from datetime import datetime
from decimal import Decimal
from typing import Dict

import numpy as np
import pandas as pd
import streamlit as st

from nomenclador_valores import NOMENCLADOR_VALORES_NACIONALES

# =============================================================================
# CONFIGURACIÓN DE PÁGINA Y CONSTANTES DE NEGOCIO
# =============================================================================
st.set_page_config(
    page_title="Auditoría Preventiva SSSalud",
    page_icon=":material/shield:",
    layout="wide",
    initial_sidebar_state="collapsed"
)

COLUMNAS = [
    'Tipo_Archivo', 'Cod_OS', 'CUIL', 'Cod_Certificado', 'Venc_Certificado',
    'Periodo_Prestacion', 'CUIT_Prestador', 'Tipo_Comp', 'Tipo_Emision',
    'Fecha_Emision', 'CAE', 'Pto_Venta', 'Num_Comp', 'Importe_Comp',
    'Importe_Solicitado', 'Cod_Practica', 'Cantidad', 'Provincia', 'Dependencia'
]

CODIGOS_CON_DEPENDENCIA = [
    '001', '002', '003', '004', '005', '006', '007', '008', '009', '010',
    '011', '012', '037', '038', '039', '040', '041', '042', '043', '044',
    '045', '046', '047', '048', '058', '059', '060', '061', '062', '063',
    '064', '065', '066', '067', '068', '069', '070', '071', '072', '076',
    '077', '078', '096'
]

CATALOGO_ERRORES_SSS = {
    '404': 'Cantidad inválida para el código de práctica declarado',
    '405': 'Adicional por Dependencia (S) en práctica no habilitada',
    '406': 'Incompatibilidad: Código 089 con prácticas escolares (025-036)',
    '407': 'Incompatibilidad: Código 086 con códigos 090 o 091',
    '408': 'Código 086 (Apoyo) sin práctica principal en lote ni en histórico',
    '411': 'Comprobante duplicado en presentaciones históricas (DEVOK)',
    '415': 'Código 096 (Transporte) sin práctica principal en lote ni en histórico',
    '420': 'Múltiples prácticas principales (rango 001-084) en el mismo período',
    '421': 'Incompatibilidad simultánea entre códigos 089 y 087',
    '422': 'Incompatibilidad de códigos 087/089 con prácticas principales',
    '424': 'Incompatibilidad: Código 085 con códigos 090 o 091',
    '425': 'Edad menor a 6 años para Transporte (096) con Dependencia',
    '426': 'Incompatibilidad de Estimulación Temprana (085) con otras prácticas',
    '427': 'Edad fuera de rango (1 a 6 años) para Estimulación Temprana (085)',
    '429': 'Incompatibilidad simultánea entre códigos 090 y 091',
}

CATALOGO_ERRORES_AFIP = {
    '100': 'Comprobante no encontrado en los Libros IVA cargados',
    '101': 'Fecha de emisión del TXT no coincide con Libro IVA AFIP',
    '110': 'Importe del comprobante en TXT no coincide con Libro IVA AFIP',
}

MESES_ES = {
    '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
    '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
    '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
}

# =============================================================================
# ESTILOS VISUALES (ESTÉTICA SAPI WEB)
# =============================================================================
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1120px;
    }

    /* Barra lateral limpia */
    section[data-testid="stSidebar"] {
        border-right: 1px solid #e2e8f0;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
        background: #f8fafc !important;
        border: 1px dashed #cbd5e1 !important;
        border-radius: 10px !important;
        padding: 0.75rem !important;
    }
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2563eb !important;
        background: #eff6ff !important;
    }

    /* Cabecera principal estilo SAPI Web (100% ancho y simétrica) */
    .sapi-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 60%, #1d4ed8 100%);
        border-radius: 16px;
        padding: 1.5rem 1.75rem;
        color: #ffffff;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.18);
        margin-bottom: 1.15rem;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        gap: 0.65rem;
        width: 100%;
        box-sizing: border-box;
    }
    .sapi-header-title {
        font-size: 1.6rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.6rem;
    }
    .sapi-header-sub {
        font-size: 0.92rem;
        color: #cbd5e1;
        margin: 0.2rem 0 0 0;
        text-align: center;
    }
    .sapi-badge-pill {
        background: rgba(255, 255, 255, 0.14);
        border: 1px solid rgba(255, 255, 255, 0.28);
        color: #f8fafc;
        padding: 0.4rem 1rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        backdrop-filter: blur(6px);
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
    }

    /* Tarjetas contenedoras SAPI */
    .st-key-card_params,
    .st-key-card_lote,
    .st-key-card_resultados {
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        padding: 1.25rem 1.4rem !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
        margin-bottom: 1rem !important;
    }
    .sapi-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0 0 0.25rem 0;
        display: flex;
        align-items: center;
        gap: 0.45rem;
    }
    .sapi-card-sub {
        font-size: 0.85rem;
        color: #64748b;
        margin: 0 0 0.85rem 0;
    }

    /* Badges de estado */
    .badge-ok {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.26rem 0.68rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        background: #dcfce7;
        color: #15803d;
        border: 1px solid #86efac;
    }
    .badge-err {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.26rem 0.68rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 700;
        background: #fee2e2;
        color: #b91c1c;
        border: 1px solid #fca5a5;
    }
    .badge-warn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.26rem 0.68rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        background: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-info {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.26rem 0.68rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }
    .badge-muted {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.26rem 0.68rem;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        background: #f1f5f9;
        color: #64748b;
        border: 1px solid #cbd5e1;
    }

    /* Cuadro de carga principal de prestaciones (_ds.txt) estilo SAPI */
    .st-key-uploader_txt {
        width: 100% !important;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzone"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        height: 166px !important;
        min-height: 166px !important;
        padding: 1.5rem 1.5rem !important;
        gap: 0.45rem !important;
        background: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 14px !important;
        box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
        margin: 0 auto !important;
        cursor: pointer !important;
        transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease !important;
    }
    .st-key-card_lote:has(.st-key-btn_ejecutar_auditoria) .st-key-uploader_txt [data-testid="stFileUploaderDropzone"] {
        height: 108px !important;
        min-height: 108px !important;
        padding: 0.65rem 1.25rem !important;
        gap: 0.2rem !important;
    }
    .st-key-btn_ejecutar_auditoria button {
        height: 42px !important;
        min-height: 42px !important;
    }
    .st-key-dl_panel_zip button,
    .st-key-dl_panel_ind button {
        height: 44px !important;
        min-height: 44px !important;
    }
    .dl-subcap {
        font-size: 0.86rem;
        color: #64748b;
        margin: 0 0 0.75rem 0;
        min-height: 1.4rem;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderPagination"],
    .st-key-uploader_txt ul {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzone"]:hover {
        border-color: #2563eb !important;
        background: #f8fafc !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.08) !important;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzone"] > span,
    .st-key-uploader_txt [data-testid="stFileUploaderDropzone"] button:not([aria-label^="Remove"]) {
        display: none !important;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzoneInstructions"] {
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        text-align: center !important;
        margin-right: 0 !important;
        width: 100% !important;
        gap: 0.4rem !important;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzoneInstructions"] > span,
    .st-key-uploader_txt [data-testid="stFileUploaderDropzoneInstructions"] > div {
        display: none !important;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzoneInstructions"]::before {
        content: "Selección del Archivo Principal de Prestaciones (_ds.txt)";
        display: inline-block;
        width: fit-content;
        margin: 0 auto;
        padding-left: 26px;
        background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath fill='%23D97706' d='M3 6a2 2 0 0 1 2-2h4.6l2 2H19a2 2 0 0 1 2 2v1H3V6z'/%3E%3Cpath fill='%23F59E0B' d='M3 8h18v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8z'/%3E%3C/svg%3E");
        background-repeat: no-repeat;
        background-position: left center;
        background-size: 19px 19px;
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.35;
        text-align: center;
    }
    .st-key-uploader_txt [data-testid="stFileUploaderDropzoneInstructions"]::after {
        content: "Arrastre y suelte el archivo TXT aquí.";
        display: block;
        white-space: pre-line;
        font-size: 0.85rem;
        color: #64748b;
        line-height: 1.5;
        text-align: center;
    }
    .st-key-uploader_txt label {
        display: none !important;
    }

    /* Tarjetas KPI principales del Informe (estilo lector-facturas-qr) */
    .kpi-grid-4 {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.9rem;
        margin-bottom: 1.15rem;
    }
    @media (max-width: 980px) {
        .kpi-grid-4 {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    .kpi-box {
        border-radius: 14px;
        padding: 1rem 1.15rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 0.45rem;
        box-sizing: border-box;
    }
    .kpi-box-ok {
        background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
        border: 1px solid #86efac;
    }
    .kpi-box-err {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border: 1px solid #fca5a5;
    }
    .kpi-box-warn {
        background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
        border: 1px solid #fcd34d;
    }
    .kpi-box-info {
        background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
        border: 1px solid #93c5fd;
    }
    .kpi-box-neutral {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
    }
    .kpi-box-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
    }
    .kpi-box-label {
        font-size: 0.76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #475569;
        margin: 0;
    }
    .kpi-box-ok .kpi-box-label { color: #166534; }
    .kpi-box-err .kpi-box-label { color: #991b1b; }
    .kpi-box-warn .kpi-box-label { color: #92400e; }
    .kpi-box-info .kpi-box-label { color: #1e40af; }

    .kpi-box-val {
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1.15;
        font-variant-numeric: tabular-nums;
        margin: 0;
        color: #0f172a;
    }
    .kpi-box-ok .kpi-box-val { color: #15803d; }
    .kpi-box-err .kpi-box-val { color: #b91c1c; }
    .kpi-box-warn .kpi-box-val { color: #b45309; }
    .kpi-box-info .kpi-box-val { color: #1d4ed8; }
    .kpi-box-neutral .kpi-box-val { color: #475569; font-size: 1.2rem; }

    .kpi-box-delta {
        font-size: 0.78rem;
        color: #475569;
        font-variant-numeric: tabular-nums;
        line-height: 1.35;
        margin: 0;
    }

    /* Barra horizontal compacta de métricas (estilo Paso 3 de lector-facturas-qr) */
    .rev-kpi-bar {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 0.7rem 1.15rem;
        margin-bottom: 0.85rem;
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        align-items: center;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
    }
    .rev-kpi-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.2rem 1rem;
        gap: 0.5rem;
    }
    .rev-kpi-item + .rev-kpi-item {
        border-left: 1px solid #e2e8f0;
    }
    .rev-kpi-label {
        font-size: 0.82rem;
        font-weight: 600;
        color: #475569;
        margin: 0;
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
    }
    .rev-kpi-val {
        font-size: 1.18rem;
        font-weight: 800;
        line-height: 1.1;
        font-variant-numeric: tabular-nums;
        margin: 0;
        color: #0f172a;
    }

    /* Notificaciones emergentes (toast) */
    [data-testid="stToastContainer"] {
        z-index: 999999 !important;
    }
    [data-testid="stToast"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.14) !important;
    }

    /* Modal emergente centrado para progreso de auditoría */
    .sapi-scan-overlay {
        position: fixed;
        inset: 0;
        background: rgba(15, 23, 42, 0.45);
        backdrop-filter: blur(4px);
        z-index: 999998;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 1rem;
        box-sizing: border-box;
    }
    .sapi-scan-modal {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.75rem 2rem;
        width: 100%;
        max-width: 480px;
        box-shadow: 0 20px 45px -10px rgba(15, 23, 42, 0.25);
        text-align: center;
        box-sizing: border-box;
    }
    .sapi-scan-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        line-height: 1;
        margin-bottom: 0.65rem;
    }
    .sapi-scan-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0 0 0.35rem 0;
    }
    .sapi-scan-sub {
        font-size: 0.88rem;
        color: #475569;
        margin: 0;
        word-break: break-word;
        line-height: 1.4;
    }
    .sapi-progress-track {
        width: 100%;
        height: 10px;
        background: #e2e8f0;
        border-radius: 999px;
        overflow: hidden;
        margin: 1rem 0 0.5rem 0;
    }
    .sapi-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #1d4ed8 0%, #3b82f6 100%);
        border-radius: 999px;
        transition: width 0.25s ease;
    }
    .sapi-scan-pct {
        font-size: 0.8rem;
        font-weight: 700;
        color: #1d4ed8;
        margin: 0;
    }

    /* Botones, pestañas e iconos Material */
    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
    button[data-baseweb="tab"] {
        font-weight: 600 !important;
        color: #64748b !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #1d4ed8 !important;
        font-weight: 700 !important;
    }
    [data-testid="stTextInput"] [data-testid="stIconMaterial"] {
        color: #475569 !important;
    }
    .st-key-btn_zip_paquete [data-testid="stIconMaterial"] {
        color: #fde047 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# ICONOS SVG INLINE Y FUNCIONES AUXILIARES
# =============================================================================
_SVG_PATHS: Dict[str, str] = {
    "shield": (
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'd="M12 2.5l7.5 3.2v5.8c0 5.1-3.2 9.4-7.5 10.9-4.3-1.5-7.5-5.8-7.5-10.9V5.7L12 2.5z"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round" d="M9 12.2l2.1 2.1 4.1-4.3"/>'
    ),
    "bolt": '<path fill="currentColor" d="M13 2L4 14h6l-1 8 9-12h-6l1-8z"/>',
    "upload": (
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'd="M12 16V4m0 0l-4 4m4-4l4 4M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>'
    ),
    "search": (
        '<circle cx="11" cy="11" r="7" fill="none" stroke="currentColor" stroke-width="2.2"/>'
        '<path stroke="currentColor" stroke-width="2.2" stroke-linecap="round" d="M20 20l-3.8-3.8"/>'
    ),
    "clipboard": (
        '<rect x="5" y="4" width="14" height="17" rx="2" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<rect x="9" y="2" width="6" height="4" rx="1" fill="#ffffff" stroke="currentColor" stroke-width="2"/>'
        '<path stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M9 11h6M9 15h4"/>'
    ),
    "check_circle": (
        '<circle cx="12" cy="12" r="9.5" fill="currentColor"/>'
        '<path fill="none" stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="M8 12.5l2.8 2.8 5.4-5.8"/>'
    ),
    "alert_triangle": (
        '<path fill="currentColor" d="M12 2.5L1.8 20.5a1 1 0 0 0 .87 1.5h18.66a1 1 0 0 0 .87-1.5L12 2.5z"/>'
        '<path stroke="#ffffff" stroke-width="2.1" stroke-linecap="round" d="M12 9v5.2"/>'
        '<circle cx="12" cy="17.6" r="1.2" fill="#ffffff"/>'
    ),
    "x_circle": (
        '<circle cx="12" cy="12" r="9.5" fill="currentColor"/>'
        '<path stroke="#ffffff" stroke-width="2.2" stroke-linecap="round" d="M9 9l6 6M15 9l-6 6"/>'
    ),
    "coins": (
        '<circle cx="10" cy="12" r="6.5" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M15.5 6.8a6.5 6.5 0 0 1 0 10.4"/>'
    ),
    "file_text": (
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'd="M6 2h9l4 4v16H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M9 11h6M9 15h6"/>'
    ),
    "users": (
        '<circle cx="9" cy="8" r="3.2" fill="none" stroke="currentColor" stroke-width="2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M3.5 19c.6-2.8 2.8-4.2 5.5-4.2s4.9 1.4 5.5 4.2"/>'
        '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M16.5 10.8a2.8 2.8 0 0 0 0-5.4M17.8 14.9c1.8.4 3.1 1.6 3.7 4.1"/>'
    ),
}


def _svg_inline(nombre: str, color: str, size: int = 16) -> str:
    """Devuelve un icono SVG plano inline en el color indicado."""
    cuerpo = _SVG_PATHS.get(nombre, "")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'style="color: {color}; flex-shrink: 0; vertical-align: middle;">{cuerpo}</svg>'
    )


def formato_moneda(valor: float) -> str:
    """Formatea un número al estilo moneda argentina ($ 1.234.567,89)."""
    try:
        s = f"{float(valor):,.2f}"
        return "$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "$ 0,00"


def formatear_periodo_legible(periodo: str) -> str:
    """Convierte YYYYMM en 'Mes YYYY' si es válido."""
    if len(periodo) == 6 and periodo.isdigit():
        anio = periodo[:4]
        mes = periodo[4:6]
        if mes in MESES_ES:
            return f"{MESES_ES[mes]} {anio}"
    return "Formato inválido (use YYYYMM)"


def desglosar_errores(series_errores: pd.Series, catalogo: dict, sep: str = '-') -> pd.DataFrame:
    """Cuenta la frecuencia de cada código de rechazo en una serie."""
    conteo = {}
    for val in series_errores.dropna():
        partes = [p.strip() for p in str(val).split(sep) if p.strip()]
        for cod in partes:
            conteo[cod] = conteo.get(cod, 0) + 1
    if not conteo:
        return pd.DataFrame(columns=['Código', 'Descripción', 'Ocurrencias'])
    filas = [
        {
            'Código': f"-{cod}" if sep == '-' and not cod.startswith('-') else cod,
            'Descripción': catalogo.get(cod, 'Observación / Regla de validación'),
            'Ocurrencias': cant
        }
        for cod, cant in sorted(conteo.items(), key=lambda x: x[1], reverse=True)
    ]
    return pd.DataFrame(filas)


def describir_codigos(val: str, catalogo: dict, sep: str = '-') -> str:
    """Devuelve la descripción legible de los códigos de rechazo en una celda."""
    partes = [p.strip() for p in str(val).split(sep) if p.strip()]
    descripciones = [catalogo.get(cod, f"Observación / Regla ({cod})") for cod in partes]
    return " | ".join(dict.fromkeys(descripciones))


# =============================================================================
# BARRA LATERAL - BASES DE DATOS E HISTÓRICOS (CRUCES)
# =============================================================================
with st.sidebar:
    st.markdown("### Bases de referencia")
    st.caption("Despliegue las secciones que necesite para adjuntar padrones, históricos y tablas de cruce.")

    with st.expander("1. Control SSSalud", expanded=False, icon=":material/verified_user:"):
        file_cert = st.file_uploader(
            "Base Certificados (Excel)",
            type=["xlsx"],
            help="Padrón de certificados CUD con columna 'Cuil' y 'Edad' (encabezado en fila 5)."
        )
        files_devok = st.file_uploader(
            "Históricos DEVOK (CSV/TXT)",
            type=["csv", "txt"],
            accept_multiple_files=True,
            help="Archivos DEVOK de períodos anteriores para detectar duplicados (-411) y validar apoyos/transporte (-408, -415)."
        )

    with st.expander("2. Control AFIP", expanded=False, icon=":material/receipt_long:"):
        files_iva = st.file_uploader(
            "Libros IVA AFIP (Excel/CSV)",
            type=["xlsx", "csv"],
            accept_multiple_files=True,
            help="Exportaciones de Mis Comprobantes / Libro IVA Digital para validar existencia (100), fecha (101) e importe (110)."
        )

    with st.expander("3. Subsidios y Padrón", expanded=False, icon=":material/payments:"):
        file_val = st.file_uploader(
            "Valores Nomenclador (Opcional · Excel)",
            type=["xlsx"],
            help="Ya incluye la base nacional vigente (202412-202610). Cargue un Excel solo si desea reemplazarla con valores actualizados."
        )
        file_afil = st.file_uploader(
            "Base Afiliados (Excel)",
            type=["xlsx"],
            help="Padrón de afiliados con 'Cuil', 'Nombre' y 'Convenio' para enriquecer el reporte de diferencias."
        )

    st.markdown("---")
    with st.expander("Guía de códigos de rechazo", expanded=False, icon=":material/menu_book:"):
        st.markdown("**Códigos SSSalud (`DS.DEVERR`)**")
        for cod, desc in CATALOGO_ERRORES_SSS.items():
            st.markdown(f"- **`-{cod}`**: {desc}")
        st.markdown("---")
        st.markdown("**Códigos AFIP (`DS_WS.DEVERR`)**")
        for cod, desc in CATALOGO_ERRORES_AFIP.items():
            st.markdown(f"- **`{cod}-`**: {desc}")


# =============================================================================
# ENCABEZADO PRINCIPAL ESTILO SAPI WEB
# =============================================================================
st.markdown(
    f"""
    <div class="sapi-header">
        <div>
            <h1 class="sapi-header-title">
                {_svg_inline("shield", "#93c5fd", 26)}
                <span>Sistema de Auditoría FTP Preventiva SSSalud</span>
            </h1>
            <p class="sapi-header-sub">
                Control previo de lotes de prestaciones, validación fiscal contra Libros IVA (AFIP/ARCA) y proyección de topes de reintegro
            </p>
        </div>
        <div class="sapi-badge-pill">
            {_svg_inline("bolt", "#fde047", 14)}
            <span>MECANISMO DE INTEGRACIÓN · LEY 24.901 · PRE-AUDITORÍA LOCAL</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# ESTADO DE SESIÓN INICIAL PARA PARÁMETROS Y FLUJO
# =============================================================================
if "param_rnos" not in st.session_state:
    st.session_state["param_rnos"] = ""
if "param_cuit" not in st.session_state:
    st.session_state["param_cuit"] = ""
if "param_periodo" not in st.session_state:
    _hoy = datetime.now()
    _mes_def = _hoy.month - 1 if _hoy.month > 1 else 12
    _anio_def = _hoy.year if _hoy.month > 1 else _hoy.year - 1
    st.session_state["param_periodo"] = f"{_anio_def}{_mes_def:02d}"
if "param_modo" not in st.session_state:
    st.session_state["param_modo"] = "Proceso Completo (Todo lo anterior)"

MODOS_CONTROL = (
    "Proceso Completo (Todo lo anterior)",
    "Control SSSalud (DEV.ERR)",
    "Control AFIP (DS_WS.DEVERR)",
    "Cálculo Subsidios (DS.SUBSIDIO)"
)


# =============================================================================
# PANTALLA 1 y 2: PARÁMETROS Y CARGA DE ARCHIVO (OCULTA AL VER RESULTADOS)
# =============================================================================
modal_progreso = st.empty()


def _render_modal_progreso(texto: str, porc: int) -> None:
    modal_progreso.markdown(
        f"""
<div class="sapi-scan-overlay">
    <div class="sapi-scan-modal">
        <div class="sapi-scan-icon">{_svg_inline("search", "#2563eb", 34)}</div>
        <p class="sapi-scan-title">Ejecutando Auditoría Preventiva SSSalud</p>
        <p class="sapi-scan-sub">{html.escape(texto)}</p>
        <div class="sapi-progress-track">
            <div class="sapi-progress-fill" style="width: {porc}%;"></div>
        </div>
        <p class="sapi-scan-pct">{porc}% completado</p>
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


if 'resultado_auditoria' not in st.session_state:
    # -------------------------------------------------------------------------
    # SECCIÓN 1: PARÁMETROS DE EJECUCIÓN (TARJETA SAPI)
    # -------------------------------------------------------------------------
    with st.container(border=True, key="card_params"):
        st.markdown(
            f'<p class="sapi-card-title">{_svg_inline("clipboard", "#1d4ed8", 18)}<span>1. Parámetros de Ejecución</span></p>'
            '<p class="sapi-card-sub">Configure los identificadores institucionales, el período de presentación y el alcance de la auditoría.</p>',
            unsafe_allow_html=True,
        )

        col1, col2, col3, col4 = st.columns([1.1, 1.25, 1.1, 1.85], gap="medium")

        with col1:
            rnos_ingresado = st.text_input(
                "RNOS Institucional",
                value=st.session_state["param_rnos"],
                placeholder="Ej: 107909",
                max_chars=6,
                icon=":material/local_hospital:",
                help="Número de Registro Nacional de Obras Sociales (obligatorio, hasta 6 dígitos)."
            )
            st.session_state["param_rnos"] = rnos_ingresado
        with col2:
            cuit_os_ingresado = st.text_input(
                "CUIT (Propio)",
                value=st.session_state["param_cuit"],
                placeholder="Ej: 30-12345678-9",
                max_chars=13,
                icon=":material/account_balance:",
                help="CUIT institucional obligatorio (11 dígitos) utilizado para el armado de líneas de subsidio."
            )
            st.session_state["param_cuit"] = cuit_os_ingresado
        with col3:
            periodo_pres = st.text_input(
                "Período (YYYYMM)",
                value=st.session_state["param_periodo"],
                icon=":material/calendar_month:",
                help="Período de presentación en formato de 6 dígitos (ej. 202610)"
            )
            st.session_state["param_periodo"] = periodo_pres
            st.caption(formatear_periodo_legible(periodo_pres))

        with col4:
            idx_modo = MODOS_CONTROL.index(st.session_state["param_modo"]) if st.session_state["param_modo"] in MODOS_CONTROL else 0
            modo = st.selectbox(
                "Alcance del control",
                MODOS_CONTROL,
                index=idx_modo,
                help="Seleccione si desea ejecutar los 3 controles simultáneamente o un módulo puntual."
            )
            st.session_state["param_modo"] = modo
            descripciones_modo = {
                "Proceso Completo (Todo lo anterior)": "Ejecuta Control SSSalud, cruce AFIP y proyección de subsidios.",
                "Control SSSalud (DEV.ERR)": "Genera archivos DEVOK y DEVERR según reglas de validación de SSSalud.",
                "Control AFIP (DS_WS.DEVERR)": "Cruza los comprobantes del lote contra los Libros IVA cargados.",
                "Cálculo Subsidios (DS.SUBSIDIO)": "Calcula topes según nomenclador y genera DS.SUBSIDIO y reporte de diferencias."
            }
            st.caption(descripciones_modo.get(modo, ''))

    # -------------------------------------------------------------------------
    # SECCIÓN 2: ARCHIVO DE PRESTACIONES
    # -------------------------------------------------------------------------
    with st.container(border=True, key="card_lote"):
        st.markdown(
            f'<p class="sapi-card-title">{_svg_inline("file_text", "#1d4ed8", 18)}<span>2. Archivo de Prestaciones (_ds.txt)</span></p>'
            '<p class="sapi-card-sub">Cargue el archivo TXT a continuación, adicionalmente puede utilizar la barra lateral izquierda para adjuntar padrones o Libros IVA.</p>',
            unsafe_allow_html=True,
        )

        archivo_txt = st.file_uploader(
            "Seleccione o arrastre el archivo TXT principal de prestaciones (_ds.txt)",
            type=["txt"],
            key="uploader_txt",
            help="Archivo separado por pipes (|) con las 19 columnas reglamentarias. Las bases de cruce opcionales se cargan desde el panel lateral izquierdo."
        )

        rnos_limpio = rnos_ingresado.strip()
        rnos_valido = bool(rnos_limpio) and rnos_limpio.isdigit() and 1 <= len(rnos_limpio) <= 6

        cuit_raw = cuit_os_ingresado.strip()
        cuit_limpio = "".join(ch for ch in cuit_raw if ch.isdigit())
        cuit_chars_ok = all(ch.isdigit() or ch in "- " for ch in cuit_raw)
        cuit_valido = bool(cuit_raw) and cuit_chars_ok and len(cuit_limpio) == 11

        periodo_pres = periodo_pres.strip()
        periodo_valido = len(periodo_pres) == 6 and periodo_pres.isdigit()

        errores_params = []
        if not rnos_valido:
            errores_params.append("Complete el **RNOS Institucional** (1 a 6 dígitos numéricos).")
        if not cuit_valido:
            errores_params.append("Complete el **CUIT (Propio)** válido (11 dígitos numéricos).")
        if not periodo_valido:
            errores_params.append("El **Período** debe tener exactamente 6 dígitos numéricos (formato YYYYMM).")

        if archivo_txt is not None:
            if not errores_params:
                clave_lote_toast = (archivo_txt.name, archivo_txt.size, modo, periodo_pres, rnos_limpio, cuit_limpio)
                if st.session_state.get("ultimo_lote_notificado") != clave_lote_toast:
                    st.session_state["ultimo_lote_notificado"] = clave_lote_toast
                    st.toast(
                        f":blue[:material/description:] Lote listo: **{archivo_txt.name}** · Modo: **{modo}** · Período: **{periodo_pres}** ({formatear_periodo_legible(periodo_pres)})",
                        duration="long",
                    )

            _, col_btn, _ = st.columns([1.15, 1.7, 1.15])
            with col_btn:
                iniciar_auditoria = st.button(
                    "Ejecutar auditoría",
                    key="btn_ejecutar_auditoria",
                    type="primary",
                    icon=":material/search:",
                    use_container_width=True
                )
        else:
            st.session_state["ultimo_lote_notificado"] = None
            iniciar_auditoria = False
else:
    archivo_txt = None
    rnos_limpio = ""
    cuit_limpio = ""
    errores_params = []
    periodo_valido = False
    iniciar_auditoria = False


if archivo_txt is not None and iniciar_auditoria and errores_params:
    st.toast(f":red[:material/error:] {' · '.join(errores_params)}", duration="long")
elif archivo_txt is not None and not errores_params and iniciar_auditoria:
    rnos_ingresado = rnos_limpio
    cuit_os_ingresado = cuit_limpio
    logs = []
    output_files = {}
    resumen_ejecucion = {
        'modo': modo,
        'periodo': periodo_pres,
        'rnos': rnos_ingresado,
        'archivo_nombre': archivo_txt.name,
        'timestamp': datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        'sss_ejecutado': False,
        'afip_ejecutado': False,
        'sub_ejecutado': False,
    }

    def log_msg(msg):
        logs.append(msg)

    try:
        _render_modal_progreso("Leyendo y normalizando registros del lote TXT...", 10)
        archivo_txt.seek(0)
        df = pd.read_csv(archivo_txt, sep='|', names=COLUMNAS, dtype=str, encoding='latin1', header=None)
        log_msg(f"Registros cargados desde TXT: {len(df)}")

        # Conversiones Comunes
        df['Importe_Num'] = pd.to_numeric(df['Importe_Solicitado'], errors='coerce') / 100.0
        df['Cantidad_Num'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
        df['Cod_Int'] = pd.to_numeric(df['Cod_Practica'], errors='coerce').fillna(0).astype(int).astype(str)

        resumen_ejecucion['total_registros'] = len(df)
        resumen_ejecucion['importe_total_lote'] = float(df['Importe_Num'].fillna(0).sum())
        resumen_ejecucion['cuils_unicos'] = int(df['CUIL'].nunique())

        # ---------------------------------------------------------
        # 1. CONTROL SSSALUD
        # ---------------------------------------------------------
        if modo in ["Control SSSalud (DEV.ERR)", "Control SSSalud (Lógica Médica)", "Proceso Completo (Todo lo anterior)"]:
            _render_modal_progreso("Aplicando reglas médicas y cruces históricos SSSalud (DEV.ERR)...", 35)
            log_msg("[1/3] Ejecutando Control SSSalud...")
            resumen_ejecucion['sss_ejecutado'] = True

            # Padrón Certificados
            if file_cert is not None:
                try:
                    file_cert.seek(0)
                    df_pad = pd.read_excel(file_cert, header=4, dtype=str, engine='openpyxl')
                    df_pad['Cuil'] = df_pad['Cuil'].str.replace('-', '', regex=False).str.strip()
                    df_pad['Edad'] = pd.to_numeric(df_pad['Edad'], errors='coerce').fillna(0).astype(int)
                    df = df.merge(df_pad[['Cuil', 'Edad']], left_on='CUIL', right_on='Cuil', how='left')
                except Exception as e:
                    log_msg(f"Advertencia leyendo padrón de certificados: {e}")

            # Históricos DEVOK
            set_duplicados = set()
            set_hist_transporte = set()
            set_hist_apoyo = set()
            todos = [f"{x:03d}" for x in range(1, 100)]

            if files_devok:
                log_msg(f"Procesando {len(files_devok)} archivos históricos DEVOK...")
                cod_transp_ok = set([c for c in todos if c not in ['086', '095', '096']])
                cod_apoyo_ok = set([f"{x:03d}" for x in range(1, 90) if x != 86] + ['097'])

                for f in files_devok:
                    try:
                        f.seek(0)
                        df_h = pd.read_csv(f, sep='|', header=None, dtype=str, encoding='latin1', usecols=[2, 5, 6, 7, 11, 12, 15])
                        cuit = df_h[6].str.strip()
                        tipo = pd.to_numeric(df_h[7], errors='coerce').fillna(0).astype(int).astype(str)
                        pto = pd.to_numeric(df_h[11], errors='coerce').fillna(0).astype(int).astype(str)
                        num = pd.to_numeric(df_h[12], errors='coerce').fillna(0).astype(int).astype(str)
                        set_duplicados.update((cuit + "_" + tipo + "_" + pto + "_" + num).dropna().unique())

                        df_h['Cod'] = df_h[15].str.strip().apply(lambda x: x.zfill(3) if pd.notnull(x) else '000')
                        df_h['Key'] = df_h[2].str.strip() + "_" + df_h[5].str.strip()

                        set_hist_transporte.update(df_h.loc[df_h['Cod'].isin(cod_transp_ok), 'Key'].unique())
                        set_hist_apoyo.update(df_h.loc[df_h['Cod'].isin(cod_apoyo_ok), 'Key'].unique())
                    except Exception:
                        pass

            df['Codigo_Rechazo'] = ''
            cuit_a = df['CUIT_Prestador'].str.strip()
            tipo_a = pd.to_numeric(df['Tipo_Comp'], errors='coerce').fillna(0).astype(int).astype(str)
            pto_a = pd.to_numeric(df['Pto_Venta'], errors='coerce').fillna(0).astype(int).astype(str)
            num_a = pd.to_numeric(df['Num_Comp'], errors='coerce').fillna(0).astype(int).astype(str)
            mask = (cuit_a + "_" + tipo_a + "_" + pto_a + "_" + num_a).isin(set_duplicados)
            df.loc[mask, 'Codigo_Rechazo'] += '-411'

            cod = pd.to_numeric(df['Cod_Practica'], errors='coerce').fillna(0).astype(int)
            cant = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0).astype(int)
            df.loc[(cod < 90) & (cant != 1), 'Codigo_Rechazo'] += '-404'
            df.loc[cod.isin([90, 91]) & (cant != 4), 'Codigo_Rechazo'] += '-404'
            df.loc[(cod == 96) & ((cant <= 1) | (cant == 4)), 'Codigo_Rechazo'] += '-404'
            df.loc[(df['Dependencia'] == 'S') & (~df['Cod_Practica'].isin(CODIGOS_CON_DEPENDENCIA)), 'Codigo_Rechazo'] += '-405'

            if 'Edad' in df.columns:
                df.loc[(df['Cod_Practica'] == '096') & (df['Dependencia'] == 'S') & (df['Edad'] > 0) & (df['Edad'] < 6), 'Codigo_Rechazo'] += '-425'
                df.loc[(df['Cod_Practica'] == '085') & (df['Edad'] > 0) & ((df['Edad'] < 1) | (df['Edad'] > 6)), 'Codigo_Rechazo'] += '-427'

            grupos = df.groupby(['CUIL', 'Periodo_Prestacion'])
            principales_408_local = set([f"{x:03d}" for x in range(1, 90) if x != 86] + ['097'])
            principales_transp_local = set([c for c in todos if c not in ['086', '095', '096']])
            rango_1_84 = [f"{x:03d}" for x in range(1, 85)]

            for (cuil, periodo), grupo in grupos:
                practicas = set(grupo['Cod_Practica'].unique())

                def add_err(idx, code):
                    df.loc[idx, 'Codigo_Rechazo'] += code

                if '089' in practicas and '087' in practicas:
                    add_err(grupo[grupo['Cod_Practica'].isin(['089', '087'])].index, '-421')
                if '090' in practicas and '091' in practicas:
                    add_err(grupo[grupo['Cod_Practica'] == '091'].index, '-429')
                if '085' in practicas:
                    prohibidos = [f"{x:03d}" for x in list(range(1, 7)) + list(range(13, 25)) + list(range(37, 85)) + [86] + list(range(92, 95))]
                    conf = practicas.intersection(set(prohibidos))
                    if conf:
                        add_err(grupo[grupo['Cod_Practica'].isin(['085'] + list(conf))].index, '-426')
                if '089' in practicas:
                    esc = [f"{x:03d}" for x in range(25, 37)]
                    if practicas.intersection(set(esc)):
                        add_err(grupo[grupo['Cod_Practica'].isin(esc)].index, '-406')
                if '086' in practicas and ('090' in practicas or '091' in practicas):
                    add_err(grupo[grupo['Cod_Practica'] == '086'].index, '-407')

                if '086' in practicas:
                    tiene_local = not practicas.isdisjoint(principales_408_local)
                    tiene_hist = (cuil + "_" + periodo) in set_hist_apoyo
                    if not tiene_local and not tiene_hist:
                        add_err(grupo[grupo['Cod_Practica'] == '086'].index, '-408')

                if '096' in practicas:
                    tiene_local = not practicas.isdisjoint(principales_transp_local)
                    tiene_hist = (cuil + "_" + periodo) in set_hist_transporte
                    if not tiene_local and not tiene_hist:
                        add_err(grupo[grupo['Cod_Practica'] == '096'].index, '-415')

                en_rango = practicas.intersection(set(rango_1_84))
                if len(en_rango) > 1:
                    add_err(grupo[grupo['Cod_Practica'].isin(en_rango)].index, '-420')
                if '087' in practicas or '089' in practicas:
                    prohibidos = rango_1_84 + ['093', '094', '098', '099']
                    conf = practicas.intersection(set(prohibidos))
                    if conf:
                        causantes = practicas.intersection({'087', '089'})
                        add_err(grupo[grupo['Cod_Practica'].isin(conf.union(causantes))].index, '-422')
                if '085' in practicas and ('090' in practicas or '091' in practicas):
                    add_err(grupo[grupo['Cod_Practica'] == '085'].index, '-424')

            df_ok = df[df['Codigo_Rechazo'] == ''].copy()
            if not df_ok.empty:
                name_ok = f"{rnos_ingresado}-{periodo_pres}_DS.DEVOK"
                buf_ok = io.StringIO()
                df_ok[COLUMNAS].to_csv(buf_ok, sep='|', index=False, header=False, encoding='latin1')
                output_files[name_ok] = buf_ok.getvalue()
                log_msg(f"  -> Generado OK: {name_ok} ({len(df_ok)} registros)")

            df_err = df[df['Codigo_Rechazo'] != ''].copy()
            if not df_err.empty:
                name_err = f"{rnos_ingresado}-{periodo_pres}_DS.DEVERR"
                buf_err = io.StringIO()
                df_err[COLUMNAS + ['Codigo_Rechazo']].to_csv(buf_err, sep='|', index=False, header=False, encoding='latin1')
                output_files[name_err] = buf_err.getvalue()
                log_msg(f"  -> Generado ERR: {name_err} ({len(df_err)} registros)")

            resumen_ejecucion['sss_ok_count'] = len(df_ok)
            resumen_ejecucion['sss_err_count'] = len(df_err)
            if not df_err.empty:
                df_sss_vista = df_err[COLUMNAS + ['Codigo_Rechazo']].copy()
                df_sss_vista['Descripcion codigo'] = df_sss_vista['Codigo_Rechazo'].apply(
                    lambda x: describir_codigos(x, CATALOGO_ERRORES_SSS, sep='-')
                )
                resumen_ejecucion['df_sss_err'] = df_sss_vista
            else:
                resumen_ejecucion['df_sss_err'] = pd.DataFrame()
            resumen_ejecucion['df_sss_desglose'] = desglosar_errores(df_err['Codigo_Rechazo'], CATALOGO_ERRORES_SSS, sep='-') if not df_err.empty else pd.DataFrame()

        # ---------------------------------------------------------
        # 2. CONTROL AFIP
        # ---------------------------------------------------------
        if modo in ["Control AFIP (DS_WS.DEVERR)", "Control AFIP (Cruce c/Libros IVA)", "Proceso Completo (Todo lo anterior)"]:
            _render_modal_progreso("Cruzando comprobantes contra Libros IVA AFIP/ARCA...", 65)
            log_msg("[2/3] Ejecutando Control AFIP...")
            MAPEO_FACTURAS = {'1': '1', '2': '4', '3': '6', '5': '11', '6': '15', '7': '51', '8': '54'}

            if files_iva:
                dfs_iva = []
                for f in files_iva:
                    try:
                        f.seek(0)
                        if f.name.endswith('.xlsx'):
                            d = pd.read_excel(f, dtype=str, engine='openpyxl')
                            if 'Nro. Doc. Vendedor' not in d.columns:
                                f.seek(0)
                                d = pd.read_excel(f, header=1, dtype=str, engine='openpyxl')
                        else:
                            d = pd.read_csv(f, dtype=str, encoding='latin1', sep=None, engine='python')
                            if 'Nro. Doc. Vendedor' not in d.columns:
                                f.seek(0)
                                d = pd.read_csv(f, header=1, dtype=str, encoding='latin1', sep=None, engine='python')
                        d.columns = d.columns.str.strip()
                        dfs_iva.append(d)
                    except Exception as e:
                        log_msg(f"Advertencia leyendo libro IVA {f.name}: {e}")

                if dfs_iva:
                    resumen_ejecucion['afip_ejecutado'] = True
                    df_iva_raw = pd.concat(dfs_iva, ignore_index=True)
                    df_iva = pd.DataFrame()
                    df_iva['IVA_CUIT'] = df_iva_raw['Nro. Doc. Vendedor'].astype(str).str.replace(r'\D', '', regex=True)
                    df_iva['IVA_TIPO'] = df_iva_raw['Tipo'].apply(lambda x: str(x).split('-')[0].strip().lstrip('0'))
                    df_iva['IVA_PTO'] = df_iva_raw['Punto de Venta'].apply(lambda x: str(int(float(x))))
                    df_iva['IVA_NUM'] = df_iva_raw['Número Desde'].apply(lambda x: str(int(float(x))))
                    df_iva['IVA_FECHA_ISO'] = pd.to_datetime(df_iva_raw['Fecha'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                    df_iva['IVA_TOTAL_DEC'] = df_iva_raw['Total'].apply(lambda x: Decimal(str(x).replace(',', '.')))
                    df_iva['KEY_AFIP'] = df_iva['IVA_CUIT'] + "_" + df_iva['IVA_TIPO'] + "_" + df_iva['IVA_PTO'] + "_" + df_iva['IVA_NUM']
                    df_iva = df_iva.drop_duplicates(subset=['KEY_AFIP'])

                    df_proc = df.copy()
                    df_proc['TXT_CUIT'] = df_proc['CUIT_Prestador'].astype(str).str.strip()
                    df_proc['TIPO_SSS_INT'] = df_proc['Tipo_Comp'].apply(lambda x: str(int(x)))
                    df_proc['TXT_TIPO_AFIP'] = df_proc['TIPO_SSS_INT'].map(MAPEO_FACTURAS).fillna('999')
                    df_proc['TXT_PTO'] = df_proc['Pto_Venta'].apply(lambda x: str(int(x)))
                    df_proc['TXT_NUM'] = df_proc['Num_Comp'].apply(lambda x: str(int(x)))
                    df_proc['TXT_FECHA_ISO'] = pd.to_datetime(df_proc['Fecha_Emision'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
                    df_proc['TXT_TOTAL_DEC'] = df_proc['Importe_Comp'].apply(lambda x: Decimal(x) / Decimal(100))
                    df_proc['KEY_AFIP'] = df_proc['TXT_CUIT'] + "_" + df_proc['TXT_TIPO_AFIP'] + "_" + df_proc['TXT_PTO'] + "_" + df_proc['TXT_NUM']

                    df_merged = df_proc.merge(df_iva[['KEY_AFIP', 'IVA_FECHA_ISO', 'IVA_TOTAL_DEC']], on='KEY_AFIP', how='left')
                    df_merged['Error_AFIP'] = ''

                    mask_not_found = df_merged['IVA_TOTAL_DEC'].isna()
                    df_merged.loc[mask_not_found, 'Error_AFIP'] += '100-'
                    mask_found = ~mask_not_found
                    df_merged.loc[mask_found & (df_merged['TXT_TOTAL_DEC'] != df_merged['IVA_TOTAL_DEC']), 'Error_AFIP'] += '110-'
                    df_merged.loc[mask_found & (df_merged['TXT_FECHA_ISO'] != df_merged['IVA_FECHA_ISO']), 'Error_AFIP'] += '101-'

                    df_afip_err = df_merged[df_merged['Error_AFIP'] != ''].copy()
                    if not df_afip_err.empty:
                        name_err = f"{rnos_ingresado}-{periodo_pres}_DS_WS.DEVERR"
                        buf_aerr = io.StringIO()
                        df_afip_err[COLUMNAS + ['Error_AFIP']].to_csv(buf_aerr, sep='|', index=False, header=False, encoding='latin1')
                        output_files[name_err] = buf_aerr.getvalue()
                        log_msg(f"  -> Generado AFIP ERR: {name_err} ({len(df_afip_err)} registros)")

                    df_afip_ok = df_merged[df_merged['Error_AFIP'] == ''].copy()
                    if not df_afip_ok.empty:
                        name_ok = f"{rnos_ingresado}-{periodo_pres}_DS_WS.DEVOK_AFIP"
                        buf_aok = io.StringIO()
                        df_afip_ok[COLUMNAS].to_csv(buf_aok, sep='|', index=False, header=False, encoding='latin1')
                        output_files[name_ok] = buf_aok.getvalue()
                        log_msg(f"  -> Generado AFIP OK: {name_ok} ({len(df_afip_ok)} registros)")

                    resumen_ejecucion['afip_ok_count'] = len(df_afip_ok)
                    resumen_ejecucion['afip_err_count'] = len(df_afip_err)
                    cols_vista_afip = [
                        'CUIL', 'CUIT_Prestador', 'Pto_Venta', 'Num_Comp',
                        'TXT_FECHA_ISO', 'IVA_FECHA_ISO', 'TXT_TOTAL_DEC', 'IVA_TOTAL_DEC', 'Error_AFIP'
                    ]
                    resumen_ejecucion['df_afip_err'] = df_afip_err[cols_vista_afip].astype(str).copy() if not df_afip_err.empty else pd.DataFrame()
                    resumen_ejecucion['df_afip_desglose'] = desglosar_errores(df_afip_err['Error_AFIP'], CATALOGO_ERRORES_AFIP, sep='-') if not df_afip_err.empty else pd.DataFrame()
            else:
                log_msg("Nota: No se cargaron libros IVA. Se omite control AFIP.")

        # ---------------------------------------------------------
        # 3. CÁLCULO SUBSIDIOS
        # ---------------------------------------------------------
        if modo in ["Cálculo Subsidios (DS.SUBSIDIO)", "Cálculo Subsidios (Económico)", "Proceso Completo (Todo lo anterior)"]:
            _render_modal_progreso("Calculando topes del Nomenclador y generando DS.SUBSIDIO...", 90)
            log_msg("[3/3] Ejecutando Cálculo de Subsidios...")
            try:
                if file_val is not None:
                    file_val.seek(0)
                    df_val = pd.read_excel(file_val, dtype=str, engine='openpyxl')
                    df_val.columns = df_val.columns.astype(str).str.strip()
                    df_val['Cod_Int'] = pd.to_numeric(df_val['CODIGO'], errors='coerce').fillna(0).astype(int).astype(str)
                    df_val.set_index('Cod_Int', inplace=True)
                else:
                    df_val = pd.DataFrame.from_dict(NOMENCLADOR_VALORES_NACIONALES, orient='index')
                    log_msg("Utilizando tabla nacional de Valores Nomenclador integrada.")

                agg_funcs = {
                    'Cod_OS': 'first',
                    'Importe_Num': 'sum',
                    'Cantidad_Num': 'sum',
                    'Dependencia': lambda x: 'S' if 'S' in x.values else 'N',
                    'CUIT_Prestador': 'first'
                }
                df_grouped = df.groupby(['CUIL', 'Periodo_Prestacion', 'Cod_Int']).agg(agg_funcs).reset_index()

                def get_valor_tabla(cod_busqueda, periodo):
                    if cod_busqueda in df_val.index and periodo in df_val.columns:
                        try:
                            return float(str(df_val.loc[cod_busqueda, periodo]).replace(',', '.'))
                        except Exception:
                            return 0.0
                    return 0.0

                def calcular_grupo(row):
                    cod = str(row['Cod_Int'])
                    periodo = str(row['Periodo_Prestacion']).strip()
                    solicitado = row['Importe_Num']
                    cantidad = row['Cantidad_Num']
                    dep = row['Dependencia']

                    cod_lookup = '90' if cod == '86' else cod
                    val_tabla = get_valor_tabla(cod_lookup, periodo)

                    tope_base = val_tabla * 4 if cod in ['90', '91', '86'] else (min(cantidad, 2500) * val_tabla if cod == '96' else val_tabla)
                    tope_final = tope_base * 1.35 if dep == 'S' else tope_base
                    return min(solicitado, max(0.0, tope_final))

                df_grouped['Monto_Subsidiable'] = df_grouped.apply(calcular_grupo, axis=1)

                df_grouped['Str_Imp_Sol'] = df_grouped['Importe_Num'].apply(lambda x: "{:.2f}".format(x))
                df_grouped['Str_Imp_Sub'] = df_grouped['Monto_Subsidiable'].apply(lambda x: "{:.2f}".format(x))
                df_grouped['Linea'] = (
                    cuit_os_ingresado + "|" + periodo_pres + "|" + df_grouped['Cod_OS'] + "|" +
                    df_grouped['CUIL'] + "|" + df_grouped['Periodo_Prestacion'] + "|" +
                    df_grouped['Str_Imp_Sol'] + "|" + df_grouped['Cod_Int'] + "|" + df_grouped['Str_Imp_Sub']
                )

                name_sub = f"{rnos_ingresado}-{periodo_pres}_DS.SUBSIDIO"
                buf_sub = io.StringIO()
                df_grouped['Linea'].to_csv(buf_sub, index=False, header=False, quoting=3, escapechar=None)
                output_files[name_sub] = buf_sub.getvalue()
                log_msg(f"  -> Subsidio generado: {name_sub} ({len(df_grouped)} líneas)")

                # Padrón Afiliados merge
                if file_afil is not None:
                    try:
                        file_afil.seek(0)
                        df_afi = pd.read_excel(file_afil, dtype=str, engine='openpyxl')
                        if 'Cuil' in df_afi.columns:
                            df_afi['Cuil'] = pd.to_numeric(df_afi['Cuil'], errors='coerce').fillna(0).astype(np.int64).astype(str)
                            df_afi = df_afi.drop_duplicates(subset=['Cuil'])
                            df_grouped = df_grouped.merge(df_afi[['Cuil', 'Nombre', 'Convenio']], left_on='CUIL', right_on='Cuil', how='left')
                            df = df.merge(df_afi[['Cuil', 'Convenio']], left_on='CUIL', right_on='Cuil', how='left')
                    except Exception:
                        pass

                if 'Nombre' not in df_grouped.columns:
                    df_grouped['Nombre'] = 'SIN NOMBRE EN PADRÓN'
                if 'Convenio' not in df_grouped.columns:
                    df_grouped['Convenio'] = 'SIN CONVENIO'
                if 'Convenio' not in df.columns:
                    df['Convenio'] = 'SIN CONVENIO'
                df_grouped.fillna({'Convenio': 'SIN CONVENIO', 'Nombre': 'SIN NOMBRE EN PADRÓN'}, inplace=True)

                df_grouped['Diferencia'] = df_grouped['Importe_Num'] - df_grouped['Monto_Subsidiable']
                rep_cols = ['CUIL', 'Nombre', 'Convenio', 'Periodo_Prestacion', 'Cod_Int', 'Importe_Num', 'Monto_Subsidiable', 'Diferencia']
                df_rep = df_grouped[rep_cols].copy()
                df_rep.columns = ['CUIL', 'Nombre', 'Convenio', 'Periodo', 'Codigo', 'Importe Solicitado', 'Importe Subsidiado', 'Diferencia']

                name_rep = f"{rnos_ingresado}-{periodo_pres}_Control_Diferencias.csv"
                buf_rep = io.StringIO()
                df_rep.to_csv(buf_rep, index=False, sep=';', float_format='%.2f', encoding='utf-8-sig')
                output_files[name_rep] = buf_rep.getvalue()
                log_msg(f"  -> Reporte detallado: {name_rep}")

                resumen_ejecucion['sub_ejecutado'] = True
                resumen_ejecucion['sub_solicitado'] = float(df_rep['Importe Solicitado'].sum())
                resumen_ejecucion['sub_subsidiado'] = float(df_rep['Importe Subsidiado'].sum())
                resumen_ejecucion['sub_diferencia'] = float(df_rep['Diferencia'].sum())
                resumen_ejecucion['df_rep'] = df_rep

            except Exception as e:
                log_msg(f"Advertencia procesando subsidios/valores: {e}")

        _render_modal_progreso("Finalizando informes y preparando archivos...", 100)
        resumen_ejecucion['logs'] = logs
        resumen_ejecucion['output_files'] = output_files
        st.session_state['resultado_auditoria'] = resumen_ejecucion
        st.session_state['toast_auditoria_pendiente'] = {
            'total_registros': resumen_ejecucion['total_registros'],
            'sss_err': resumen_ejecucion.get('sss_err_count', 0),
            'afip_err': resumen_ejecucion.get('afip_err_count', 0),
        }
        modal_progreso.empty()
        st.rerun()

    except Exception as e:
        modal_progreso.empty()
        st.error(f"Error en el procesamiento: {e}")


# =============================================================================
# PANEL DE RESULTADOS (PASO 3 - PERSISTENTE EN SESSION_STATE)
# =============================================================================
if 'resultado_auditoria' in st.session_state:
    toast_aud = st.session_state.pop('toast_auditoria_pendiente', None)
    if toast_aud:
        st.toast(
            f":green[:material/check_circle:] Auditoría completada · {toast_aud['total_registros']:,} registros evaluados",
            duration="long"
        )
        if toast_aud['sss_err'] > 0 or toast_aud['afip_err'] > 0:
            st.toast(
                f":orange[:material/warning:] Observaciones detectadas — SSSalud: {toast_aud['sss_err']:,} · AFIP: {toast_aud['afip_err']:,}",
                duration="long"
            )

    res = st.session_state['resultado_auditoria']
    output_files = res.get('output_files', {})

    with st.container(border=True, key="card_resultados"):
        col_res_title, col_res_back = st.columns([3.3, 1.0], gap="medium")
        with col_res_title:
            st.markdown(
                f'<p class="sapi-card-title">{_svg_inline("check_circle", "#16a34a", 18)}<span>3. Informe de Validación y Resultados</span></p>'
                f'<p class="sapi-card-sub">Lote procesado: <b>{html.escape(str(res["archivo_nombre"]))}</b> · '
                f'Período: <b>{html.escape(str(res["periodo"]))}</b> · '
                f'Ejecución: {html.escape(str(res["timestamp"]))}</p>',
                unsafe_allow_html=True,
            )
        with col_res_back:
            if st.button("Volver atrás", key="btn_volver_atras", icon=":material/arrow_back:", use_container_width=True):
                st.session_state.pop('resultado_auditoria', None)
                st.session_state['ultimo_lote_notificado'] = None
                st.rerun()

        # ---------------------------------------------------------------------
        # TARJETAS KPI ESTILO SAPI WEB
        # ---------------------------------------------------------------------
        # Card 1: Lote procesado
        card1_html = (
            f'<div class="kpi-box kpi-box-info">'
            f'<div class="kpi-box-top"><p class="kpi-box-label">Lote procesado</p>{_svg_inline("clipboard", "#1d4ed8", 18)}</div>'
            f'<p class="kpi-box-val">{res.get("total_registros", 0):,} reg.</p>'
            f'<div class="kpi-box-delta">'
            f'<div>{res.get("cuils_unicos", 0):,} beneficiarios</div>'
            f'<div style="font-weight: 700; color: #1e40af; white-space: nowrap;">{formato_moneda(res.get("importe_total_lote", 0))}</div>'
            f'</div>'
            f'</div>'
        )

        # Card 2: Control SSSalud
        if res.get('sss_ejecutado'):
            ok_c = res.get('sss_ok_count', 0)
            err_c = res.get('sss_err_count', 0)
            tot_c = max(1, ok_c + err_c)
            tasa_ok = (ok_c / tot_c) * 100
            cls_sss = "kpi-box-ok" if err_c == 0 else "kpi-box-warn"
            ico_sss = _svg_inline("check_circle", "#16a34a", 18) if err_c == 0 else _svg_inline("alert_triangle", "#d97706", 18)
            card2_html = (
                f'<div class="kpi-box {cls_sss}">'
                f'<div class="kpi-box-top"><p class="kpi-box-label">Control SSSalud</p>{ico_sss}</div>'
                f'<p class="kpi-box-val">{tasa_ok:.1f}% OK</p>'
                f'<div class="kpi-box-delta">'
                f'<div>{ok_c:,} aprobados</div>'
                f'<div>{err_c:,} observados</div>'
                f'</div>'
                f'</div>'
            )
        else:
            card2_html = (
                f'<div class="kpi-box kpi-box-neutral">'
                f'<div class="kpi-box-top"><p class="kpi-box-label">Control SSSalud</p>{_svg_inline("shield", "#94a3b8", 18)}</div>'
                f'<p class="kpi-box-val">No ejecutado</p>'
                f'<p class="kpi-box-delta">No incluido en el alcance</p>'
                f'</div>'
            )

        # Card 3: Cruce AFIP
        if res.get('afip_ejecutado'):
            a_ok = res.get('afip_ok_count', 0)
            a_err = res.get('afip_err_count', 0)
            a_tot = max(1, a_ok + a_err)
            tasa_afip = (a_ok / a_tot) * 100
            cls_afip = "kpi-box-ok" if a_err == 0 else "kpi-box-err"
            ico_afip = _svg_inline("check_circle", "#16a34a", 18) if a_err == 0 else _svg_inline("x_circle", "#dc2626", 18)
            card3_html = (
                f'<div class="kpi-box {cls_afip}">'
                f'<div class="kpi-box-top"><p class="kpi-box-label">Cruce AFIP</p>{ico_afip}</div>'
                f'<p class="kpi-box-val">{tasa_afip:.1f}% válido</p>'
                f'<p class="kpi-box-delta">{a_ok:,} validados · {a_err:,} con diferencia</p>'
                f'</div>'
            )
        else:
            card3_html = (
                f'<div class="kpi-box kpi-box-neutral">'
                f'<div class="kpi-box-top"><p class="kpi-box-label">Cruce AFIP</p>{_svg_inline("search", "#94a3b8", 18)}</div>'
                f'<p class="kpi-box-val">Sin cruce</p>'
                f'<p class="kpi-box-delta">Omitido o sin Libros IVA</p>'
                f'</div>'
            )

        # Card 4: Subsidio proyectado
        if res.get('sub_ejecutado'):
            sol = res.get('sub_solicitado', 0.0)
            sub = res.get('sub_subsidiado', 0.0)
            dif = res.get('sub_diferencia', 0.0)
            pct_cob = (sub / sol * 100) if sol > 0 else 0.0
            card4_html = (
                f'<div class="kpi-box kpi-box-info">'
                f'<div class="kpi-box-top"><p class="kpi-box-label">Subsidio proyectado</p>{_svg_inline("coins", "#1d4ed8", 18)}</div>'
                f'<p class="kpi-box-val">{formato_moneda(sub)}</p>'
                f'<p class="kpi-box-delta">Cobertura: {pct_cob:.1f}% · Dif. tope: {formato_moneda(dif)}</p>'
                f'</div>'
            )
        else:
            card4_html = (
                f'<div class="kpi-box kpi-box-neutral">'
                f'<div class="kpi-box-top"><p class="kpi-box-label">Subsidio proyectado</p>{_svg_inline("coins", "#94a3b8", 18)}</div>'
                f'<p class="kpi-box-val">Sin cálculo</p>'
                f'<p class="kpi-box-delta">Omitido o sin Nomenclador</p>'
                f'</div>'
            )

        st.markdown(
            f'<div class="kpi-grid-4">{card1_html}{card2_html}{card3_html}{card4_html}</div>',
            unsafe_allow_html=True,
        )

        # ---------------------------------------------------------------------
        # PESTAÑAS DE EXPLORACIÓN Y DESCARGA
        # ---------------------------------------------------------------------
        tab_descargas, tab_sss, tab_afip, tab_sub = st.tabs([
            f"Archivos generados ({len(output_files)})",
            "Control SSSalud",
            "Cruce AFIP",
            "Subsidios y topes"
        ])

        # --- TAB 1: ARCHIVOS GENERADOS ---
        with tab_descargas:
            if output_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for fname, content in output_files.items():
                        zip_file.writestr(fname, content)

                col_zip, col_ind = st.columns([1.0, 2.0], gap="large")
                with col_zip:
                    with st.container(key="dl_panel_zip"):
                        st.markdown("##### Paquete completo")
                        st.markdown('<p class="dl-subcap">Todos los archivos juntos en formato <code>.zip</code>:</p>', unsafe_allow_html=True)
                        st.download_button(
                            label="Descargar paquete completo (.zip)",
                            data=zip_buffer.getvalue(),
                            file_name=f"Resultados_Auditoria_{res['periodo']}.zip",
                            mime="application/zip",
                            key="btn_zip_paquete",
                            icon=":material/folder_zip:",
                            type="primary",
                            use_container_width=True
                        )

                with col_ind:
                    with st.container(key="dl_panel_ind"):
                        st.markdown("##### Descarga individual")
                        st.markdown('<p class="dl-subcap">Seleccione un archivo para descargarlo por separado:</p>', unsafe_allow_html=True)
                        cols_arch = st.columns(2, gap="small")
                        for idx, (fname, content) in enumerate(output_files.items()):
                            lineas_cant = len([ln for ln in content.splitlines() if ln.strip()])
                            with cols_arch[idx % 2]:
                                st.download_button(
                                    label=f"{fname} ({lineas_cant:,})",
                                    data=content.encode('latin1', errors='replace') if not fname.endswith('.csv') else content.encode('utf-8-sig'),
                                    file_name=fname,
                                    mime="text/plain",
                                    key=f"dl_{fname}",
                                    icon=":material/download:",
                                    use_container_width=True
                                )
            else:
                st.warning("No se generaron archivos de salida en esta ejecución.")

        # --- TAB 2: DETALLE SSSALUD ---
        with tab_sss:
            if not res.get('sss_ejecutado'):
                st.info("El módulo Control SSSalud no fue incluido en esta ejecución.")
            else:
                err_c = res.get('sss_err_count', 0)
                ok_c = res.get('sss_ok_count', 0)
                if err_c == 0:
                    st.success(f"Sin observaciones. Los {ok_c:,} registros superaron las validaciones de SSSalud.")
                else:
                    st.warning(f"Se registraron {err_c:,} filas con observaciones sobre un total de {ok_c + err_c:,} registros evaluados.")
                    st.markdown("##### Detalle de registros observados (`DS.DEVERR`)")
                    df_sss_err = res['df_sss_err']
                    if 'Descripcion codigo' not in df_sss_err.columns and 'Codigo_Rechazo' in df_sss_err.columns:
                        df_sss_err = df_sss_err.copy()
                        df_sss_err['Descripcion codigo'] = df_sss_err['Codigo_Rechazo'].apply(
                            lambda x: describir_codigos(x, CATALOGO_ERRORES_SSS, sep='-')
                        )
                    filtro_cod = st.text_input(
                        "Filtrar por CUIL, CUIT Prestador, código o descripción (ej. 404, 411):",
                        icon=":material/search:",
                        key="filtro_sss"
                    )
                    config_sss = {
                        'Descripcion codigo': st.column_config.TextColumn("Descripcion codigo", width="large"),
                    }
                    if filtro_cod:
                        mask_f = (
                            df_sss_err['CUIL'].astype(str).str.contains(filtro_cod, case=False, na=False) |
                            df_sss_err['CUIT_Prestador'].astype(str).str.contains(filtro_cod, case=False, na=False) |
                            df_sss_err['Codigo_Rechazo'].astype(str).str.contains(filtro_cod, case=False, na=False) |
                            df_sss_err['Descripcion codigo'].astype(str).str.contains(filtro_cod, case=False, na=False)
                        )
                        st.dataframe(df_sss_err[mask_f], column_config=config_sss, use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(df_sss_err, column_config=config_sss, use_container_width=True, hide_index=True)

        # --- TAB 3: DETALLE AFIP ---
        with tab_afip:
            if not res.get('afip_ejecutado'):
                st.info("El control AFIP no se ejecutó. Verifique que el modo seleccionado lo incluya y que se hayan cargado los Libros IVA en el panel lateral.")
            else:
                a_err = res.get('afip_err_count', 0)
                a_ok = res.get('afip_ok_count', 0)
                if a_err == 0:
                    st.success(f"Sin discrepancias. Los {a_ok:,} comprobantes coinciden en existencia, fecha e importe con los Libros IVA.")
                else:
                    st.warning(f"Se detectaron {a_err:,} comprobantes con observaciones en el cruce contra Libros IVA (`DS_WS.DEVERR`).")
                    col_a1, col_a2 = st.columns([1.1, 1.9], gap="medium")
                    with col_a1:
                        st.markdown("##### Resumen por tipo de error")
                        st.dataframe(res['df_afip_desglose'], use_container_width=True, hide_index=True)
                    with col_a2:
                        st.markdown("##### Comparativa TXT vs Libro IVA (`DS_WS.DEVERR`)")
                        df_afip_err = res['df_afip_err']
                        filtro_afip = st.text_input(
                            "Filtrar por CUIT Prestador, CUIL o código de error (100, 101, 110):",
                            icon=":material/search:",
                            key="filtro_afip"
                        )
                        if filtro_afip:
                            mask_af = (
                                df_afip_err['CUIT_Prestador'].str.contains(filtro_afip, case=False, na=False) |
                                df_afip_err['CUIL'].str.contains(filtro_afip, case=False, na=False) |
                                df_afip_err['Error_AFIP'].str.contains(filtro_afip, case=False, na=False)
                            )
                            st.dataframe(df_afip_err[mask_af], use_container_width=True, hide_index=True)
                        else:
                            st.dataframe(df_afip_err, use_container_width=True, hide_index=True)

        # --- TAB 4: PROYECCIÓN SUBSIDIOS ---
        with tab_sub:
            if not res.get('sub_ejecutado'):
                st.info("El cálculo de subsidios no se ejecutó. Verifique que el modo seleccionado lo incluya y que se haya cargado la tabla de Valores Nomenclador.")
            else:
                df_rep = res['df_rep']
                st.markdown(
                    f"""
                    <div class="rev-kpi-bar">
                        <div class="rev-kpi-item">
                            <p class="rev-kpi-label">{_svg_inline("clipboard", "#475569", 16)}<span>Total solicitado</span></p>
                            <p class="rev-kpi-val">{formato_moneda(res['sub_solicitado'])}</p>
                        </div>
                        <div class="rev-kpi-item">
                            <p class="rev-kpi-label" style="color: #166534;">{_svg_inline("check_circle", "#16a34a", 16)}<span>Total subsidiable (tope SSS)</span></p>
                            <p class="rev-kpi-val" style="color: #15803d;">{formato_moneda(res['sub_subsidiado'])}</p>
                        </div>
                        <div class="rev-kpi-item">
                            <p class="rev-kpi-label" style="color: #b45309;">{_svg_inline("alert_triangle", "#d97706", 16)}<span>Diferencia / recorte por tope</span></p>
                            <p class="rev-kpi-val" style="color: #b45309;">{formato_moneda(res['sub_diferencia'])}</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("##### Resumen por convenio")
                df_conv = (
                    df_rep.groupby('Convenio', as_index=False)[['Importe Solicitado', 'Importe Subsidiado', 'Diferencia']]
                    .sum()
                    .sort_values(by='Importe Solicitado', ascending=False)
                )
                config_moneda = {
                    'Importe Solicitado': st.column_config.NumberColumn("Importe Solicitado", format="$ %.2f"),
                    'Importe Subsidiado': st.column_config.NumberColumn("Importe Subsidiado", format="$ %.2f"),
                    'Diferencia': st.column_config.NumberColumn("Diferencia", format="$ %.2f"),
                }
                st.dataframe(
                    df_conv,
                    column_config=config_moneda,
                    use_container_width=True,
                    hide_index=True
                )

                st.markdown("##### Detalle por beneficiario y práctica")
                fcol1, fcol2 = st.columns([1, 2])
                with fcol1:
                    solo_con_dif = st.checkbox("Mostrar solo registros con diferencia mayor a $0", value=False)
                with fcol2:
                    buscar_sub = st.text_input(
                        "Buscar por CUIL, nombre, convenio o código de práctica:",
                        icon=":material/search:",
                        key="filtro_sub"
                    )

                df_vista_sub = df_rep.copy()
                if solo_con_dif:
                    df_vista_sub = df_vista_sub[df_vista_sub['Diferencia'] > 0.009]
                if buscar_sub:
                    mask_s = (
                        df_vista_sub['CUIL'].astype(str).str.contains(buscar_sub, case=False, na=False) |
                        df_vista_sub['Nombre'].astype(str).str.contains(buscar_sub, case=False, na=False) |
                        df_vista_sub['Convenio'].astype(str).str.contains(buscar_sub, case=False, na=False) |
                        df_vista_sub['Codigo'].astype(str).str.contains(buscar_sub, case=False, na=False)
                    )
                    df_vista_sub = df_vista_sub[mask_s]

                st.dataframe(
                    df_vista_sub,
                    column_config=config_moneda,
                    use_container_width=True,
                    hide_index=True
                )
