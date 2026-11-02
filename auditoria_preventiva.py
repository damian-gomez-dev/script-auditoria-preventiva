import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import pandas as pd
import numpy as np
import os
import glob
import threading
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================

RNOS_FIJO = "107909"
CUIT_OS_PROPIO = "41763271426" 

# Carpeta Raíz
BASE_DIR = r"C:\Users\Damian Gomez\Desktop\Programacion\Control integracion"

# Carpetas de ENTRADA
DIR_DATABASES = os.path.join(BASE_DIR, "Bases de datos")
DIR_HISTORICOS_DEVOK = os.path.join(DIR_DATABASES, "DEVOK Historicos")
DIR_HISTORICOS_SUBSIDIOS = os.path.join(DIR_DATABASES, "SUBSIDIOS Historicos")
DIR_LIBROS_IVA = os.path.join(DIR_DATABASES, "Libros IVA")

FILE_PADRON_CERTIFICADOS = os.path.join(DIR_DATABASES, "Base Listado certificados disca.xlsx") 
FILE_PADRON_AFILIADOS = os.path.join(DIR_DATABASES, "Base Padron de afiliados.xlsx")
FILE_VALORES = os.path.join(DIR_DATABASES, "Base Valores Integracion.xlsx")

# Carpetas de SALIDA
DIR_OUT_ERRORES = os.path.join(BASE_DIR, "Control Errores")
DIR_OUT_AFIP = os.path.join(BASE_DIR, "Control AFIP")
DIR_OUT_SUBSIDIOS = os.path.join(BASE_DIR, "Control Subsidios")

# =============================================================================
# ESTRUCTURA TXT
# =============================================================================
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

class IntegracionApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Sistema Integración SSSalud - RNOS: {RNOS_FIJO} - v30.0")
        self.root.geometry("950x800")
        
        self.path_txt = tk.StringVar()
        self.modo_var = tk.StringVar(value="ambos")
        
        periodo_defecto = self.calcular_periodo_anterior()
        self.periodo_pres_var = tk.StringVar(value=periodo_defecto)

        self.crear_carpetas_salida()
        self.crear_interfaz()
        self.verificar_entorno()

    def calcular_periodo_anterior(self):
        hoy = datetime.now()
        mes = hoy.month - 1
        year = hoy.year
        if mes == 0:
            mes = 12
            year -= 1
        return f"{year}{mes:02d}"

    def crear_carpetas_salida(self):
        try:
            os.makedirs(DIR_OUT_ERRORES, exist_ok=True)
            os.makedirs(DIR_OUT_SUBSIDIOS, exist_ok=True)
            os.makedirs(DIR_OUT_AFIP, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudieron crear carpetas:\n{e}")

    def verificar_entorno(self):
        missing = []
        if not os.path.exists(DIR_HISTORICOS_DEVOK): missing.append("Carpeta Históricos DEVOK")
        if not os.path.exists(DIR_LIBROS_IVA): missing.append("Carpeta Libros IVA")
        
        if not os.path.exists(FILE_PADRON_CERTIFICADOS): 
            possible = glob.glob(os.path.join(DIR_DATABASES, "*ertificados*.xlsx"))
            if not possible: missing.append("Base Certificados (Edad)")
        if not os.path.exists(FILE_PADRON_AFILIADOS):
             possible = glob.glob(os.path.join(DIR_DATABASES, "*afiliados*.xlsx"))
             if not possible: missing.append("Base Afiliados (Nombre/Convenio)")
        if not os.path.exists(FILE_VALORES): missing.append("Base Valores")
        
        if missing:
            msg = "FALTAN BASES DE DATOS:\n" + "\n".join(missing)
            self.log_area.insert(tk.END, "⚠️ ALERTA: Revise las bases de datos.\n")
            messagebox.showwarning("Entorno Incompleto", msg)
        else:
            self.log_area.insert(tk.END, "✅ Entorno verificado correctamente.\n")

    def crear_interfaz(self):
        frame_file = tk.LabelFrame(self.root, text="Configuración de Entrada", padx=10, pady=10)
        frame_file.pack(fill="x", padx=10, pady=5)
        
        tk.Label(frame_file, text="Seleccionar TXT (_ds.txt):").grid(row=0, column=0, sticky="w")
        sub_frame = tk.Frame(frame_file)
        sub_frame.grid(row=1, column=0, columnspan=3, sticky="we", pady=(0, 10))
        tk.Entry(sub_frame, textvariable=self.path_txt, width=70).pack(side="left", padx=5)
        tk.Button(sub_frame, text="Examinar...", command=self.buscar_txt).pack(side="left")

        tk.Label(frame_file, text="Periodo de Presentación (YYYYMM):").grid(row=2, column=0, sticky="w")
        tk.Entry(frame_file, textvariable=self.periodo_pres_var, width=20, font=("Arial", 10, "bold")).grid(row=2, column=1, sticky="w", padx=5)
        tk.Label(frame_file, text="(Determina el nombre de los archivos de salida)").grid(row=2, column=2, sticky="w")

        frame_mode = tk.LabelFrame(self.root, text="Opciones de Proceso", padx=10, pady=10)
        frame_mode.pack(fill="x", padx=10, pady=5)
        
        tk.Radiobutton(frame_mode, text="Control SSSalud (Lógica Médica)", variable=self.modo_var, value="errores").pack(anchor="w")
        tk.Radiobutton(frame_mode, text="Control AFIP (Cruce c/Libros IVA)", variable=self.modo_var, value="afip").pack(anchor="w")
        tk.Radiobutton(frame_mode, text="Cálculo Subsidios (Económico)", variable=self.modo_var, value="subsidios").pack(anchor="w")
        tk.Radiobutton(frame_mode, text="PROCESO COMPLETO (Todo lo anterior)", variable=self.modo_var, value="todo").pack(anchor="w")

        tk.Button(self.root, text="INICIAR PROCESO", bg="#0066cc", fg="white", font=("Arial", 12, "bold"), command=self.iniciar_hilo).pack(fill="x", padx=20, pady=10)

        self.log_area = scrolledtext.ScrolledText(self.root, width=100, height=22)
        self.log_area.pack(padx=10, pady=5)

    def buscar_txt(self):
        f = filedialog.askopenfilename(filetypes=[("Archivos TXT", "*.txt")])
        if f: self.path_txt.set(f)

    def log(self, msg):
        self.log_area.insert(tk.END, msg + "\n")
        self.log_area.see(tk.END)

    def iniciar_hilo(self):
        t = threading.Thread(target=self.ejecutar_proceso)
        t.start()

    # =========================================================================
    # LÓGICA PRINCIPAL
    # =========================================================================
    def ejecutar_proceso(self):
        txt_path = self.path_txt.get()
        periodo_presentacion = self.periodo_pres_var.get().strip()

        if not txt_path or not os.path.exists(txt_path):
            self.log("ERROR: Seleccione un archivo TXT válido.")
            return
        
        if len(periodo_presentacion) != 6 or not periodo_presentacion.isdigit():
            self.log("ERROR: El periodo de presentación debe tener 6 dígitos (YYYYMM).")
            return

        modo = self.modo_var.get()
        self.log("="*60)
        self.log(f"Procesando: {os.path.basename(txt_path)}")
        self.log(f"Periodo: {periodo_presentacion} | Modo: {modo.upper()}")
        self.log("="*60)

        try:
            # Cargar TXT
            df = pd.read_csv(txt_path, sep='|', names=COLUMNAS, dtype=str, encoding='latin1', header=None)
            self.log(f"Registros cargados: {len(df)}")
            
            # Conversiones Comunes
            df['Importe_Num'] = pd.to_numeric(df['Importe_Solicitado'], errors='coerce') / 100.0
            df['Cantidad_Num'] = pd.to_numeric(df['Cantidad'], errors='coerce').fillna(0)
            df['Cod_Int'] = pd.to_numeric(df['Cod_Practica'], errors='coerce').fillna(0).astype(int).astype(str)

            # --- EJECUCIÓN MODULAR ---
            
            if modo in ["errores", "todo"]:
                self.control_errores_sssalud(df.copy(), periodo_presentacion)

            if modo in ["afip", "todo"]:
                self.control_errores_afip(df.copy(), periodo_presentacion)

            if modo in ["subsidios", "todo"]:
                self.control_subsidios(df.copy(), periodo_presentacion)

            self.log("\n--- FIN DEL PROCESO ---")
            messagebox.showinfo("Listo", "Proceso finalizado correctamente.")

        except Exception as e:
            self.log(f"ERROR CRÍTICO: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", str(e))

    # =========================================================================
    # 1. CONTROL SSSALUD (Lógica Médica)
    # =========================================================================
    def control_errores_sssalud(self, df, periodo_presentacion):
        self.log("\n>>> [1/3] CONTROL SSSALUD (Validaciones Médicas)")
        
        # Carga Padrón
        if os.path.exists(FILE_PADRON_CERTIFICADOS):
            try:
                df_pad = pd.read_excel(FILE_PADRON_CERTIFICADOS, header=4, dtype=str, engine='openpyxl')
                df_pad['Cuil'] = df_pad['Cuil'].str.replace('-', '', regex=False).str.strip()
                df_pad['Edad'] = pd.to_numeric(df_pad['Edad'], errors='coerce').fillna(0).astype(int)
                df = df.merge(df_pad[['Cuil', 'Edad']], left_on='CUIL', right_on='Cuil', how='left')
            except: pass
        
        # Carga Históricos DEVOK (Ahora carga todo lo necesario para los SETS)
        set_duplicados = set()
        set_hist_transporte = set()
        set_hist_apoyo = set()

        if os.path.exists(DIR_HISTORICOS_DEVOK):
            self.log("Analizando históricos DEVOK...")
            archivos = glob.glob(os.path.join(DIR_HISTORICOS_DEVOK, "*"))
            
            # Rangos de códigos válidos para históricos
            todos = [f"{x:03d}" for x in range(1, 100)]
            cod_transp_ok = set([c for c in todos if c not in ['086', '095', '096']])
            cod_apoyo_ok = set([f"{x:03d}" for x in range(1, 90) if x != 86] + ['097'])

            for f in archivos:
                try:
                    # Leemos columnas: 2(RNOS), 5(Periodo), 6(CUIT), 7(Tipo), 11(Pto), 12(Num), 15(Codigo)
                    df_h = pd.read_csv(f, sep='|', header=None, dtype=str, encoding='latin1', usecols=[2, 5, 6, 7, 11, 12, 15])
                    
                    # Para Duplicados
                    cuit = df_h[6].str.strip()
                    tipo = pd.to_numeric(df_h[7], errors='coerce').fillna(0).astype(int).astype(str)
                    pto = pd.to_numeric(df_h[11], errors='coerce').fillna(0).astype(int).astype(str)
                    num = pd.to_numeric(df_h[12], errors='coerce').fillna(0).astype(int).astype(str)
                    set_duplicados.update((cuit+"_"+tipo+"_"+pto+"_"+num).dropna().unique())

                    # Para Reglas 408 y 415
                    df_h['Cod'] = df_h[15].str.strip().apply(lambda x: x.zfill(3) if pd.notnull(x) else '000')
                    df_h['Key'] = df_h[2].str.strip() + "_" + df_h[5].str.strip() # CUIL_PERIODO (Nota: col 2 es CUIL en historico DEVOK?)
                    # Corrección: En DEVOK SSSalud:
                    # Col 2 = CUIL Afiliado
                    # Col 5 = Periodo Prestacion
                    
                    set_hist_transporte.update(df_h.loc[df_h['Cod'].isin(cod_transp_ok), 'Key'].unique())
                    set_hist_apoyo.update(df_h.loc[df_h['Cod'].isin(cod_apoyo_ok), 'Key'].unique())
                except: pass

        df['Codigo_Rechazo'] = ''

        # Validaciones
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

        # Grupos
        grupos = df.groupby(['CUIL', 'Periodo_Prestacion'])
        
        principales_408_local = set([f"{x:03d}" for x in range(1, 90) if x != 86] + ['097'])
        todos = [f"{x:03d}" for x in range(1, 100)]
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
            
            # CORRECCIÓN V30: Ahora set_hist_apoyo y set_hist_transporte están definidos
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
        
        # Exportar
        df_ok = df[df['Codigo_Rechazo'] == ''].copy()
        if not df_ok.empty:
            name = f"{RNOS_FIJO}-{periodo_presentacion}_DS.DEVOK"
            df_ok[COLUMNAS].to_csv(os.path.join(DIR_OUT_ERRORES, name), sep='|', index=False, header=False, encoding='latin1')
            self.log(f"-> Generado OK: {name}")

        df_err = df[df['Codigo_Rechazo'] != ''].copy()
        if not df_err.empty:
            name = f"{RNOS_FIJO}-{periodo_presentacion}_DS.DEVERR"
            df_err[COLUMNAS + ['Codigo_Rechazo']].to_csv(os.path.join(DIR_OUT_ERRORES, name), sep='|', index=False, header=False, encoding='latin1')
            self.log(f"-> Generado ERR: {name}")

    # =========================================================================
    # 2. CONTROL AFIP (Cruce con Libros IVA - Coincidencia Exacta)
    # =========================================================================
    def control_errores_afip(self, df, periodo_presentacion):
        from decimal import Decimal
        import re
        
        self.log("\n>>> [2/3] CONTROL AFIP (Cruce Fiscal Libros IVA)")
        
        MAPEO_FACTURAS = {
            '1': '1',   # Factura A
            '2': '4',   # Recibo A
            '3': '6',   # Factura B o Recibo B
            '5': '11',  # Factura C
            '6': '15',  # Recibo C
            '7': '51',  # Factura M
            '8': '54'   # Recibo M
        }
        
        if not os.path.exists(DIR_LIBROS_IVA):
            self.log("ERROR: No existe carpeta 'Libros IVA'. Saltando control.")
            return

        self.log("Cargando Libros IVA...")
        files_iva = glob.glob(os.path.join(DIR_LIBROS_IVA, "*.xlsx")) + \
                    glob.glob(os.path.join(DIR_LIBROS_IVA, "*.csv"))
        
        if not files_iva:
            self.log("ERROR: No hay archivos de Libros IVA.")
            return

        dfs_iva = []
        for f in files_iva:
            try:
                if f.endswith('.xlsx'):
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
                self.log(f"Error leyendo {os.path.basename(f)}: {e}")
        
        if not dfs_iva: return
        df_iva_raw = pd.concat(dfs_iva, ignore_index=True)

        # --- NORMALIZACIÓN IVA ---
        df_iva = pd.DataFrame()
        df_iva['IVA_CUIT'] = df_iva_raw['Nro. Doc. Vendedor'].astype(str).str.replace(r'\D', '', regex=True)
        df_iva['IVA_TIPO'] = df_iva_raw['Tipo'].apply(lambda x: str(x).split('-')[0].strip().lstrip('0'))
        df_iva['IVA_PTO'] = df_iva_raw['Punto de Venta'].apply(lambda x: str(int(float(x))))
        df_iva['IVA_NUM'] = df_iva_raw['Número Desde'].apply(lambda x: str(int(float(x))))
        df_iva['IVA_FECHA_ISO'] = pd.to_datetime(df_iva_raw['Fecha'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_iva['IVA_TOTAL_DEC'] = df_iva_raw['Total'].apply(lambda x: Decimal(str(x).replace(',', '.')))
        df_iva['KEY_AFIP'] = df_iva['IVA_CUIT'] + "_" + df_iva['IVA_TIPO'] + "_" + df_iva['IVA_PTO'] + "_" + df_iva['IVA_NUM']
        df_iva = df_iva.drop_duplicates(subset=['KEY_AFIP'])

        # --- NORMALIZACIÓN TXT ---
        df_proc = df.copy()
        df_proc['TXT_CUIT'] = df_proc['CUIT_Prestador'].astype(str).str.strip()
        df_proc['TIPO_SSS_INT'] = df_proc['Tipo_Comp'].apply(lambda x: str(int(x)))
        df_proc['TXT_TIPO_AFIP'] = df_proc['TIPO_SSS_INT'].map(MAPEO_FACTURAS).fillna('999')
        df_proc['TXT_PTO'] = df_proc['Pto_Venta'].apply(lambda x: str(int(x)))
        df_proc['TXT_NUM'] = df_proc['Num_Comp'].apply(lambda x: str(int(x)))
        df_proc['TXT_FECHA_ISO'] = pd.to_datetime(df_proc['Fecha_Emision'], dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d')
        df_proc['TXT_TOTAL_DEC'] = df_proc['Importe_Comp'].apply(lambda x: Decimal(x) / Decimal(100))
        df_proc['KEY_AFIP'] = df_proc['TXT_CUIT'] + "_" + df_proc['TXT_TIPO_AFIP'] + "_" + df_proc['TXT_PTO'] + "_" + df_proc['TXT_NUM']

        # --- CRUCE ---
        df_merged = df_proc.merge(df_iva[['KEY_AFIP', 'IVA_FECHA_ISO', 'IVA_TOTAL_DEC']], on='KEY_AFIP', how='left')
        df_merged['Error_AFIP'] = ''

        mask_not_found = df_merged['IVA_TOTAL_DEC'].isna()
        df_merged.loc[mask_not_found, 'Error_AFIP'] += '100-'
        mask_found = ~mask_not_found
        df_merged.loc[mask_found & (df_merged['TXT_TOTAL_DEC'] != df_merged['IVA_TOTAL_DEC']), 'Error_AFIP'] += '110-'
        df_merged.loc[mask_found & (df_merged['TXT_FECHA_ISO'] != df_merged['IVA_FECHA_ISO']), 'Error_AFIP'] += '101-'

        # --- EXPORTACIÓN ---
        # 1. Exportar Errores (.DEVERR)
        df_afip_err = df_merged[df_merged['Error_AFIP'] != ''].copy()
        if not df_afip_err.empty:
            name_err = f"{RNOS_FIJO}-{periodo_presentacion}_DS_WS.DEVERR"
            df_afip_err[COLUMNAS + ['Error_AFIP']].to_csv(os.path.join(DIR_OUT_AFIP, name_err), sep='|', index=False, header=False, encoding='latin1')
            self.log(f"-> Generado AFIP ERR: {name_err} ({len(df_afip_err)} facturas)")

        # 2. Exportar Aceptados (.DEVOK_AFIP)
        df_afip_ok = df_merged[df_merged['Error_AFIP'] == ''].copy()
        if not df_afip_ok.empty:
            name_ok = f"{RNOS_FIJO}-{periodo_presentacion}_DS_WS.DEVOK_AFIP"
            df_afip_ok[COLUMNAS].to_csv(os.path.join(DIR_OUT_AFIP, name_ok), sep='|', index=False, header=False, encoding='latin1')
            self.log(f"-> Generado AFIP OK: {name_ok} ({len(df_afip_ok)} facturas)")
        else:
            self.log("⚠️ ATENCIÓN: No hay facturas aceptadas en este lote.")

    # =========================================================================
    # 3. CÁLCULO SUBSIDIOS
    # =========================================================================
    def control_subsidios(self, df, periodo_presentacion):
        self.log("\n>>> [3/3] CÁLCULO DE SUBSIDIOS")
        
        if not os.path.exists(FILE_VALORES): return

        # Carga Historial
        historial = {}
        if os.path.exists(DIR_HISTORICOS_SUBSIDIOS):
            archivos = glob.glob(os.path.join(DIR_HISTORICOS_SUBSIDIOS, "*"))
            for f in archivos:
                try:
                    df_h = pd.read_csv(f, sep='|', header=None, dtype=str, encoding='latin1', usecols=[3, 4, 6, 7])
                    df_h[3] = df_h[3].str.strip()
                    df_h[4] = df_h[4].str.strip()
                    df_h[6] = pd.to_numeric(df_h[6], errors='coerce').fillna(0).astype(int).astype(str)
                    df_h[7] = pd.to_numeric(df_h[7], errors='coerce').fillna(0.0)
                    grupo = df_h.groupby([3, 4, 6])[7].sum().reset_index()
                    for _, row in grupo.iterrows():
                        key = (row[3], row[4], row[6])
                        historial[key] = historial.get(key, 0) + row[7]
                except: pass

        try:
            df_val = pd.read_excel(FILE_VALORES, dtype=str, engine='openpyxl')
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
                
                consumido = historial.get((str(row['CUIL']), periodo, cod), 0.0)
                return min(solicitado, max(0.0, tope_final - consumido))

            df_grouped['Monto_Subsidiable'] = df_grouped.apply(calcular_grupo, axis=1)

            # Exportación .SUBSIDIO
            df_grouped['Str_Imp_Sol'] = df_grouped['Importe_Num'].apply(lambda x: "{:.2f}".format(x))
            df_grouped['Str_Imp_Sub'] = df_grouped['Monto_Subsidiable'].apply(lambda x: "{:.2f}".format(x))
            df_grouped['Linea'] = (CUIT_OS_PROPIO + "|" + periodo_presentacion + "|" + df_grouped['Cod_OS'] + "|" +
                                   df_grouped['CUIL'] + "|" + df_grouped['Periodo_Prestacion'] + "|" +
                                   df_grouped['Str_Imp_Sol'] + "|" + df_grouped['Cod_Int'] + "|" + df_grouped['Str_Imp_Sub'])
            
            name_sub = f"{RNOS_FIJO}-{periodo_presentacion}_DS.SUBSIDIO"
            df_grouped['Linea'].to_csv(os.path.join(DIR_OUT_SUBSIDIOS, name_sub), index=False, header=False, quoting=3, escapechar=None)
            self.log(f"-> Archivo generado: {name_sub}")

            # Merge Afiliados
            if os.path.exists(FILE_PADRON_AFILIADOS):
                try:
                    df_afi = pd.read_excel(FILE_PADRON_AFILIADOS, dtype=str, engine='openpyxl')
                    if 'Cuil' in df_afi.columns:
                        df_afi['Cuil'] = pd.to_numeric(df_afi['Cuil'], errors='coerce').fillna(0).astype(np.int64).astype(str)
                        df_afi = df_afi.drop_duplicates(subset=['Cuil'])
                        df_grouped = df_grouped.merge(df_afi[['Cuil', 'Nombre', 'Convenio']], left_on='CUIL', right_on='Cuil', how='left')
                        df = df.merge(df_afi[['Cuil', 'Convenio']], left_on='CUIL', right_on='Cuil', how='left')
                except: pass
            
            if 'Convenio' not in df_grouped.columns: df_grouped['Convenio'] = 'SIN CONVENIO'
            if 'Convenio' not in df.columns: df['Convenio'] = 'SIN CONVENIO'
            df_grouped.fillna({'Convenio': 'SIN CONVENIO'}, inplace=True)
            df.fillna({'Convenio': 'SIN CONVENIO'}, inplace=True)

            # CSV Detalle
            df_grouped['Diferencia'] = df_grouped['Importe_Num'] - df_grouped['Monto_Subsidiable']
            rep_cols = ['CUIL', 'Nombre', 'Convenio', 'Periodo_Prestacion', 'Cod_Int', 'Importe_Num', 'Monto_Subsidiable', 'Diferencia']
            df_rep = df_grouped[rep_cols].copy()
            df_rep.columns = ['CUIL', 'Nombre', 'Convenio', 'Periodo', 'Codigo', 'Importe Solicitado', 'Importe Subsidiado', 'Diferencia']
            name_rep = f"{RNOS_FIJO}-{periodo_presentacion}_Control_Diferencias.csv"
            df_rep.to_csv(os.path.join(DIR_OUT_SUBSIDIOS, name_rep), index=False, sep=';', float_format='%.2f', encoding='utf-8-sig')
            self.log(f"-> Reporte Detallado: {name_rep}")

            # CSV Resumen
            resumen = df_grouped.groupby('Convenio').agg(
                Solicitado=('Importe_Num', 'sum'), Subsidiado=('Monto_Subsidiable', 'sum'), Afiliados=('CUIL', 'nunique')
            ).reset_index()
            facturas = df.groupby('Convenio').size().reset_index(name='Cantidad de facturas')
            resumen = resumen.merge(facturas, on='Convenio', how='left')
            resumen['Diferencia'] = resumen['Solicitado'] - resumen['Subsidiado']
            resumen['Porcentual'] = (resumen['Subsidiado'] / resumen['Solicitado']).fillna(0)
            resumen['Porcentaje(afiliados)'] = (resumen['Afiliados'] / df['CUIL'].nunique()).fillna(0)
            
            row_tot = pd.DataFrame([{
                'Convenio': 'TOTAL', 'Solicitado': resumen['Solicitado'].sum(), 'Subsidiado': resumen['Subsidiado'].sum(),
                'Diferencia': resumen['Diferencia'].sum(), 'Porcentual': (resumen['Subsidiado'].sum()/resumen['Solicitado'].sum() if resumen['Solicitado'].sum()>0 else 0),
                'Cantidad de facturas': resumen['Cantidad de facturas'].sum(), 'Afiliados': resumen['Afiliados'].sum(), 'Porcentaje(afiliados)': 1.0
            }])
            res_final = pd.concat([row_tot, resumen], ignore_index=True)
            res_final.rename(columns={'Afiliados': 'Cantidad(de afiliados)', 'Porcentaje(afiliados)': 'Porcentaje(de afiliados por convenio)'}, inplace=True)
            
            name_res = f"{RNOS_FIJO}-{periodo_presentacion}_Resumen_Convenios.csv"
            res_final.to_csv(os.path.join(DIR_OUT_SUBSIDIOS, name_res), index=False, sep=';', float_format='%.2f', encoding='utf-8-sig')
            self.log(f"-> Resumen Gerencial: {name_res}")

            self.log(f"\nTOTAL: Solicitado ${res_final.iloc[0]['Solicitado']:,.2f} | Subsidiado ${res_final.iloc[0]['Subsidiado']:,.2f}")

        except Exception as e:
            self.log(f"Error en subsidios: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    root = tk.Tk()
    app = IntegracionApp(root)
    root.mainloop()