import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os

# Configuração da página
st.set_page_config(
    page_title="Gerador de Relatórios de Tratamento",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
    <style>
    .main {
        background-color: #000000;
        padding: 20px;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
    }
    .stFileUploader {
        border: 2px dashed #2196F3;
        padding: 10px;
    }
    h1 {
        color: #2196F3;
        text-align: center;
    }
    .sidebar .sidebar-content {
        background-color: #e0e7ff;
    }
    </style>
""", unsafe_allow_html=True)

# Funções de processamento (reutilizando o código otimizado)
def extract_content(uploaded_files):
    images = []
    full_text = ""
    for uploaded_file in uploaded_files:
        with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
            for page in doc:
                for img in page.get_images(full=True):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    img_bytes = base_image["image"]
                    image = Image.open(io.BytesIO(img_bytes))
                    temp_path = f"temp_image{len(images)}.png"
                    image.save(temp_path, format='PNG')
                    images.append(temp_path)
                full_text += page.get_text()
    return images, full_text

def parse_text(text):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    footer_info = lines[:13]
    patient_info = lines[13:38]
    plan_info = next((line for line in lines if line.startswith("Campos no plano")), "")
    fields_text = " ".join(lines[38:lines.index("Nome do paciente:") if "Nome do paciente:" in lines else len(lines)])
    fields_text = re.sub(r'\s+', ' ', fields_text.strip())
    values = fields_text.split()
    valid_ids = {"CBCT", "MV", "KV"}
    sections = {}
    current_id = None
    for value in values:
        if value in valid_ids or value.isdigit():
            current_id = value
            sections[current_id] = []
        elif current_id:
            sections[current_id].append(value)
    complete_lines = []
    for marker, data in sections.items():
        current_line = [marker]
        for item in data:
            current_line.append(item)
            if len(current_line) == 17:  # Ajustado para o número de colunas
                complete_lines.append(current_line)
                current_line = [marker]
        if len(current_line) > 1:
            complete_lines.append(current_line)
    return footer_info, patient_info, plan_info, complete_lines

def create_pdf(images, footer_info, patient_info, plan_info, field_lines):
    c = canvas.Canvas("output.pdf", pagesize=letter)
    width, height = letter
    c.setFont("Helvetica", 6)
    c.setStrokeColorRGB(0.0, 0.05, 0.25)
    c.setFont("Helvetica-Bold", 13)
    c.setFillColorRGB(0.82, 0.70, 0.53)
    c.drawString(50, 754, "INFORMAÇÕES TÉCNICAS DO PLANEJAMENTO DO TRATAMENTO")
    c.setFillColorRGB(0, 0, 0)
    c.line(0, 758, 650, 758)
    if os.path.exists("logo_dasa.PNG"):
        c.drawImage("logo_dasa.PNG", 510, 730, width=90, height=50)
    c.setFont("Helvetica-Bold", 6)
    positions = [(50, 705, patient_info[0]), (50, 695, patient_info[1]),
                 (280, 705, patient_info[6]), (280, 695, patient_info[8])]
    for x, y, text in positions:
        c.drawString(x, y, text)
    c.setFont("Helvetica", 6)
    c.drawString(310, 20, f"{patient_info[2]} {patient_info[5]}")
    c.drawString(50, 20, footer_info[11])
    c.setFont("Helvetica-Bold", 6)
    c.drawString(50, 648, f"Informações dos {plan_info}")
    c.setFont("Helvetica", 6)
    c.line(50, 643, 580, 643)
    x_positions = [50, 90, 120, 170, 195, 230, 250, 270, 290, 320, 360, 410, 445, 465, 485, 505, 540]
    headers = ["ID", "Técnica", "Máquina", "Energia", "Escala", "X1[cm]", "X2[cm]", "Y1[cm]",
               "Y2[cm]", "Gantry", "Colimador", "Mesa", "X[cm]", "Y[cm]", "Z[cm]", "SSD[cm]", "UM"]
    for i, header in enumerate(headers):
        c.drawString(x_positions[i], 635, header)
    y = 622
    for line in field_lines[:3]:
        for i, value in enumerate(line[:len(headers)]):
            c.drawString(x_positions[i], y, value)
        y -= 8
    y = 598
    for line in field_lines[3:]:
        for i, value in enumerate(line[:len(headers)]):
            c.drawString(x_positions[i], y, value)
        y -= 8
    if len(images) >= 4:
        c.drawImage(images[0], 60, 40, width=230, height=230)
        c.drawImage(images[1], 320, 40, width=230, height=230)
        c.drawImage(images[2], 60, 285, width=230, height=230)
        c.drawImage(images[3], 320, 285, width=230, height=230)
    c.save()

# Interface do Streamlit
st.title("🏥 Gerador de Relatórios de Tratamento")
st.sidebar.header("Opções")
st.sidebar.write("Use esta ferramenta para gerar relatórios a partir de PDFs médicos.")

# Upload da logo
uploaded_logo = st.sidebar.file_uploader("Carregar Logo (PNG)", type="png")
if uploaded_logo:
    with open("logo_dasa.PNG", "wb") as f:
        f.write(uploaded_logo.read())
    st.sidebar.image("logo_dasa.PNG", width=150)

# Upload dos PDFs
st.write("Faça o upload dos PDFs para gerar o relatório:")
uploaded_files = st.file_uploader("Escolha os PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files and st.button("Gerar Relatório"):
    with st.spinner("Processando os PDFs..."):
        images, text = extract_content(uploaded_files)
        footer_info, patient_info, plan_info, field_lines = parse_text(text)
        create_pdf(images, footer_info, patient_info, plan_info, field_lines)

        with open("output.pdf", "rb") as f:
            st.download_button(
                label="Baixar Relatório",
                data=f,
                file_name="relatorio_medico.pdf",
                mime="application/pdf"
            )
        for img in images:
            os.remove(img)
        os.remove("output.pdf")
    st.success("Relatório gerado com sucessoimport streamlit as st
import fitz  # PyMuPDF
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import re
from datetime import datetime
import pdfplumber
from reportlab.lib import colors

# Função para extrair imagens e texto do PDF de Relatório de Tratamento
def extrair_imagens_e_texto(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_images = []
    text = ""
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text += page.get_text()
        for img in page.get_images(full=True):
            xref = img[0]
            base_image = doc.extract_image(xref)
            img_bytes = base_image["image"]
            image = Image.open(io.BytesIO(img_bytes))
            temp_image_path = f"temp_image{len(all_images)}.png"
            image.save(temp_image_path, format='PNG')
            all_images.append(temp_image_path)
    return all_images, text

# Função para extrair dados de QA do PDF CQ
def extrair_qa(pdf_qa_file):
    with pdfplumber.open(pdf_qa_file) as pdf_qa:
        text_qa = ''
        for page_qa in pdf_qa.pages:
            text_qa += page_qa.extract_text() or ""
    
    linhas_qa_novo = text_qa.strip().split("\n")
    area_gama_valores1 = []
    for linha_qa_novo in linhas_qa_novo:
        if "Área gama < 1,0" in linha_qa_novo:
            matches_qa = re.findall(r"(\d+\.?\d*)\s*%", linha_qa_novo)
            if len(matches_qa) >= 2:
                area_gama_valores1.append(float(matches_qa[1]))

    campo_regex = re.compile(r'Campo \d+')
    area_gama_regex = re.compile(r'Área gama < 1,0\s+(\d+\.\d+) %')
    resultado_analise_regex = re.compile(r'Resultado da análise\s*[:.-]?\s*(.*?(?=\n|$))', re.IGNORECASE)
    gama_dta_regex = re.compile(r'Gama DTA\s*:\s*(\d+\.\d+)\s*mm\s*Tol\.\s*:\s*(\d+\.\d+) %')

    return {
        "campos_qa": campo_regex.findall(text_qa),
        "area_gama_valores": area_gama_regex.findall(text_qa),
        "resultados_analise": resultado_analise_regex.findall(text_qa),
        "gama_dta_valores": gama_dta_regex.findall(text_qa),
        "area_gama_valores1": area_gama_valores1
    }

# Função para gerar o PDF
def gerar_pdf(all_images, text, qa_data, logo_file, ass1_file, ass2_file):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y_position = height - 50
    x_offset = 50
    y_offset = 750
    line_height = 14

    # Logo
    logo_path = "logo_temp.png"
    with open(logo_path, "wb") as f:
        f.write(logo_file.read())
    c.drawImage(logo_path, 510, 730, width=80, height=40)

    # Título
    titulo = text[0:144]
    titulo_semsp = titulo.replace(' ', '')
    titulo2 = (titulo_semsp[:9] + " " + titulo_semsp[9:11] + " " + titulo_semsp[11:16] + " " + titulo_semsp[16:18] + " " + titulo_semsp[18:28])
    c.setFont("Helvetica", 16)
    c.drawString(60, y_offset - 10, titulo2)
    c.line(60, y_offset - 20, 590, y_offset - 20)

    # Dados do paciente
    nome = re.search(r"Nome:\s*(.+?)\s*Data", text)
    string_nome = nome.group(1).strip()[:28] if nome else "Não encontrado"
    data = re.search(r"Data de Nasc.:\s*(.+?)\s*Pront", text)
    data_nasc_str = data.group(1).strip() if data else "Não encontrado"
    data_form = datetime.strptime(data_nasc_str, "%A, %B %d, %Y").strftime("%d/%m/%Y") if data else "Não encontrado"
    pront = re.search(r"Prontuário:\s*(\d+)", text).group(1) if re.search(r"Prontuário:\s*(\d+)", text) else "Não encontrado"
    radio = re.search(r"Radio-Oncologista:\s*(.+)", text).group(1) if re.search(r"Radio-Oncologista:\s*(.+)", text) else "Não encontrado"
    curso = re.search(r"Curso / Plano:\s*(.+)", text).group(1) if re.search(r"Curso / Plano:\s*(.+)", text) else "Não encontrado"
    dose = re.search(r"Dose de Prescrição:\s*(.+)", text).group(1) if re.search(r"Dose de Prescrição:\s*(.+)", text) else "Não encontrado"
    curva = re.search(r"Curva de Prescrição:\s*(.+)", text).group(1) if re.search(r"Curva de Prescrição:\s*(.+)", text) else "Não encontrado"
    ct = re.search(r"Imagem Utilizada:\s*(.+)", text).group(1) if re.search(r"Imagem Utilizada:\s*(.+)", text) else "Não encontrado"

    campos = {
        "Nome ": string_nome, 
        "Data de Nascimento ": data_form, 
        "Prontuário ": pront, 
        "Radio-Oncologista ": radio, 
        "Curso/Plano ": curso, 
        "Tomografia ": ct, 
        "Dose de Prescrição ": dose, 
        "Curva de Prescrição ": curva
    }
    y = 700
    y1 = 700
    c.setFont("Helvetica", 9)
    for chave, valor in list(campos.items())[:4]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, y, f"{chave}: ")
        c.setFont("Helvetica", 9)
        c.drawString(155, y, valor)
        y -= 20
    for chave, valor in list(campos.items())[4:]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(315, y1, f"{chave}: ")
        c.setFont("Helvetica", 9)
        c.drawString(407, y1, valor)
        y1 -= 20

    # Deslocamentos
    linhas = text.splitlines()
    deslocamento = linhas[12:21] if len(linhas) > 20 else ["Deslocamento não encontrado"] * 9
    c.setFont("Helvetica", 7)
    c.setLineWidth(0.3)
    c.line(60, y_position - 120, 590, y_position - 120)
    c.drawString(60, y_position - 133, deslocamento[0].upper())
    c.line(60, y_position - 140, 590, y_position - 140)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(75, y_position - 155, "LATERAL")
    c.drawString(75, y_position - 165, deslocamento[2].upper() + " cm " + deslocamento[6].upper())
    c.drawString(245, y_position - 155, "VERTICAL")
    c.drawString(245, y_position - 165, deslocamento[3].upper() + " cm " + deslocamento[7].upper())
    c.drawString(445, y_position - 155, "LONGITUDINAL")
    c.drawString(445, y_position - 165, deslocamento[4].upper() + " cm " + deslocamento[8].upper())

    # Imagens
    for i in range(min(3, len(all_images))):
        c.drawImage(all_images[i], 30 + i * 145, y_position - 280, width=160, height=100)

    # Campos de Tratamento e QA
    cabecalho = linhas[23:48] if len(linhas) > 47 else ["Não encontrado"] * 25
    c.line(60, 150, 590, 150)
    c.drawString(60, 137, "CONTROLE DE QUALIDADE - EQUIPAMENTO USADO: EPID, METODOLOGIA USADA: ANÁLISE GAMA")
    c.line(60, 130, 590, 130)
    c.drawString(60, 120, cabecalho[0])
    c.drawString(60, 110, "Gama DTA")
    c.drawString(60, 100, "Tolerância")
    c.drawString(60, 90, "Área gama < 1,0")
    c.drawString(60, 80, "Resultado")
    a = 1
    for i in range(len(qa_data["campos_qa"])):
        cam = qa_data["campos_qa"][i].replace("Campo", "")
        c.drawString(128 + a, 120, cam)
        c.drawString(130 + a, 110, f"{qa_data['gama_dta_valores'][i][1]} % / {qa_data['gama_dta_valores'][i][0]} mm")
        c.drawString(130 + a, 90, f"{qa_data['area_gama_valores'][i]} %")
        c.drawString(130 + a, 100, f"{qa_data['area_gama_valores1'][i]} %")
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.limegreen)
        results = qa_data["resultados_analise"][i].strip().lower()
        novoresults = results.replace("aprovado", "Aprovado").strip()
        c.drawString(130 + a, 80, novoresults)
        a += 60
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.black)

    # Assinaturas
    ass1_path = "ass1_temp.jpg"
    with open(ass1_path, "wb") as f:
        f.write(ass1_file.read())
    c.drawImage(ass1_path, 450, 21, width=90, height=40)
    
    ass2_path = "ass2_temp.jpg"
    with open(ass2_path, "wb") as f:
        f.write(ass2_file.read())
    c.drawImage(ass2_path, 160, 12, width=100, height=50)

    c.setFont("Helvetica", 10)
    c.drawString(60, 20, "PLANEJADO POR:  ________________________    ")
    c.drawString(330, 20, "VERIFICADO POR:  _________________________  ")

    c.save()
    buffer.seek(0)
    return buffer

# Interface Streamlit
st.set_page_config(page_title="Gerador de Relatórios", layout="wide", page_icon="🩺")
st.markdown("<style>.stButton>button {background-color: #4CAF50; color: white; border-radius: 10px;}</style>", unsafe_allow_html=True)
st.title("🩺 Gerador de Relatórios de Tratamento")
st.markdown("Carregue os PDFs e imagens para gerar o relatório unificado.")

# Upload dos arquivos
uploaded_rel = st.file_uploader("PDF de Relatório de Tratamento (REP REL)", type="pdf")
uploaded_qa = st.file_uploader("PDF de Controle de Qualidade (REP CQ)", type="pdf")
uploaded_logo = st.file_uploader("Logo Dasa Oncologia", type=["png", "jpg"])
uploaded_ass1 = st.file_uploader("Assinatura Guilherme", type=["jpg"])
uploaded_ass2 = st.file_uploader("Assinatura Lucas", type=["jpg"])

if st.button("Gerar Relatório"):
    if uploaded_rel and uploaded_qa and uploaded_logo and uploaded_ass1 and uploaded_ass2:
        with st.spinner("Gerando o PDF..."):
            all_images, text = extrair_imagens_e_texto(uploaded_rel)
            qa_data = extrair_qa(uploaded_qa)
            pdf_buffer = gerar_pdf(all_images, text, qa_data, uploaded_logo, uploaded_ass1, uploaded_ass2)
            st.success("Relatório gerado com sucesso!")
            st.download_button(
                label="Baixar Relatório",
                data=pdf_buffer,
                file_name="output.pdf",
                mime="application/pdf"
            )
    else:
        st.error("Por favor, carregue todos os arquivos necessários.")
