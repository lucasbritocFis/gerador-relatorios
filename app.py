import streamlit as st
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import io
import fitz  # PyMuPDF
from PIL import Image
import pdfplumber
import re
from datetime import datetime

# Função para extrair imagens e texto do PDF REL
def extrair_imagens_e_texto(pdf_file):
    """Extrai imagens e texto de um PDF fornecido por upload."""
    try:
        doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
        all_images = []
        texto_total = ""
        for page in doc:
            texto_total += page.get_text()
            for img in page.get_images(full=True):
                img_bytes = doc.extract_image(img[0])["image"]
                image = Image.open(io.BytesIO(img_bytes))
                all_images.append(image)
        return all_images, texto_total
    except Exception as e:
        st.error(f"Erro ao processar PDF REL: {str(e)}")
        return [], ""

# Função para extrair dados do texto
def extrair_dados(texto):
    """Extrai informações específicas do texto usando expressões regulares."""
    try:
        padroes = {
            "nome": (r"Nome:\s*(.+?)\s*Data", lambda x: x[:28]),
            "data_nasc": (r"Data de Nasc.:\s*(.+?)\s*Pront", lambda x: datetime.strptime(x, "%A, %B %d, %Y").strftime("%d/%m/%Y")),
            "pront": (r"Prontuário:\s*(\d+)", str),
            "radio": (r"Radio-Oncologista:\s*(.+)", str),
            "curso": (r"Curso / Plano:\s*(.+)", str),
            "dose": (r"Dose de Prescrição:\s*(.+)", str),
            "curva": (r"Curva de Prescrição:\s*(.+)", str),
            "ct": (r"Imagem Utilizada:\s*(.+)", str),
            "desloc": (r"Deslocamento da mesa da posição de setup de referência:\s*(.+)", str)
        }
        dados = {}
        for chave, (padrao, transform) in padroes.items():
            match = re.search(padrao, texto)
            dados[chave] = transform(match.group(1).strip()) if match else "Não encontrado"
        return dados
    except Exception as e:
        st.error(f"Erro ao extrair dados: {str(e)}")
        return {}

# Função para extrair dados de QA do PDF CQ
def extrair_qa(pdf_qa_file):
    """Extrai informações de controle de qualidade do PDF CQ."""
    try:
        with pdfplumber.open(pdf_qa_file) as pdf_qa:
            text_qa = "".join(page.extract_text() or "" for page in pdf_qa.pages)
        linhas = text_qa.strip().split("\n")
        area_gama_valores1 = [float(re.findall(r"(\d+\.?\d*)\s*%", linha)[1]) 
                              for linha in linhas if "Área gama < 1,0" in linha and len(re.findall(r"(\d+\.?\d*)\s*%", linha)) >= 2]
        return {
            "campos": re.compile(r'Campo \d+').findall(text_qa),
            "area_gama": re.compile(r'Área gama < 1,0\s+(\d+\.\d+) %').findall(text_qa),
            "resultados": re.compile(r'Resultado da análise\s*[:.-]?\s*(.*?(?=\n|$))', re.IGNORECASE).findall(text_qa),
            "gama_dta": re.compile(r'Gama DTA\s*:\s*(\d+\.\d+)\s*mm\s*Tol\.\s*:\s*(\d+\.\d+) %').findall(text_qa),
            "area_gama_dupla": area_gama_valores1
        }
    except Exception as e:
        st.error(f"Erro ao processar PDF QA: {str(e)}")
        return {}

# Função para gerar o PDF
def gerar_pdf(all_images, dados, qa_data):
    """Gera um PDF unificado com layout profissional."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y_position = height - 50

    # Título
    titulo = dados.get("nome", "Não encontrado")[:9] + " " + dados.get("nome", "")[9:11] + " " + dados.get("nome", "")[11:16] + " " + dados.get("nome", "")[16:18] + " " + dados.get("nome", "")[18:28]
    c.setFont("Helvetica", 16)
    c.drawString(60, y_position - 10, titulo)

    # Dados do paciente
    campos = {
        "Nome": dados.get("nome", "Não encontrado"),
        "Data de Nascimento": dados.get("data_nasc", "Não encontrado"),
        "Prontuário": dados.get("pront", "Não encontrado"),
        "Radio-Oncologista": dados.get("radio", "Não encontrado"),
        "Curso/Plano": dados.get("curso", "Não encontrado"),
        "Tomografia": dados.get("ct", "Não encontrado"),
        "Dose de Prescrição": dados.get("dose", "Não encontrado"),
        "Curva de Prescrição": dados.get("curva", "Não encontrado")
    }
    y = 700
    for chave, valor in list(campos.items())[:4]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(60, y, f"{chave}: ")
        c.setFont("Helvetica", 9)
        c.drawString(155, y, valor)
        y -= 20
    y1 = 700
    for chave, valor in list(campos.items())[4:]:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(315, y1, f"{chave}: ")
        c.setFont("Helvetica", 9)
        c.drawString(407, y1, valor)
        y1 -= 20

    # Deslocamento
    c.setFont("Helvetica", 7)
    c.line(60, y_position - 120, 590, y_position - 120)
    c.drawString(60, y_position - 133, "DESLOCAMENTO DA MESA")
    c.line(60, y_position - 140, 590, y_position - 140)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(75, y_position - 155, "LATERAL")
    c.drawString(75, y_position - 165, "Valor cm")
    c.drawString(245, y_position - 155, "VERTICAL")
    c.drawString(245, y_position - 165, "Valor cm")
    c.drawString(445, y_position - 155, "LONGITUDINAL")
    c.drawString(445, y_position - 165, "Valor cm")

    # Imagens
    for i, img in enumerate(all_images[:3]):
        img_path = f"temp_image{i}.png"
        img.save(img_path, "PNG")
        c.drawImage(img_path, 30 + i*170, y_position - 280, width=160, height=100)

    # Controle de Qualidade
    c.setFont("Helvetica", 7)
    c.line(60, 150, 590, 150)
    c.drawString(60, 137, "CONTROLE DE QUALIDADE - EQUIPAMENTO USADO: EPID, METODOLOGIA USADA: ANÁLISE GAMA")
    c.line(60, 130, 590, 130)
    c.drawString(60, 120, "Campo")
    c.drawString(60, 110, "Gama DTA")
    c.drawString(60, 100, "Tolerância")
    c.drawString(60, 90, "Área gama < 1,0")
    c.drawString(60, 80, "Resultado")
    a = 0
    for i, campo in enumerate(qa_data.get("campos", [])):
        cam = campo.replace("Campo", "")
        c.drawString(128 + a, 120, cam)
        c.drawString(130 + a, 110, f"{qa_data.get('gama_dta', [('', '')])[i][1]} % / {qa_data.get('gama_dta', [('', '')])[i][0]} mm")
        c.drawString(130 + a, 90, f"{qa_data.get('area_gama', [''])[i]} %")
        c.drawString(130 + a, 100, f"{qa_data.get('area_gama_dupla', [''])[i]} %")
        c.setFont("Helvetica-Bold", 7)
        c.setFillColor(colors.limegreen)
        resultado = qa_data.get("resultados", [""])[i].strip().lower().replace("aprovado", "Aprovado")
        c.drawString(130 + a, 80, resultado)
        a += 60

    c.save()
    buffer.seek(0)
    return buffer

# Interface Streamlit
st.set_page_config(page_title="Gerador de Relatórios", layout="wide", page_icon="🩺")
st.markdown("<style>.stButton>button {background-color: #4CAF50; color: white; border-radius: 10px;}</style>", unsafe_allow_html=True)
st.title("🩺 Gerador de Relatórios de Tratamento")
st.markdown("Unifique relatórios de tratamento e controle de qualidade em um único PDF profissional.")

# Upload de PDFs
uploaded_rel = st.file_uploader("Carregar PDF de Relatório de Tratamento", type="pdf")
uploaded_qa = st.file_uploader("Carregar PDF de Controle de Qualidade", type="pdf")

if st.button("Gerar Relatório"):
    if uploaded_rel and uploaded_qa:
        with st.spinner("Gerando o PDF..."):
            all_images, texto = extrair_imagens_e_texto(uploaded_rel)
            if all_images and texto:
                dados = extrair_dados(texto)
                qa_data = extrair_qa(uploaded_qa)
                pdf_buffer = gerar_pdf(all_images, dados, qa_data)
                if pdf_buffer:
                    st.success("Relatório gerado com sucesso!")
                    st.download_button(
                        label="Baixar Relatório",
                        data=pdf_buffer,
                        file_name="relatorio_unificado.pdf",
                        mime="application/pdf"
                    )
    else:
        st.error("Por favor, carregue ambos os PDFs.")
