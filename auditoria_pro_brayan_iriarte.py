import streamlit as st
import pandas as pd
import re, fitz, difflib, time, requests, os, shutil
from io import BytesIO
from PIL import Image
import pytesseract

# Para que funcione en tu PC y en la nube
if shutil.which("tesseract"):
    pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")
else:
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ===== TU LLAVE - SEGURO PARA GITHUB Y NUBE =====
# En tu PC usa la de abajo, en la nube usa Secrets
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except:
    GROQ_API_KEY = "gsk_PEGA_AQUI_TU_LLAVE_NUEVA"

MODELO = "openai/gpt-oss-120b"
AUTOR = "Brayan Melvin Iriarte Peralta"

st.set_page_config(page_title="AuditorIA Pro | Brayan Iriarte", page_icon="✔", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    .main-title {font-size:32px; font-weight:700; color:#0F2A44; letter-spacing:-0.5px; margin-bottom:2px;}
    .subtitle {font-size:14px; color:#5A6D80; margin-bottom:6px;}
    .author-line {font-size:12px; color:#94A3B8; margin-bottom:16px;}
    .author-line b {color:#0F2A44;}
    .badge {background:#EAF2F8; color:#0F2A44; padding:4px 10px; border-radius:20px; font-size:11px; font-weight:600; letter-spacing:0.5px;}
    .sidebar-welcome {background:#F1F5F9; padding:12px; border-radius:8px; font-size:12.5px; line-height:1.5; color:#334155; border-left:3px solid #0F2A44;}
    .section-label {font-size:11px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#64748B; margin-top:18px; margin-bottom:8px;}
    .kpi-card {background:white; border:1px solid #E2E8F0; border-radius:10px; padding:16px; text-align:center;}
    .kpi-num {font-size:28px; font-weight:800; color:#0F2A44;}
    .kpi-label {font-size:11px; color:#64748B; text-transform:uppercase; letter-spacing:0.8px;}
    .stButton>button {background:#0F2A44 !important; color:white !important; font-weight:600; border-radius:6px; height:44px;}
    .suggest-box {background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:12px 14px; font-size:13px; color:#334155; margin-bottom:12px;}
    .suggest-box b {color:#0F2A44;}
    @keyframes fadeUp { from {opacity:0; transform: translateY(12px);} to {opacity:1; transform: translateY(0);} }
    @keyframes popIn { 0% {transform:scale(0.95); opacity:0;} 100% {transform:scale(1); opacity:1;} }
    .kpi-card { animation: fadeUp 0.6s ease forwards; }
    div[data-testid="stVerticalBlockBorderWrapper"] { animation: popIn 0.5s ease; }
    .stButton>button { transition: all 0.2s ease !important; }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(15,42,68,0.25) !important; }
    div[data-testid="stDataFrame"] { animation: fadeUp 0.5s ease; }
    .badge { animation: fadeUp 0.8s ease; }
</style>
""", unsafe_allow_html=True)

if "df_pdfs" not in st.session_state: st.session_state.df_pdfs = None
if "df_libro" not in st.session_state: st.session_state.df_libro = None
if "df_consol" not in st.session_state: st.session_state.df_consol = None
if "ejecutado" not in st.session_state: st.session_state.ejecutado = False
if "chat" not in st.session_state: st.session_state.chat = []
if "show_anim" not in st.session_state: st.session_state.show_anim = False

with st.sidebar:
    st.markdown('<div style="font-size:22px; font-weight:800; color:#0F2A44;">AUDITORIA<span style="color:#2563EB;">PRO</span></div>', unsafe_allow_html=True)
    st.markdown('<span class="badge">PROTOTIPO v0.9 — VERSIÓN DE PRUEBA</span>', unsafe_allow_html=True)
    st.markdown("""<div class="sidebar-welcome" style="margin-top:12px;"><b>Bienvenido.</b><br>Este es un prototipo en fase de validación, diseñado para contribuir y mejorar los procedimientos de pruebas en auditoría mediante la contrastación directa con el documento fuente.</div>""", unsafe_allow_html=True)
    st.markdown('<div class="section-label">Pruebas disponibles — Verificadas</div>', unsafe_allow_html=True)
    p_recalculo = st.checkbox("Recálculo aritmético Base + IGV = Total", value=True)
    p_concilia = st.checkbox("Conciliación Base, IGV y Total", value=True)
    p_fechas = st.checkbox("Corte de fechas Emisión / Vencimiento", value=True)
    p_serie = st.checkbox("Serie y número de comprobante", value=True)
    materialidad = st.number_input("Materialidad S/", value=1.0, step=0.5)
    st.markdown('<div class="section-label">Próximamente</div>', unsafe_allow_html=True)
    for label in ["Validación RUC en SUNAT / Estado contribuyente","Detección de duplicados y comprobantes alterados","Análisis de integridad — Ley de Benford","Cruce con registro de compras y PDT 621"]:
        if st.checkbox(label, key=label):
            st.info("Próximamente disponible — En desarrollo.")
    st.markdown("---")
    st.success("Agente IA conectado — gpt-oss-120b")
    st.caption("Documento fuente prevalece sobre registro contable.")
    st.caption(f"Proyecto por {AUTOR}")

st.markdown('<div class="main-title">Validación Documental — Facturas vs. Registro Contable</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Contrastación automatizada del registro contable con el comprobante de pago electrónico. Identificación por Serie, RUC y Total.</div>', unsafe_allow_html=True)
st.markdown(f'<div class="author-line">Proyecto por <b>{AUTOR}</b> • AuditorIA Pro v0.9 • Lima, Perú</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1: pdfs = st.file_uploader("Documento fuente — Facturas PDF", type=["pdf"], accept_multiple_files=True, key="pdf_uploader")
with col2: libro = st.file_uploader("Registro contable — Excel", type=["xlsx","csv"], key="excel_uploader")

ejecutar = st.button("EJECUTAR VALIDACIÓN", type="primary", use_container_width=True)
if ejecutar:
    if not pdfs:
        st.warning("Cargue los documentos fuente para iniciar.")
    else:
        st.session_state.ejecutado=True
        st.session_state.df_pdfs=None; st.session_state.df_libro=None; st.session_state.df_consol=None
        st.session_state.show_anim=True

def extraer_pdf(file):
    text=""; doc=fitz.open(stream=file.read(), filetype="pdf")
    for p in doc: text+=p.get_text()+"\n"
    uso_ocr=False
    if len(text.strip())<50 or "RUC" not in text:
        uso_ocr=True; text=""
        for p in doc:
            pix=p.get_pixmap(dpi=300); img=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
            text+=pytesseract.image_to_string(img, lang='eng+spa')+"\n"
    m_ruc=re.search(r"(\d{11})", text); ruc_val=m_ruc.group(1) if m_ruc else "NO ENCONTRADO"
    fechas=re.findall(r"(\d{2}[-/]\d{2}[-/]\d{4})", text)
    montos=re.findall(r"([\d,]+\.\d{2})", text)
    total_val=float(max([float(m.replace(",","")) for m in montos])) if montos else 0
    base_val=round(total_val/1.18,2); igv_val=round(total_val-base_val,2)
    serie_num="NO ENCONTRADO"
    m=re.search(r"\b([EF]\d{3}-\d{3,})\b", text.upper())
    if m: serie_num=m.group(1)
    else:
        m_file=re.search(r"\b([EF]\d{3})-(\d{3,})\b", file.name.upper())
        if m_file: serie_num=f"{m_file.group(1)}-{m_file.group(2)}"
        else: serie_num="SIN SERIE EN NOMBRE"
    serie=serie_num.split("-")[0] if "-" in serie_num else ""
    numero=serie_num.split("-")[1] if "-" in serie_num else ""
    prov="CITITEX S.A.C." if ruc_val=="20522054331" else "TRANSPORTES Y NEGOCIOS ESCOBAR S.R.L." if "ESCOBAR" in text.upper() else "TRANSPORTES Y SERVICIOS CL E.I.R.L." if "20600095375" in text else file.name[:30]
    return {"Archivo":file.name,"Serie - N° Comprobante":serie_num,"Serie":serie,"N°":numero,"RUC":ruc_val,"Proveedor":prov,"F. Emis.":fechas[0] if fechas else "","F. Venc.":fechas[1] if len(fechas)>1 else fechas[0] if fechas else "","Base":base_val,"IGV":igv_val,"Total":total_val,"Método":"OCR" if uso_ocr else "Digital"}

def ia_mapear(df):
    cols=list(df.columns)
    conoc={"RUC":["RUC","N° RUC"],"PROVEEDOR":["PROVEEDOR","RAZON SOCIAL","NOMBRE","PROV"],"F_EMIS":["FEC EMIS","FECHA EMIS","EMISION","FEC. EMIS"],"F_VEN":["FECHA VEN","VENCIMIENTO","F VENC","FECHA. VEN"],"BASE":["B IMPO","BASE IMPONIBLE","BASE","SUBTOTAL","B. IMPO"],"IGV":["IGV","I.G.V"],"TOTAL":["FACTURA TOAL","FACTURA TO","TOTAL FACTURADO","TOTAL","IMPORTE TOTAL"],"DOC":["DOC","COMPROBANTE","FACTURA","SERIE"],"ITEM":["ITM","ITEM","N°"]}
    mapa={}
    for col in cols:
        cu=str(col).upper().replace("\n"," ").replace(".","").strip()
        best=None; bs=0
        for k,sins in conoc.items():
            for s in sins:
                sc=0.95 if s in cu else difflib.SequenceMatcher(None,cu,s).ratio()
                if sc>bs: bs=sc; best=k
        if bs>0.55: mapa[best]=col
    return mapa

def norm_fecha(v):
    try:
        d=pd.to_datetime(v, dayfirst=True, errors='coerce')
        if pd.notna(d): return d.strftime("%d-%m-%Y")
    except: pass
    return str(v).strip().split(" ")[0].replace("/","-")

def extraer_serie_de_doc(t):
    if pd.isna(t): return ""
    s=str(t).upper()
    m=re.search(r"\b([EF]\d{3})-(\d{3,})\b", s)
    return f"{m.group(1)}-{m.group(2)}" if m else ""

def df_a_pdf(df, titulo):
    try:
        from reportlab.lib.pagesizes import landscape, A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        buf=BytesIO(); doc=SimpleDocTemplate(buf, pagesize=landscape(A4)); styles=getSampleStyleSheet()
        data=[list(df.columns.astype(str))] + df.astype(str).values.tolist()
        data=[[str(c)[:28] for c in row] for row in data]
        t=Table(data, repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0F2A44")),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTSIZE',(0,0),(-1,-1),7),('GRID',(0,0),(-1,-1),0.5,colors.grey),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white, colors.HexColor("#EAF2F8")])]))
        doc.build([Paragraph(titulo, styles['Title']), t]); buf.seek(0); return buf.getvalue()
    except: return None

def mostrar_opciones(df, nombre_base):
    c1,c2,c3,c4=st.columns(4)
    out_xlsx=BytesIO()
    with pd.ExcelWriter(out_xlsx, engine='openpyxl') as w: df.to_excel(w, index=False)
    c1.download_button("Excel", out_xlsx.getvalue(), f"{nombre_base}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{nombre_base}")
    c2.download_button("CSV", df.to_csv(index=False).encode('utf-8-sig'), f"{nombre_base}.csv", mime="text/csv", use_container_width=True, key=f"csv_{nombre_base}")
    pdf_bytes=df_a_pdf(df, nombre_base)
    if pdf_bytes: c3.download_button("PDF", pdf_bytes, f"{nombre_base}.pdf", mime="application/pdf", use_container_width=True, key=f"pdf_{nombre_base}")
    else: c3.button("PDF — Requiere reportlab", use_container_width=True, key=f"pdf_fail_{nombre_base}")
    if c4.button("Copiar tabla", use_container_width=True, key=f"copybtn_{nombre_base}"):
        st.session_state[f"show_{nombre_base}"]=True
    if st.session_state.get(f"show_{nombre_base}", False):
        st.code(df.to_csv(index=False, sep="\t"), language="text")

def pintar_consol(df):
    def cr(v):
        s=str(v)
        if "CONCILIADO" in s: return 'background-color: #C6EFCE; color: #006100; font-weight: bold'
        if "HALLAZGO" in s: return 'background-color: #FFC7CE; color: #9C0006; font-weight: bold'
        return ''
    def cd(v):
        try:
            f=float(v)
            if abs(f)>1: return 'background-color: #FFC7CE; color: #9C0006; font-weight: bold'
            if f==0: return 'background-color: #C6EFCE; color: #006100'
        except: pass
        return ''
    styled=df.style.map(cr, subset=['Resultado'])
    for c in ['Dif Base','Dif IGV','Dif Total']:
        if c in df.columns: styled=styled.map(cd, subset=[c])
    return styled

def llamar_groq(pregunta, df_contexto):
    contexto = df_contexto.to_string(index=False)[:8000]
    prompt = f"""Eres Grok, auditor senior peruano, experto SUNAT. Tienes el consolidado real.
DATOS:
{contexto}
Pregunta: {pregunta}
Responde con montos, series y fechas reales. Si te dicen Hola Grok, responde como Grok. No inventes. Tono profesional, corto."""
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={"model": MODELO, "messages": [{"role":"system","content":"Eres Grok, auditor senior, respondes con datos reales."},{"role":"user","content":prompt}], "temperature": 0.1, "max_tokens": 900},
            timeout=30)
        if r.status_code==200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            return f"Error Groq {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"Error conexión: {e}"

if st.session_state.ejecutado and pdfs and st.session_state.df_pdfs is None:
    with st.status("Procesando validación documental...", expanded=True) as status:
        st.write("Extrayendo texto de facturas PDF y aplicando OCR...")
        time.sleep(0.4)
        st.write("Identificando Serie, RUC y proveedor...")
        df_pdfs=pd.DataFrame([extraer_pdf(p) for p in pdfs])
        df_pdfs.insert(0,"Item",range(1,len(df_pdfs)+1))
        st.write(f"Verificando identidad por Serie + RUC + Total — {len(df_pdfs)} documentos...")
        st.write("Recalculando Base + IGV = Total / IGV = Base x 18%...")
        if libro is not None:
            df_libro=pd.read_excel(libro, header=0)
            df_libro_display = df_libro.copy()
            for c in df_libro_display.columns:
                try: df_libro_display[c] = df_libro_display[c].astype(str)
                except: pass
            st.session_state.df_libro=df_libro_display
            mapa=ia_mapear(df_libro)
            col_total=mapa.get("TOTAL"); col_igv=mapa.get("IGV"); col_base=mapa.get("BASE"); col_femis=mapa.get("F_EMIS"); col_fven=mapa.get("F_VEN"); col_doc=mapa.get("DOC"); col_ruc=mapa.get("RUC")
            resultados=[]; usados=set()
            for idx, row in df_libro.iterrows():
                base_lib=float(row[col_base]) if col_base and pd.notna(row[col_base]) else 0
                igv_lib=float(row[col_igv]) if col_igv and pd.notna(row[col_igv]) else 0
                total_lib=float(row[col_total]) if col_total and pd.notna(row[col_total]) else 0
                f_emis_lib=norm_fecha(row[col_femis]) if col_femis else ""; f_ven_lib=norm_fecha(row[col_fven]) if col_fven else ""
                doc_libro=str(row[col_doc]) if col_doc and pd.notna(row[col_doc]) else ""
                serie_libro=extraer_serie_de_doc(doc_libro)
                ruc_libro=str(row[col_ruc]) if col_ruc and pd.notna(row[col_ruc]) else ""
                m_ruc=re.search(r"\d{11}", ruc_libro); ruc_clean=m_ruc.group(0) if m_ruc else ""
                match=None; match_idx=-1
                if serie_libro!="":
                    cands=[]
                    for j, prow in df_pdfs.iterrows():
                        if j in usados: continue
                        if prow["Serie - N° Comprobante"]==serie_libro:
                            cands.append((abs(prow["Total"]-total_lib), j, prow))
                    if cands:
                        cands.sort(key=lambda x: x[0]); _, match_idx, match=cands[0]
                if match is None:
                    for j, prow in df_pdfs.iterrows():
                        if j in usados: continue
                        if ruc_clean!="" and prow["RUC"]==ruc_clean and abs(prow["Total"]-total_lib)<2:
                            match=prow; match_idx=j; break
                if match is not None:
                    usados.add(match_idx)
                    f_emis_ver=norm_fecha(match["F. Emis."]); f_ven_ver=norm_fecha(match["F. Venc."])
                    hallazgos=[]
                    if p_recalculo:
                        igv_esp=round(base_lib*0.18,2)
                        if abs(igv_esp-igv_lib)>1.0: hallazgos.append(f"Recálculo IGV: Base {base_lib} x 18% = {igv_esp} vs {igv_lib}")
                        tot_esp=round(base_lib+igv_lib,2)
                        if abs(tot_esp-total_lib)>1.0: hallazgos.append(f"Recálculo Total: {base_lib}+{igv_lib}={tot_esp} vs {total_lib}")
                    if p_concilia:
                        if abs(round(match["Base"]-base_lib,2))>materialidad: hallazgos.append(f"Base: Libro {base_lib} vs Fuente {match['Base']}")
                        if abs(round(match["IGV"]-igv_lib,2))>materialidad: hallazgos.append(f"IGV: Libro {igv_lib} vs Fuente {match['IGV']}")
                        if abs(round(match["Total"]-total_lib,2))>materialidad: hallazgos.append(f"Total: Libro {total_lib} vs Fuente {match['Total']}")
                    if p_fechas:
                        if f_emis_lib!=f_emis_ver and f_emis_lib!="" and f_emis_ver!="": hallazgos.append(f"Fecha emisión: Libro {f_emis_lib} vs Fuente {f_emis_ver}")
                        if f_ven_lib!=f_ven_ver and f_ven_lib!="" and f_ven_ver!="": hallazgos.append(f"Fecha vencimiento: Libro {f_ven_lib} vs Fuente {f_ven_ver}")
                    estado="CONCILIADO" if len(hallazgos)==0 else "HALLAZGO"
                    resultados.append({"Item":idx,"Serie Libro":serie_libro if serie_libro else "(por RUC+Total)","Serie Fuente":match["Serie - N° Comprobante"],"Documento":doc_libro[:50],"RUC Fuente":match["RUC"],"Proveedor Fuente":match["Proveedor"],"Base Libro":base_lib,"Base Fuente":match["Base"],"Dif Base":round(match["Base"]-base_lib,2),"IGV Libro":igv_lib,"IGV Fuente":match["IGV"],"Dif IGV":round(match["IGV"]-igv_lib,2),"Total Libro":total_lib,"Total Fuente":match["Total"],"Dif Total":round(match["Total"]-total_lib,2),"F. Emis. Libro":f_emis_lib,"F. Emis. Fuente":f_emis_ver,"F. Venc. Libro":f_ven_lib,"F. Venc. Fuente":f_ven_ver,"Resultado":estado,"Detalle":" | ".join(hallazgos) if hallazgos else "Sin diferencias"})
                else:
                    resultados.append({"Item":idx,"Serie Libro":serie_libro,"Documento":doc_libro[:50],"RUC Fuente":"NO ENCONTRADA","Resultado":"NO ENCONTRADA","Detalle":f"No se encontró Serie {serie_libro} Total {total_lib}","Base Libro":base_lib,"IGV Libro":igv_lib,"Total Libro":total_lib})
            st.session_state.df_consol=pd.DataFrame(resultados)
        st.session_state.df_pdfs=df_pdfs
        st.write("Elaborando consolidado y conclusión...")
        status.update(label="Validación completada", state="complete", expanded=False)

if st.session_state.df_pdfs is not None:
    st.markdown("### 1. Documento fuente — Facturas")
    st.dataframe(st.session_state.df_pdfs.astype(str), width='stretch', hide_index=True)
    mostrar_opciones(st.session_state.df_pdfs, "1_Fuente")
if st.session_state.df_libro is not None:
    st.markdown("### 2. Registro contable")
    st.dataframe(st.session_state.df_libro.astype(str), width='stretch', hide_index=True)
    mostrar_opciones(st.session_state.df_libro, "2_Registro")
if st.session_state.df_consol is not None:
    df_c=st.session_state.df_consol
    total=len(df_c); ok=len(df_c[df_c['Resultado'].str.contains("CONCILIADO")]); hall=total-ok
    dif_total=df_c['Dif Total'].sum() if 'Dif Total' in df_c.columns else 0
    if st.session_state.get("show_anim", False):
        st.toast(f"Validación completada: {ok} conciliados, {hall} con hallazgos", icon="✅")
        if hall == 0:
            st.balloons()
        else:
            st.snow()
        st.session_state.show_anim=False
    k1,k2,k3,k4=st.columns(4)
    k1.markdown(f'<div class="kpi-card"><div class="kpi-num">{total}</div><div class="kpi-label">Comprobantes revisados</div></div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="kpi-card"><div class="kpi-num" style="color:#006100">{ok}</div><div class="kpi-label">Conciliados</div></div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="kpi-card"><div class="kpi-num" style="color:#9C0006">{hall}</div><div class="kpi-label">Con hallazgos</div></div>', unsafe_allow_html=True)
    k4.markdown(f'<div class="kpi-card"><div class="kpi-num">S/ {abs(dif_total):,.2f}</div><div class="kpi-label">Monto en riesgo</div></div>', unsafe_allow_html=True)
    st.markdown("### 3. Consolidado final")
    st.dataframe(pintar_consol(df_c), width='stretch', hide_index=True)
    mostrar_opciones(df_c, "3_Consolidado")
    st.divider()
    st.markdown("### 4. Conclusión")
    dif_base_total=df_c['Dif Base'].sum() if 'Dif Base' in df_c.columns else 0
    dif_igv_total=df_c['Dif IGV'].sum() if 'Dif IGV' in df_c.columns else 0
    if hall==0:
        st.success(f"De {total} comprobantes verificados contra el documento fuente, todos se encuentran conciliados.")
    else:
        st.error(f"De {total} comprobantes, {ok} conciliados y {hall} con hallazgos. El documento fuente prevalece sobre el registro contable.")
        st.markdown(f"- **Diferencia acumulada:** Base S/ {dif_base_total:,.2f} | IGV S/ {dif_igv_total:,.2f} | Total S/ {dif_total:,.2f}  \n- **Efecto:** Se recomienda ajuste contable por S/ {abs(dif_total):,.2f}.")
        st.code(f"Conclusión: De {total} comprobantes, {ok} conciliados y {hall} con hallazgos. Diferencia Base {dif_base_total:.2f} IGV {dif_igv_total:.2f} Total {dif_total:.2f}.", language="text")
    st.divider()
    with st.container(border=True):
        st.markdown("### 5. Agente de análisis — IA conectada")
        st.markdown("""
        <div class="suggest-box">
        <b>Puedes empezar con:</b><br>
        - Hola, Grok? ¿de qué consisten estas facturas?<br>
        - ¿Cuáles son las facturas mayores a S/ 100,000?<br>
        - Dame las fechas de emisión y vencimiento de los 5 comprobantes<br>
        - ¿Cuál es el de mayor monto y por qué tiene hallazgo?<br>
        - Dame el asiento de ajuste contable
        </div>
        """, unsafe_allow_html=True)
        for msg in st.session_state.chat:
            with st.chat_message(msg["role"]): st.write(msg["content"])
        col_preg, col_btn1, col_btn2 = st.columns([5,1,1])
        with col_preg:
            pregunta = st.text_input("Pregunte al agente:", placeholder="Pregunte sobre hallazgos, montos, series, fechas...", key="input_agente", label_visibility="collapsed")
        with col_btn1:
            enviar = st.button("Preguntar", use_container_width=True)
        with col_btn2:
            limpiar = st.button("Limpiar", use_container_width=True)
        if limpiar:
            st.session_state.chat=[]
            st.session_state.df_pdfs=None; st.session_state.df_libro=None; st.session_state.df_consol=None; st.session_state.ejecutado=False
            st.rerun()
        if enviar and pregunta:
            st.session_state.chat.append({"role":"user","content":pregunta})
            with st.chat_message("user"): st.write(pregunta)
            with st.chat_message("assistant"):
                with st.spinner("Analizando con Grok..."):
                    resp = llamar_groq(pregunta, df_c)
                    st.write(resp)
                    st.session_state.chat.append({"role":"assistant","content":resp})
elif not st.session_state.ejecutado:
    st.info("Cargue el documento fuente y el registro contable para iniciar la validación.")

st.markdown("---")
st.markdown(f"""
<div style="text-align:center; padding:18px; margin-top:20px; background:#F8FAFC; border-radius:10px; border:1px solid #E2E8F0;">
    <div style="font-size:13px; color:#64748B;">Desarrollado para mejorar los procedimientos de pruebas en auditoría</div>
    <div style="font-size:16px; font-weight:800; color:#0F2A44; margin-top:4px;">Proyecto por {AUTOR}</div>
    <div style="font-size:12px; color:#94A3B8;">AuditorIA Pro — Validación Documental con IA • 2026 • Lima, Perú</div>
</div>
""", unsafe_allow_html=True)