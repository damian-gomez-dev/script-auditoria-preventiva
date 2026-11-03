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
# CONFIGURACIÓN GENERAL
# =============================================================================
RNOS_FIJO = "999999"
CUIT_OS_PROPIO = "30000000000"

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

st.set_page_config(page_title="Sistema Integración SSSalud", layout="wide")

st.title(f"🏥 Sistema Integración SSSalud - RNOS: {RNOS_FIJO}")
st.markdown("Herramienta de auditoría preventiva, control AFIP y cálculo de subsidios adaptada para Streamlit.")

# =============================================================================
# BARRA LATERAL - CONFIGURACIÓN
# =============================================================================
st.sidebar.header("⚙️ Parámetros de Ejecución")

modo = st.sidebar.selectbox(
    "Seleccione el modo de control:",
    (
        "PROCESO COMPLETO (Todo lo anterior)",
        "Control SSSalud (Lógica Médica)",
        "Control AFIP (Cruce c/Libros IVA)",
        "Cálculo Subsidios (Económico)"
    )
)

hoy = datetime.now()
mes_def = hoy.month - 1 if hoy.month > 1 else 12
anio_def = hoy.year if hoy.month > 1 else hoy.year - 1
periodo_defecto = f"{anio_def}{mes_def:02d}"

periodo_pres = st.sidebar.text_input("Periodo de Presentación (YYYYMM)", value=periodo_defecto)

st.sidebar.markdown("---")
st.sidebar.subheader("📂 Carga de Archivos de Entrada")
archivo_txt = st.sidebar.file_uploader("Archivo TXT principal (_ds.txt)", type=["txt"])

# Opcionales (Bases de datos)
st.sidebar.markdown("#### Bases de Referencia (Opcional)")
file_cert = st.sidebar.file_uploader("Base Certificados (Excel)", type=["xlsx"])
file_afil = st.sidebar.file_uploader("Base Afiliados (Excel)", type=["xlsx"])
file_val = st.sidebar.file_uploader("Base Valores Nomenclador (Excel)", type=["xlsx"])

st.sidebar.markdown("#### Carpetas Históricas / Libros IVA")
files_devok = st.sidebar.file_uploader("Históricos DEVOK (Múltiples CSV/TXT)", type=["csv", "txt"], accept_multiple_files=True)
files_iva = st.sidebar.file_uploader("Libros IVA AFIP (Múltiples Excel/CSV)", type=["xlsx", "csv"], accept_multiple_files=True)


# =============================================================================
# LÓGICA DE PROCESAMIENTO
# =============================================================================
if archivo_txt is not None:
    if len(periodo_pres) != 6 or not periodo_pres.isdigit():
        st.error("❌ El periodo de presentación debe tener exactamente 6 dígitos (YYYYMM).")
    else:
        if st.button("🚀 INICIAR PROCESO DE AUDITORÍA", type="primary"):
            logs = []
            output_files = {}

            def log_msg(msg):
                logs.append(msg)

            with st.spinner("Ejecutando validaciones y cálculos..."):
                try:
                    # Leer TXT Principal
                    df = pd.read_csv(archivo_txt, sep='|', names=COLUMNAS, dtype=str, encoding='latin1', header=None)
                    log_msg(f"✅ Registros cargados desde TXT: {len(df)}")

                    # Conversiones Comunes
                    df['Importe_Num'] = pd.to_numeric(df['Importe_Solicitado'], errors='coerce') / 100.0
                    df['Cantidad_Num'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
                    df['Cod_Int'] = pd.to_numeric(df['Cod_Practica'], errors='coerce').fillna(0).astype(int).astype(str)

                    # ---------------------------------------------------------
                    # 1. CONTROL SSSALUD
                    # ---------------------------------------------------------
                    if modo in ["Control SSSalud (Lógica Médica)", "PROCESO COMPLETO (Todo lo anterior)"]:
                        log_msg("
>>> [1/3] Ejecutando Control SSSalud...")
                        
                        # Padrón Certificados
                        if file_cert is not None:
                            try:
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

                        if files_devok:
                            log_msg(f"Procesando {len(files_devok)} archivos históricos DEVOK...")
                            todos = [f"{x:03d}" for x in range(1, 100)]
                            cod_transp_ok = set([c for c in todos if c not in ['086', '095', '096']])
                            cod_apoyo_ok = set([f"{x:03d}" for x in range(1, 90) if x != 86] + ['097'])

                            for f in files_devok:
                                try:
                                    df_h = pd.read_csv(f, sep='|', header=None, dtype=str, encoding='latin1', usecols=[2, 5, 6, 7, 11, 12, 15])
                                    cuit = df_h[6].str.strip()
                                    tipo = pd.to_numeric(df_h[7], errors='coerce').fillna(0).astype(int).astype(str)
                                    pto = pd.to_numeric(df_h[11], errors='coerce').fillna(0).astype(int).astype(str)
                                    num = pd.to_numeric(df_h[12], errors='coerce').fillna(0).astype(int).astype(str)
                                    set_duplicados.update((cuit+"_"+tipo+"_"+pto+"_"+num).dropna().unique())

                                    df_h['Cod'] = df_h[15].str.strip().apply(lambda x: x.zfill(3) if pd.notnull(x) else '000')
                                    df_h['Key'] = df_h[2].str.strip() + "_" + df_h[5].str.strip()
                                    
                                    set_hist_transporte.update(df_h.loc[df_h['Cod'].isin(cod_transp_ok), 'Key'].unique())
                                    set_hist_apoyo.update(df_h.loc[df_h['Cod'].isin(cod_apoyo_ok), 'Key'].unique())
                                except: pass

                        df['Codigo_Rechazo'] = ''
                        cuit_a = df['CUIT_Prestador'].str.strip()
                        tipo_a = pd.to_numeric(df['Tipo_Comp'], errors='coerce').fillna(0).astype(int).astype(str)
                        pto_a = pd.to_numeric(df['Pto_Venta'], errors='coerce').fillna(0).astype(int).astype(str)
                        num_a = pd.to_numeric(df['Num_Comp'], errors='coerce').fillna(0).astype(int).astype(str)
                        mask = (cuit_a+"_"+tipo_a+"_"+pto_a+"_"+num_a).isin(set_duplicados)
                        df.loc[mask, 'Codigo_Rechazo'] += '-411'

                        cod = pd.to_numeric(df['Cod_Practica'], errors='coerce').fillna(0).astype(int)
                        cant = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0).astype(int)
                        df.loc[(cod < 90) & (cant != 1), 'Codigo_Rechazo'] += '-404'
                        df.loc[cod.isin([90, 91]) & (cant != 4), 'Codigo_Rechazo'] += '-404'
                        df.loc[(cod == 96) & ((cant <= 1) | (cant == 4)), 'Codigo_Rechazo'] += '-404'
                        df.loc[(df['Dependencia'] == 'S') & (~df['Cod_Practica'].isin(CODIGOS_CON_DEPENDENCIA)), 'Codigo_Rechazo'] += '-405'

                        if 'Edad' in df.columns:
                            df.loc[(df['Cod_Practica']=='096') & (df['Dependencia']=='S') & (df['Edad']>0) & (df['Edad']<6), 'Codigo_Rechazo'] += '-425'
                            df.loc[(df['Cod_Practica']=='085') & (df['Edad']>0) & ((df['Edad']<1)|(df['Edad']>6)), 'Codigo_Rechazo'] += '-427'

                        grupos = df.groupby(['CUIL', 'Periodo_Prestacion'])
                        principales_408_local = set([f"{x:03d}" for x in range(1, 90) if x != 86] + ['097'])
                        principales_transp_local = set([c for c in todos if c not in ['086', '095', '096']])
                        rango_1_84 = [f"{x:03d}" for x in range(1, 85)]

                        for (cuil, periodo), grupo in grupos:
                            practicas = set(grupo['Cod_Practica'].unique())
                            def add_err(idx, code): df.loc[idx, 'Codigo_Rechazo'] += code

                            if '089' in practicas and '087' in practicas: add_err(grupo[grupo['Cod_Practica'].isin(['089', '087'])].index, '-421')
                            if '090' in practicas and '091' in practicas: add_err(grupo[grupo['Cod_Practica'] == '091'].index, '-429')
                            if '085' in practicas:
                                prohibidos = [f"{x:03d}" for x in list(range(1, 7)) + list(range(13, 25)) + list(range(37, 85)) + [86] + list(range(92, 95))]
                                conf = practicas.intersection(set(prohibidos))
                                if conf: add_err(grupo[grupo['Cod_Practica'].isin(['085'] + list(conf))].index, '-426')
                            if '089' in practicas:
                                esc = [f"{x:03d}" for x in range(25, 37)]
                                if practicas.intersection(set(esc)): add_err(grupo[grupo['Cod_Practica'].isin(esc)].index, '-406')
                            if '086' in practicas and ('090' in practicas or '091' in practicas): add_err(grupo[grupo['Cod_Practica'] == '086'].index, '-407')
                            
                            if '086' in practicas:
                                tiene_local = not practicas.isdisjoint(principales_408_local)
                                tiene_hist = (cuil+"_"+periodo) in set_hist_apoyo
                                if not tiene_local and not tiene_hist: add_err(grupo[grupo['Cod_Practica'] == '086'].index, '-408')
                            
                            if '096' in practicas:
                                tiene_local = not practicas.isdisjoint(principales_transp_local)
                                tiene_hist = (cuil+"_"+periodo) in set_hist_transporte
                                if not tiene_local and not tiene_hist: add_err(grupo[grupo['Cod_Practica'] == '096'].index, '-415')

                            en_rango = practicas.intersection(set(rango_1_84))
                            if len(en_rango) > 1: add_err(grupo[grupo['Cod_Practica'].isin(en_rango)].index, '-420')
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
                            name_ok = f"{RNOS_FIJO}-{periodo_pres}_DS.DEVOK"
                            buf_ok = io.StringIO()
                            df_ok[COLUMNAS].to_csv(buf_ok, sep='|', index=False, header=False, encoding='latin1')
                            output_files[name_ok] = buf_ok.getvalue()
                            log_msg(f"   -> Generado OK: {name_ok}")

                        df_err = df[df['Codigo_Rechazo'] != ''].copy()
                        if not df_err.empty:
                            name_err = f"{RNOS_FIJO}-{periodo_pres}_DS.DEVERR"
                            buf_err = io.StringIO()
                            df_err[COLUMNAS + ['Codigo_Rechazo']].to_csv(buf_err, sep='|', index=False, header=False, encoding='latin1')
                            output_files[name_err] = buf_err.getvalue()
                            log_msg(f"   -> Generado ERR: {name_err}")

                    # ---------------------------------------------------------
                    # 2. CONTROL AFIP
                    # ---------------------------------------------------------
                    if modo in ["Control AFIP (Cruce c/Libros IVA)", "PROCESO COMPLETO (Todo lo anterior)"]:
                        log_msg("
>>> [2/3] Ejecutando Control AFIP...")
                        MAPEO_FACTURAS = {'1': '1', '2': '4', '3': '6', '5': '11', '6': '15', '7': '51', '8': '54'}
                        
                        if files_iva:
                            dfs_iva = []
                            for f in files_iva:
                                try:
                                    if f.name.endswith('.xlsx'):
                                        d = pd.read_excel(f, dtype=str, engine='openpyxl')
                                        if 'Nro. Doc. Vendedor' not in d.columns:
                                            d = pd.read_excel(f, header=1, dtype=str, engine='openpyxl')
                                    else:
                                        d = pd.read_csv(f, dtype=str, encoding='latin1', sep=None, engine='python')
                                        if 'Nro. Doc. Vendedor' not in d.columns:
                                            d = pd.read_csv(f, header=1, dtype=str, encoding='latin1', sep=None, engine='python')
                                    d.columns = d.columns.str.strip()
                                    dfs_iva.append(d)
                                except Exception as e:
                                    log_msg(f"⚠️ Error leyendo libro IVA {f.name}: {e}")
                            
                            if dfs_iva:
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
                                    name_err = f"{RNOS_FIJO}-{periodo_pres}_DS_WS.DEVERR"
                                    buf_aerr = io.StringIO()
                                    df_afip_err[COLUMNAS + ['Error_AFIP']].to_csv(buf_aerr, sep='|', index=False, header=False, encoding='latin1')
                                    output_files[name_err] = buf_aerr.getvalue()
                                    log_msg(f"   -> Generado AFIP ERR: {name_err}")

                                df_afip_ok = df_merged[df_merged['Error_AFIP'] == ''].copy()
                                if not df_afip_ok.empty:
                                    name_ok = f"{RNOS_FIJO}-{periodo_pres}_DS_WS.DEVOK_AFIP"
                                    buf_aok = io.StringIO()
                                    df_afip_ok[COLUMNAS].to_csv(buf_aok, sep='|', index=False, header=False, encoding='latin1')
                                    output_files[name_ok] = buf_aok.getvalue()
                                    log_msg(f"   -> Generado AFIP OK: {name_ok}")
                        else:
                            log_msg("⚠️ No se cargaron libros IVA. Se omite control AFIP.")

                    # ---------------------------------------------------------
                    # 3. CÁLCULO SUBSIDIOS
                    # ---------------------------------------------------------
                    if modo in ["Cálculo Subsidios (Económico)", "PROCESO COMPLETO (Todo lo anterior)"]:
                        log_msg("
>>> [3/3] Ejecutando Cálculo de Subsidios...")
                        if file_val is not None:
                            try:
                                df_val = pd.read_excel(file_val, dtype=str, engine='openpyxl')
                                df_val.columns = df_val.columns.astype(str).str.strip()
                                df_val['Cod_Int'] = pd.to_numeric(df_val['CODIGO'], errors='coerce').fillna(0).astype(int).astype(str)
                                df_val.set_index('Cod_Int', inplace=True)

                                agg_funcs = {'Cod_OS': 'first', 'Importe_Num': 'sum', 'Cantidad_Num': 'sum', 
                                             'Dependencia': lambda x: 'S' if 'S' in x.values else 'N', 'CUIT_Prestador': 'first'}
                                df_grouped = df.groupby(['CUIL', 'Periodo_Prestacion', 'Cod_Int']).agg(agg_funcs).reset_index()

                                def get_valor_tabla(cod_busqueda, periodo):
                                    if cod_busqueda in df_val.index and periodo in df_val.columns:
                                        try: return float(str(df_val.loc[cod_busqueda, periodo]).replace(',', '.'))
                                        except: return 0.0
                                    return 0.0

                                def calcular_grupo(row):
                                    cod = str(row['Cod_Int'])
                                    periodo = str(row['Periodo_Prestacion']).strip()
                                    solicitado = row['Importe_Num']
                                    cantidad = row['Cantidad_Num']
                                    dep = row['Dependencia']
                                    
                                    cod_lookup = '90' if cod == '86' else cod
                                    val_tabla = get_valor_tabla(cod_lookup, periodo)
                                    
                                    tope_base = val_tabla * 4 if cod in ['90','91','86'] else (min(cantidad, 2500)*val_tabla if cod=='96' else val_tabla)
                                    tope_final = tope_base * 1.35 if dep == 'S' else tope_base
                                    return min(solicitado, max(0.0, tope_final))

                                df_grouped['Monto_Subsidiable'] = df_grouped.apply(calcular_grupo, axis=1)

                                df_grouped['Str_Imp_Sol'] = df_grouped['Importe_Num'].apply(lambda x: "{:.2f}".format(x))
                                df_grouped['Str_Imp_Sub'] = df_grouped['Monto_Subsidiable'].apply(lambda x: "{:.2f}".format(x))
                                df_grouped['Linea'] = (CUIT_OS_PROPIO + "|" + periodo_pres + "|" + df_grouped['Cod_OS'] + "|" +
                                                       df_grouped['CUIL'] + "|" + df_grouped['Periodo_Prestacion'] + "|" +
                                                       df_grouped['Str_Imp_Sol'] + "|" + df_grouped['Cod_Int'] + "|" + df_grouped['Str_Imp_Sub'])
                                
                                name_sub = f"{RNOS_FIJO}-{periodo_pres}_DS.SUBSIDIO"
                                buf_sub = io.StringIO()
                                df_grouped['Linea'].to_csv(buf_sub, index=False, header=False, quoting=3, escapechar=None)
                                output_files[name_sub] = buf_sub.getvalue()
                                log_msg(f"   -> Subsidio generado: {name_sub}")

                                # Padron Afiliados merge
                                if file_afil is not None:
                                    try:
                                        df_afi = pd.read_excel(file_afil, dtype=str, engine='openpyxl')
                                        if 'Cuil' in df_afi.columns:
                                            df_afi['Cuil'] = pd.to_numeric(df_afi['Cuil'], errors='coerce').fillna(0).astype(np.int64).astype(str)
                                            df_afi = df_afi.drop_duplicates(subset=['Cuil'])
                                            df_grouped = df_grouped.merge(df_afi[['Cuil', 'Nombre', 'Convenio']], left_on='CUIL', right_on='Cuil', how='left')
                                            df = df.merge(df_afi[['Cuil', 'Convenio']], left_on='CUIL', right_on='Cuil', how='left')
                                    except: pass
                                
                                if 'Convenio' not in df_grouped.columns: df_grouped['Convenio'] = 'SIN CONVENIO'
                                if 'Convenio' not in df.columns: df['Convenio'] = 'SIN CONVENIO'
                                df_grouped.fillna({'Convenio': 'SIN CONVENIO'}, inplace=True)

                                df_grouped['Diferencia'] = df_grouped['Importe_Num'] - df_grouped['Monto_Subsidiable']
                                rep_cols = ['CUIL', 'Nombre', 'Convenio', 'Periodo_Prestacion', 'Cod_Int', 'Importe_Num', 'Monto_Subsidiable', 'Diferencia']
                                df_rep = df_grouped[rep_cols].copy()
                                df_rep.columns = ['CUIL', 'Nombre', 'Convenio', 'Periodo', 'Codigo', 'Importe Solicitado', 'Importe Subsidiado', 'Diferencia']
                                
                                name_rep = f"{RNOS_FIJO}-{periodo_pres}_Control_Diferencias.csv"
                                buf_rep = io.StringIO()
                                df_rep.to_csv(buf_rep, index=False, sep=';', float_format='%.2f', encoding='utf-8-sig')
                                output_files[name_rep] = buf_rep.getvalue()
                                log_msg(f"   -> Reporte Detallado: {name_rep}")

                            except Exception as e:
                                log_msg(f"⚠️ Error procesando subsidios/valores: {e}")
                        else:
                            log_msg("⚠️ Falta cargar la base de valores nomenclador para el cálculo de subsidios.")

                    st.success("🎉 ¡Proceso finalizado con éxito!")
                    
                    # Mostrar Logs
                    st.subheader("📋 Registro de Ejecución (Logs)")
                    st.text_area("Detalles del proceso:", "\n".join(logs), height=250)

                    # Botones de Descarga en ZIP
                    if output_files:
                        st.subheader("📥 Archivos Generados para Descarga")
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                            for fname, content in output_files.items():
                                zip_file.writestr(fname, content)
                        
                        st.download_button(
                            label="📦 Descargar Todos los Archivos (.zip)",
                            data=zip_buffer.getvalue(),
                            file_name=f"Resultados_Auditoria_{periodo_pres}.zip",
                            mime="application/zip"
                        )

                except Exception as e:
                    st.error(f"❌ Error crítico en el proceso: {e}")