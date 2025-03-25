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
    st.success("Relatório gerado com sucesso!")
