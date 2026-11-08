import streamlit as st
import pandas as pd
import numpy as np
import os
import glob
from datetime import datetime
from decimal import Decimal
import io
import zipfile

# =============================================================================
# CONFIGURACIÓN DE PÁGINA Y CONSTANTES DE NEGOCIO
# =============================================================================
st.set_page_config(
    page_title="Auditoría Preventiva SSSalud | Mecanismo de Integración",
    page_icon="🛡️",
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
# ESTILOS VISUALES (CSS PERSONALIZADO)
# =============================================================================
st.markdown("""
<style>
    /* Tipografía y espaciado general */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Banner Hero Principal */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #0284c7 100%);
        color: #ffffff;
        padding: 1.75rem 2rem;
        border-radius: 16px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    .hero-badge {
        display: inline-block;
        background: rgba(56, 189, 248, 0.2);
        color: #bae6fd;
        border: 1px solid rgba(56, 189, 248, 0.4);
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        margin-bottom: 0.6rem;
    }
    .hero-title {
        font-size: 1.85rem;
        font-weight: 800;
        margin: 0 0 0.35rem 0;
        letter-spacing: -0.02em;
        color: #ffffff;
    }
    .hero-subtitle {
        font-size: 0.98rem;
        color: #e2e8f0;
        margin: 0;
        opacity: 0.92;
        line-height: 1.5;
    }

    /* Tarjetas de Sección y Pasos */
    .section-card {
        background: rgba(128, 128, 128, 0.04);
        border: 1px solid rgba(128, 128, 128, 0.18);
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }
    .step-header {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin-bottom: 0.75rem;
    }
    .step-number {
        background: linear-gradient(135deg, #2563eb, #0284c7);
        color: white;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
        flex-shrink: 0;
    }
    .step-title {
        font-size: 1.15rem;
        font-weight: 700;
        margin: 0;
    }

    /* Tarjetas de KPI de Resultados */
    .kpi-card {
        background: rgba(128, 128, 128, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-left: 4px solid #0284c7;
        border-radius: 12px;
        padding: 1rem 1.15rem;
        height: 100%;
    }
    .kpi-card.kpi-success { border-left-color: #10b981; }
    .kpi-card.kpi-danger  { border-left-color: #ef4444; }
    .kpi-card.kpi-warning { border-left-color: #f59e0b; }
    .kpi-card.kpi-purple  { border-left-color: #8b5cf6; }

    .kpi-label {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.75;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 0.2rem;
    }
    .kpi-delta {
        font-size: 0.8rem;
        opacity: 0.85;
    }

    /* Botón primario más destacado */
    div.stButton > button[kind="primary"] {
        border-radius: 10px;
        font-weight: 700;
        padding: 0.65rem 1.25rem;
        font-size: 1rem;
        box-shadow: 0 4px 14px rgba(2, 132, 199, 0.35);
        transition: all 0.2s ease;
    }
    div.stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(2, 132, 199, 0.45);
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# FUNCIONES AUXILIARES DE FORMATO Y UI
# =============================================================================
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
    return "Formato inválido (Use YYYYMM)"


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


# =============================================================================
# BARRA LATERAL - BASES DE DATOS E HISTÓRICOS (CRUCES)
# =============================================================================
with st.sidebar:
    st.markdown("## 🗂️ Centro de Bases de Datos")
    st.caption("Despliegue las secciones que necesite para cargar padrones, históricos y tablas de cruce.")

    with st.expander("🏥 1. Control Médico SSSalud", expanded=False):
        file_cert = st.file_uploader(
            "🪪 Base Certificados (Excel)",
            type=["xlsx"],
            help="Padrón de certificados CUD con columna 'Cuil' y 'Edad' (encabezado en fila 5)."
        )
        files_devok = st.file_uploader(
            "📜 Históricos DEVOK (CSV/TXT)",
            type=["csv", "txt"],
            accept_multiple_files=True,
            help="Archivos DEVOK de períodos anteriores para detectar duplicados (-411) y validar apoyos/transporte (-408, -415)."
        )

    with st.expander("🧾 2. Control Fiscal AFIP", expanded=False):
        files_iva = st.file_uploader(
            "📑 Libros IVA AFIP (Excel/CSV)",
            type=["xlsx", "csv"],
            accept_multiple_files=True,
            help="Exportaciones de Mis Comprobantes / Libro IVA Digital para validar existencia (100), fecha (101) e importe (110)."
        )

    with st.expander("💰 3. Subsidios y Padrón", expanded=False):
        file_val = st.file_uploader(
            "📊 Valores Nomenclador (Excel)",
            type=["xlsx"],
            help="Matriz de valores vigentes por código de práctica y período (YYYYMM)."
        )
        file_afil = st.file_uploader(
            "👥 Base Afiliados (Excel)",
            type=["xlsx"],
            help="Padrón de afiliados con 'Cuil', 'Nombre' y 'Convenio' para enriquecer el reporte de diferencias."
        )

    st.markdown("---")
    with st.expander("📖 Guía de Códigos de Rechazo", expanded=False):
        st.markdown("**🏥 Códigos SSSalud (`DS.DEVERR`)**")
        for cod, desc in CATALOGO_ERRORES_SSS.items():
            st.markdown(f"- **`-{cod}`**: {desc}")
        st.markdown("---")
        st.markdown("**🧾 Códigos AFIP (`DS_WS.DEVERR`)**")
        for cod, desc in CATALOGO_ERRORES_AFIP.items():
            st.markdown(f"- **`{cod}-`**: {desc}")


# =============================================================================
# ENCABEZADO PRINCIPAL (HERO BANNER)
# =============================================================================
st.markdown("""
<div class="hero-banner">
    <div class="hero-badge">🛡️ Ley 24.901 · Mecanismo de Integración</div>
    <h1 class="hero-title">🏥 Sistema de Auditoría Preventiva SSSalud</h1>
    <p class="hero-subtitle">
        Validación integral pre-presentación: detecte inconsistencias médicas (<b>DS.DEVERR</b>),
        verifique comprobantes contra Libros IVA (<b>AFIP WS</b>) y proyecte topes de reintegro (<b>DS.SUBSIDIO</b>) en segundos.
    </p>
</div>
""", unsafe_allow_html=True)


# =============================================================================
# PASO 1: PARÁMETROS DE EJECUCIÓN Y ARCHIVO DE ENTRADA
# =============================================================================
st.markdown("""
<div class="step-header">
    <span class="step-number">1</span>
    <h3 class="step-title">Parámetros Institucionales y Modo de Auditoría</h3>
</div>
""", unsafe_allow_html=True)

with st.container():
    col1, col2, col3, col4 = st.columns([1.1, 1.2, 1.1, 1.8])

    with col1:
        rnos_ingresado = st.text_input(
            "🏛️ RNOS Institucional",
            value="999999",
            help="Número de Registro Nacional de Obras Sociales"
        )
    with col2:
        cuit_os_ingresado = st.text_input(
            "🆔 CUIT Obra Social (Propio)",
            value="30000000000",
            help="CUIT institucional utilizado para el armado de líneas de subsidio"
        )
    with col3:
        hoy = datetime.now()
        mes_def = hoy.month - 1 if hoy.month > 1 else 12
        anio_def = hoy.year if hoy.month > 1 else hoy.year - 1
        periodo_defecto = f"{anio_def}{mes_def:02d}"

        periodo_pres = st.text_input(
            "📅 Período (YYYYMM)",
            value=periodo_defecto,
            help="Período de presentación en formato de 6 dígitos (ej. 202610)"
        )
        st.caption(f"📌 **{formatear_periodo_legible(periodo_pres)}**")

    with col4:
        modo = st.selectbox(
            "🎯 Alcance del Control:",
            (
                "PROCESO COMPLETO (Todo lo anterior)",
                "Control SSSalud (Lógica Médica)",
                "Control AFIP (Cruce c/Libros IVA)",
                "Cálculo Subsidios (Económico)"
            ),
            help="Elija si desea correr los 3 módulos en simultáneo o un módulo específico."
        )
        descripciones_modo = {
            "PROCESO COMPLETO (Todo lo anterior)": "Ejecuta Control Médico + Cruce AFIP + Proyección de Subsidios.",
            "Control SSSalud (Lógica Médica)": "Genera archivos DEVOK y DEVERR según reglas de negocio SSSalud.",
            "Control AFIP (Cruce c/Libros IVA)": "Cruza facturas del lote contra los Libros IVA Digitales cargados.",
            "Cálculo Subsidios (Económico)": "Calcula topes según Nomenclador y genera DS.SUBSIDIO + Reporte."
        }
        st.caption(f"ℹ️ {descripciones_modo.get(modo, '')}")

# =============================================================================
# PASO 2: CARGA DEL ARCHIVO PRINCIPAL DE PRESTACIONES
# =============================================================================
st.markdown("""
<div class="step-header" style="margin-top: 0.75rem;">
    <span class="step-number">2</span>
    <h3 class="step-title">Archivo Principal de Prestaciones (_ds.txt)</h3>
</div>
""", unsafe_allow_html=True)

archivo_txt = st.file_uploader(
    "📄 Seleccione o arrastre aquí el archivo TXT principal de prestaciones (_ds.txt)",
    type=["txt"],
    help="Archivo separado por pipes (|) con las 19 columnas reglamentarias de SSSalud. Para cargar bases adicionales (Certificados, DEVOK, IVA, Nomenclador o Afiliados), abra el panel lateral izquierdo (❯)."
)


# =============================================================================
# VISTA PREVIA RÁPIDA DEL LOTE CARGADO
# =============================================================================
if archivo_txt is not None:
    try:
        archivo_txt.seek(0)
        df_preview = pd.read_csv(archivo_txt, sep='|', names=COLUMNAS, dtype=str, encoding='latin1', header=None)
        archivo_txt.seek(0)

        imp_prev = (pd.to_numeric(df_preview['Importe_Solicitado'], errors='coerce').fillna(0) / 100.0).sum()
        cuils_unicos = df_preview['CUIL'].nunique()
        prest_unicos = df_preview['CUIT_Prestador'].nunique()
        periodos_lote = ", ".join(sorted(df_preview['Periodo_Prestacion'].dropna().unique())[:5])

        with st.expander(
            f"🔎 Vista Previa del Lote Cargado: {archivo_txt.name} — {len(df_preview):,} registros | Total Solicitado: {formato_moneda(imp_prev)}",
            expanded=False
        ):
            pcol1, pcol2, pcol3, pcol4 = st.columns(4)
            pcol1.metric("Registros en Lote", f"{len(df_preview):,}")
            pcol2.metric("Beneficiarios (CUIL)", f"{cuils_unicos:,}")
            pcol3.metric("Prestadores (CUIT)", f"{prest_unicos:,}")
            pcol4.metric("Importe Total Solicitado", formato_moneda(imp_prev))
            st.caption(f"Períodos de prestación detectados en el archivo: **{periodos_lote}**")
            st.dataframe(df_preview.head(25), use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"⚠️ No se pudo generar la vista previa del archivo TXT: {e}")

st.markdown("---")


# =============================================================================
# EJECUCIÓN DE LA AUDITORÍA
# =============================================================================
if archivo_txt is not None:
    periodo_valido = len(periodo_pres) == 6 and periodo_pres.isdigit()
    if not periodo_valido:
        st.error("❌ El período de presentación debe tener exactamente 6 dígitos numéricos (formato YYYYMM).")
    else:
        col_btn, col_info = st.columns([1.2, 2.8])
        with col_btn:
            iniciar_auditoria = st.button(
                "🚀 INICIAR PROCESO DE AUDITORÍA",
                type="primary",
                use_container_width=True
            )
        with col_info:
            st.info(
                f"Listo para auditar **{archivo_txt.name}** bajo el modo **{modo}** "
                f"para el período **{periodo_pres}** ({formatear_periodo_legible(periodo_pres)})."
            )

        if iniciar_auditoria:
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

            with st.spinner("Ejecutando validaciones médicas, cruces fiscales y cálculo de subsidios..."):
                try:
                    # Asegurar puntero al inicio en re-ejecuciones
                    archivo_txt.seek(0)
                    df = pd.read_csv(archivo_txt, sep='|', names=COLUMNAS, dtype=str, encoding='latin1', header=None)
                    log_msg(f"✅ Registros cargados desde TXT: {len(df)}")

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
                    if modo in ["Control SSSalud (Lógica Médica)", "PROCESO COMPLETO (Todo lo anterior)"]:
                        log_msg(">>> [1/3] Ejecutando Control SSSalud...")
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
                                log_msg(f"⚠️ Error leyendo padrón de certificados: {e}")

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
                            log_msg(f"   -> Generado OK: {name_ok} ({len(df_ok)} registros)")

                        df_err = df[df['Codigo_Rechazo'] != ''].copy()
                        if not df_err.empty:
                            name_err = f"{rnos_ingresado}-{periodo_pres}_DS.DEVERR"
                            buf_err = io.StringIO()
                            df_err[COLUMNAS + ['Codigo_Rechazo']].to_csv(buf_err, sep='|', index=False, header=False, encoding='latin1')
                            output_files[name_err] = buf_err.getvalue()
                            log_msg(f"   -> Generado ERR: {name_err} ({len(df_err)} registros)")

                        resumen_ejecucion['sss_ok_count'] = len(df_ok)
                        resumen_ejecucion['sss_err_count'] = len(df_err)
                        resumen_ejecucion['df_sss_err'] = df_err[COLUMNAS + ['Codigo_Rechazo']].copy() if not df_err.empty else pd.DataFrame()
                        resumen_ejecucion['df_sss_desglose'] = desglosar_errores(df_err['Codigo_Rechazo'], CATALOGO_ERRORES_SSS, sep='-') if not df_err.empty else pd.DataFrame()

                    # ---------------------------------------------------------
                    # 2. CONTROL AFIP
                    # ---------------------------------------------------------
                    if modo in ["Control AFIP (Cruce c/Libros IVA)", "PROCESO COMPLETO (Todo lo anterior)"]:
                        log_msg(">>> [2/3] Ejecutando Control AFIP...")
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
                                    log_msg(f"⚠️ Error leyendo libro IVA {f.name}: {e}")

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
                                    log_msg(f"   -> Generado AFIP ERR: {name_err} ({len(df_afip_err)} registros)")

                                df_afip_ok = df_merged[df_merged['Error_AFIP'] == ''].copy()
                                if not df_afip_ok.empty:
                                    name_ok = f"{rnos_ingresado}-{periodo_pres}_DS_WS.DEVOK_AFIP"
                                    buf_aok = io.StringIO()
                                    df_afip_ok[COLUMNAS].to_csv(buf_aok, sep='|', index=False, header=False, encoding='latin1')
                                    output_files[name_ok] = buf_aok.getvalue()
                                    log_msg(f"   -> Generado AFIP OK: {name_ok} ({len(df_afip_ok)} registros)")

                                resumen_ejecucion['afip_ok_count'] = len(df_afip_ok)
                                resumen_ejecucion['afip_err_count'] = len(df_afip_err)
                                cols_vista_afip = [
                                    'CUIL', 'CUIT_Prestador', 'Pto_Venta', 'Num_Comp',
                                    'TXT_FECHA_ISO', 'IVA_FECHA_ISO', 'TXT_TOTAL_DEC', 'IVA_TOTAL_DEC', 'Error_AFIP'
                                ]
                                resumen_ejecucion['df_afip_err'] = df_afip_err[cols_vista_afip].astype(str).copy() if not df_afip_err.empty else pd.DataFrame()
                                resumen_ejecucion['df_afip_desglose'] = desglosar_errores(df_afip_err['Error_AFIP'], CATALOGO_ERRORES_AFIP, sep='-') if not df_afip_err.empty else pd.DataFrame()
                        else:
                            log_msg("⚠️ No se cargaron libros IVA. Se omite control AFIP.")

                    # ---------------------------------------------------------
                    # 3. CÁLCULO SUBSIDIOS
                    # ---------------------------------------------------------
                    if modo in ["Cálculo Subsidios (Económico)", "PROCESO COMPLETO (Todo lo anterior)"]:
                        log_msg(">>> [3/3] Ejecutando Cálculo de Subsidios...")
                        if file_val is not None:
                            try:
                                file_val.seek(0)
                                df_val = pd.read_excel(file_val, dtype=str, engine='openpyxl')
                                df_val.columns = df_val.columns.astype(str).str.strip()
                                df_val['Cod_Int'] = pd.to_numeric(df_val['CODIGO'], errors='coerce').fillna(0).astype(int).astype(str)
                                df_val.set_index('Cod_Int', inplace=True)

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
                                log_msg(f"   -> Subsidio generado: {name_sub} ({len(df_grouped)} líneas)")

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
                                log_msg(f"   -> Reporte Detallado: {name_rep}")

                                resumen_ejecucion['sub_ejecutado'] = True
                                resumen_ejecucion['sub_solicitado'] = float(df_rep['Importe Solicitado'].sum())
                                resumen_ejecucion['sub_subsidiado'] = float(df_rep['Importe Subsidiado'].sum())
                                resumen_ejecucion['sub_diferencia'] = float(df_rep['Diferencia'].sum())
                                resumen_ejecucion['df_rep'] = df_rep

                            except Exception as e:
                                log_msg(f"⚠️ Error procesando subsidios/valores: {e}")
                        else:
                            log_msg("⚠️ Falta cargar la base de valores nomenclador para el cálculo de subsidios.")

                    resumen_ejecucion['logs'] = logs
                    resumen_ejecucion['output_files'] = output_files
                    st.session_state['resultado_auditoria'] = resumen_ejecucion

                except Exception as e:
                    st.error(f"❌ Error crítico en el proceso: {e}")
else:
    st.info("👆 **Para comenzar:** Cargue el archivo principal de prestaciones (`_ds.txt`) en el **Paso 2** y configure las bases de cruce necesarias en el panel izquierdo.")


# =============================================================================
# PANEL DE RESULTADOS INTERACTIVO (PERSISTENTE EN SESSION_STATE)
# =============================================================================
if 'resultado_auditoria' in st.session_state:
    res = st.session_state['resultado_auditoria']
    output_files = res.get('output_files', {})
    logs = res.get('logs', [])

    st.markdown(
        '<div class="step-header" style="margin-top: 0.5rem;">'
        '<span class="step-number">3</span>'
        '<h3 class="step-title">Tablero de Resultados y Centro de Descargas</h3>'
        '</div>',
        unsafe_allow_html=True
    )

    st.success(
        f"🎉 **¡Auditoría finalizada con éxito!** — Lote `{res['archivo_nombre']}` · "
        f"Período `{res['periodo']}` · Ejecutado el {res['timestamp']}"
    )

    # -------------------------------------------------------------------------
    # TARJETAS KPI EJECUTIVAS
    # -------------------------------------------------------------------------
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">📄 Lote Procesado</div>'
            f'<div class="kpi-value">{res.get("total_registros", 0):,} reg.</div>'
            f'<div class="kpi-delta">👥 {res.get("cuils_unicos", 0):,} beneficiarios · {formato_moneda(res.get("importe_total_lote", 0))}</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    with k2:
        if res.get('sss_ejecutado'):
            ok_c = res.get('sss_ok_count', 0)
            err_c = res.get('sss_err_count', 0)
            tot_c = max(1, ok_c + err_c)
            tasa_ok = (ok_c / tot_c) * 100
            color_cls = "kpi-success" if err_c == 0 else "kpi-warning"
            st.markdown(
                f'<div class="kpi-card {color_cls}">'
                f'<div class="kpi-label">🏥 Control SSSalud</div>'
                f'<div class="kpi-value">{tasa_ok:.1f}% OK</div>'
                f'<div class="kpi-delta">✅ {ok_c:,} aprobados · ❌ {err_c:,} rechazados</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="kpi-card">'
                '<div class="kpi-label">🏥 Control SSSalud</div>'
                '<div class="kpi-value">No ejecutado</div>'
                '<div class="kpi-delta">Omitido según modo seleccionado</div>'
                '</div>',
                unsafe_allow_html=True
            )

    with k3:
        if res.get('afip_ejecutado'):
            a_ok = res.get('afip_ok_count', 0)
            a_err = res.get('afip_err_count', 0)
            a_tot = max(1, a_ok + a_err)
            tasa_afip = (a_ok / a_tot) * 100
            color_afip = "kpi-success" if a_err == 0 else "kpi-danger"
            st.markdown(
                f'<div class="kpi-card {color_afip}">'
                f'<div class="kpi-label">🧾 Cruce Fiscal AFIP</div>'
                f'<div class="kpi-value">{tasa_afip:.1f}% Validado</div>'
                f'<div class="kpi-delta">✅ {a_ok:,} validados · ⚠️ {a_err:,} observados</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="kpi-card">'
                '<div class="kpi-label">🧾 Cruce Fiscal AFIP</div>'
                '<div class="kpi-value">Sin cruce</div>'
                '<div class="kpi-delta">Omitido o sin Libros IVA cargados</div>'
                '</div>',
                unsafe_allow_html=True
            )

    with k4:
        if res.get('sub_ejecutado'):
            sol = res.get('sub_solicitado', 0.0)
            sub = res.get('sub_subsidiado', 0.0)
            dif = res.get('sub_diferencia', 0.0)
            pct_cob = (sub / sol * 100) if sol > 0 else 0.0
            st.markdown(
                f'<div class="kpi-card kpi-purple">'
                f'<div class="kpi-label">💰 Subsidio Proyectado</div>'
                f'<div class="kpi-value">{formato_moneda(sub)}</div>'
                f'<div class="kpi-delta">Cobertura: {pct_cob:.1f}% · Dif. Tope: {formato_moneda(dif)}</div>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<div class="kpi-card">'
                '<div class="kpi-label">💰 Subsidio Proyectado</div>'
                '<div class="kpi-value">Sin cálculo</div>'
                '<div class="kpi-delta">Omitido o sin Nomenclador cargado</div>'
                '</div>',
                unsafe_allow_html=True
            )

    st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # PESTAÑAS DE EXPLORACIÓN Y DESCARGA
    # -------------------------------------------------------------------------
    tab_descargas, tab_sss, tab_afip, tab_sub, tab_logs = st.tabs([
        f"📥 Centro de Descargas ({len(output_files)})",
        "🏥 Detalle SSSalud",
        "🧾 Detalle AFIP",
        "💰 Proyección Subsidios",
        "📋 Registro de Logs"
    ])

    # --- TAB 1: CENTRO DE DESCARGAS ---
    with tab_descargas:
        if output_files:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for fname, content in output_files.items():
                    zip_file.writestr(fname, content)

            col_zip, col_ind = st.columns([1.15, 1.85])
            with col_zip:
                st.markdown("#### 📦 Paquete Completo")
                st.caption("Descargue todos los archivos generados en un único archivo comprimido listo para gestión.")
                st.download_button(
                    label=f"📦 Descargar Todo (.ZIP) — {len(output_files)} archivos",
                    data=zip_buffer.getvalue(),
                    file_name=f"Resultados_Auditoria_{res['periodo']}.zip",
                    mime="application/zip",
                    type="primary",
                    use_container_width=True
                )

            with col_ind:
                st.markdown("#### 📄 Descarga Individual por Archivo")
                st.caption("También puede descargar cada archivo de salida de manera independiente:")
                cols_arch = st.columns(2)
                for idx, (fname, content) in enumerate(output_files.items()):
                    lineas_cant = len([ln for ln in content.splitlines() if ln.strip()])
                    icono_f = "✅" if "DEVOK" in fname else ("❌" if "DEVERR" in fname else ("💰" if "SUBSIDIO" in fname else "📊"))
                    with cols_arch[idx % 2]:
                        st.download_button(
                            label=f"{icono_f} {fname} ({lineas_cant:,} lín.)",
                            data=content.encode('latin1', errors='replace') if not fname.endswith('.csv') else content.encode('utf-8-sig'),
                            file_name=fname,
                            mime="text/plain",
                            key=f"dl_{fname}",
                            use_container_width=True
                        )
        else:
            st.warning("⚠️ No se generaron archivos de salida en esta ejecución.")

    # --- TAB 2: DETALLE SSSALUD ---
    with tab_sss:
        if not res.get('sss_ejecutado'):
            st.info("ℹ️ El módulo **Control SSSalud** no fue seleccionado en esta ejecución.")
        else:
            err_c = res.get('sss_err_count', 0)
            ok_c = res.get('sss_ok_count', 0)
            if err_c == 0:
                st.success(f"✅ **¡Excelente!** Los {ok_c:,} registros superaron todas las validaciones de lógica médica de SSSalud sin rechazos.")
            else:
                st.warning(f"⚠️ Se detectaron **{err_c:,} registros con observaciones** sobre un total de {ok_c + err_c:,} registros evaluados.")
                col_d1, col_d2 = st.columns([1.1, 1.9])
                with col_d1:
                    st.markdown("##### 📊 Frecuencia por Código de Rechazo")
                    st.dataframe(res['df_sss_desglose'], use_container_width=True, hide_index=True)
                with col_d2:
                    st.markdown("##### 🔎 Registros Observados (`DS.DEVERR`)")
                    df_sss_err = res['df_sss_err']
                    filtro_cod = st.text_input(
                        "Filtrar por CUIL, CUIT Prestador o Código de Rechazo (ej. 404, 411):",
                        key="filtro_sss"
                    )
                    if filtro_cod:
                        mask_f = (
                            df_sss_err['CUIL'].str.contains(filtro_cod, case=False, na=False) |
                            df_sss_err['CUIT_Prestador'].str.contains(filtro_cod, case=False, na=False) |
                            df_sss_err['Codigo_Rechazo'].str.contains(filtro_cod, case=False, na=False)
                        )
                        st.dataframe(df_sss_err[mask_f], use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(df_sss_err, use_container_width=True, hide_index=True)

    # --- TAB 3: DETALLE AFIP ---
    with tab_afip:
        if not res.get('afip_ejecutado'):
            st.info("ℹ️ El módulo **Control AFIP** no se ejecutó (verifique que el modo lo incluya y que haya cargado los Libros IVA en la barra lateral).")
        else:
            a_err = res.get('afip_err_count', 0)
            a_ok = res.get('afip_ok_count', 0)
            if a_err == 0:
                st.success(f"✅ **¡Validación Fiscal Perfecta!** Los {a_ok:,} comprobantes coinciden exactamente en existencia, fecha e importe con los Libros IVA AFIP.")
            else:
                st.warning(f"⚠️ Se encontraron **{a_err:,} comprobantes con inconsistencias fiscales** (`DS_WS.DEVERR`).")
                col_a1, col_a2 = st.columns([1.1, 1.9])
                with col_a1:
                    st.markdown("##### 📊 Desglose de Errores AFIP")
                    st.dataframe(res['df_afip_desglose'], use_container_width=True, hide_index=True)
                with col_a2:
                    st.markdown("##### 🔎 Comparativa TXT vs Libro IVA (`DS_WS.DEVERR`)")
                    df_afip_err = res['df_afip_err']
                    filtro_afip = st.text_input(
                        "Filtrar por CUIT Prestador, CUIL o Código de Error (100, 101, 110):",
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
            st.info("ℹ️ El módulo **Cálculo de Subsidios** no se ejecutó (verifique que el modo lo incluya y que haya cargado la Base de Valores Nomenclador).")
        else:
            df_rep = res['df_rep']
            sc1, sc2, sc3 = st.columns(3)
            sc1.metric("💵 Total Solicitado", formato_moneda(res['sub_solicitado']))
            sc2.metric("🏦 Total Subsidiable (Tope SSS)", formato_moneda(res['sub_subsidiado']))
            sc3.metric("📉 Diferencia a Cargo / Recorte", formato_moneda(res['sub_diferencia']))

            st.markdown("##### 📊 Resumen Financiero por Convenio")
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

            st.markdown("##### 🔎 Explorador Detallado de Diferencias por Beneficiario y Práctica")
            fcol1, fcol2 = st.columns([1, 2])
            with fcol1:
                solo_con_dif = st.checkbox("Mostrar únicamente registros con Diferencia > $0", value=False)
            with fcol2:
                buscar_sub = st.text_input("Buscar por CUIL, Nombre, Convenio o Código de Práctica:", key="filtro_sub")

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

    # --- TAB 5: BITÁCORA DE EJECUCIÓN (LOGS) ---
    with tab_logs:
        st.markdown("##### 📋 Bitácora Técnica del Proceso")
        st.text_area("Detalles paso a paso de la ejecución:", "\n".join(logs), height=260)
