
import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from datetime import datetime
import pytz

VALOR_UNITARIO = 21.51

st.set_page_config(layout="centered")

st.markdown("""
### 📜 Objetivo da Aplicação

Esta aplicação tem como objetivo automatizar a análise de faturamento de chips fornecidos por parceiros, com base em regras definidas previamente. O processo consiste em importar as planilhas necessárias, validar os dados conforme critérios estabelecidos, e gerar dois relatórios: um detalhado em Excel e um resumo executivo em PDF.

A aplicação compara a base fornecida com a base interna da RNP, verificando se os chips estão aptos a faturamento conforme os critérios abaixo.

---

### 📌 Regras de Faturamento

| Status                  | Critério de Faturamento                                                                                   |
|-------------------------|------------------------------------------------------------------------------------------------------------|
| **ATIVO**               | Faturar se a data de ativação for até o último dia do mês de competência                                   |
| **CANCELADO**           | Faturar se a data de cancelamento estiver dentro do mês de competência                                     |
| **EXTRAVIADO**          | **Não faturar**                                                                                            |
| **INATIVO**             | **Não faturar**                                                                                            |
| **SUSPENSO**            | Faturar se:<br>
1️⃣ A data de suspensão estiver dentro do mês de competência<br>
2️⃣ A suspensão ocorrer dentro do período de fidelidade (até 90 dias após ativação) e esse limite cair no mês de competência<br>
3️⃣ A suspensão ocorrer **após** o mês de competência |
| **CHIP TESTE**          | Sempre deve ser faturado                                                                                   |
| **Fora da Base Interna**| Só fatura se estiver na **lista de aquisição** **e** for **chip teste**                                   |

---

⚠️ Antes de iniciar a análise, preencha os campos obrigatórios (Fornecedor e Mês de Referência) e envie as quatro planilhas solicitadas:  
- Base do Fornecedor  
- Base Interna  
- Lista de Aquisição  
- Lista de Chips de Teste  
""", unsafe_allow_html=True)

def processar_bases(fornecedor_df, interna_df, lista_aquisicao_df, chips_teste_df):
    fornecedor_df['ICCID'] = fornecedor_df['Iccid'].astype(str).str.strip()
    interna_df.columns = interna_df.columns.str.strip()
    interna_df['ICCID'] = interna_df['ICCID'].astype(str).str.strip()
    lista_aquisicao_df['iccid'] = lista_aquisicao_df['iccid'].astype(str).str.strip()
    chips_teste_df['ICCID'] = chips_teste_df['ICCID'].astype(str).str.strip()
    merged_df = pd.merge(fornecedor_df[['ICCID']], interna_df, on='ICCID', how='left')
    merged_df['CONSTA BASE B2'] = merged_df['STATUS'].apply(lambda x: 'SIM' if pd.notnull(x) else 'NÃO')
    merged_df['LISTA DE AQUISIÇÃO RNP'] = merged_df['ICCID'].isin(lista_aquisicao_df['iccid']).map({True: 'SIM', False: 'NÃO'})
    merged_df['CHIP TESTE'] = merged_df['ICCID'].isin(chips_teste_df['ICCID']).map({True: 'SIM', False: 'NÃO'})
    competencia_fim = pd.to_datetime('2025-04-30')
    def verifica_faturamento(row):
        if row['CHIP TESTE'] == 'SIM':
            return 'SIM'
        if row['CONSTA BASE B2'] == 'NÃO':
            if row['LISTA DE AQUISIÇÃO RNP'] == 'NÃO':
                return 'NÃO'
        status = row['STATUS']
        ativacao = row['DATA DE ATIVAÇÃO']
        cancelamento = row['DATA DE CANCELAMENTO']
        suspensao = row['DATA DE SUSPENSÃO']
        if status in ['EXTRAVIADO', 'INATIVO']:
            return 'NÃO'
        if status == 'ATIVO':
            if pd.notnull(ativacao) and ativacao <= competencia_fim:
                return 'SIM'
            return 'NÃO'
        if status == 'CANCELADO':
            if pd.notnull(cancelamento) and cancelamento.month == competencia_fim.month and cancelamento.year == competencia_fim.year:
                return 'SIM'
            return 'NÃO'
        if status == 'SUSPENSO':
            if pd.notnull(suspensao) and suspensao.month == competencia_fim.month and suspensao.year == competencia_fim.year:
                return 'SIM'
            if pd.notnull(suspensao) and pd.notnull(ativacao):
                fidelidade_limite = ativacao + pd.Timedelta(days=90)
                if suspensao <= fidelidade_limite and fidelidade_limite.month == competencia_fim.month and fidelidade_limite.year == competencia_fim.year:
                    return 'SIM'
            if pd.notnull(suspensao) and suspensao > competencia_fim:
                return 'SIM'
            return 'NÃO'
        return 'NÃO'
    merged_df['Apto a Faturar'] = merged_df.apply(verifica_faturamento, axis=1)
    return merged_df

def desenhar_tabela(c, y, titulo, contagem, total, total_faturar):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, titulo)
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Status ICCID's")
    c.drawRightString(400, y, "Quantidade")
    y -= 15
    c.setFont("Helvetica", 10)
    for status, quantidade in contagem.items():
        c.drawString(50, y, str(status))
        c.drawRightString(400, y, f"{quantidade:,}".replace(",", "."))
        y -= 15
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Total de ICCID's")
    c.drawRightString(400, y, f"{total:,}".replace(",", "."))
    y -= 15
    c.drawString(50, y, "Valor pacote de dados por ICCID")
    c.drawRightString(400, y, "R$ 21,51")
    y -= 15
    c.drawString(50, y, "Total a Faturar")
    c.drawRightString(400, y, f"R$ {total_faturar:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 30
    return y

def gerar_pdf_resumo(merged_df, fornecedor, mes_referencia):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    try:
        logo = ImageReader("logo.png")
        c.drawImage(logo, x=50, y=height - 100, width=80, height=40, preserveAspectRatio=True)
    except:
        pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y - 130, "Relatório de Análise de Faturamento de Chips")
    c.setLineWidth(1)
    c.line(50, y - 135, width - 50, y - 135)

    c.setFont("Helvetica", 12)
    y -= 160
    c.drawString(50, y, f"Fornecedor: {fornecedor}")
    y -= 20
    c.drawString(50, y, f"Mês de Referência: {mes_referencia}")
    y -= 30
    c.setLineWidth(0.5)
    c.line(50, y, width - 50, y)
    y -= 20

    contagem_original = merged_df['STATUS'].value_counts()
    total_original = contagem_original.sum()
    total_faturar_original = total_original * VALOR_UNITARIO
    y = desenhar_tabela(c, y, "Tabela 1: Situação Original - Base Fornecedor", contagem_original, total_original, total_faturar_original)

    revisado = merged_df[merged_df['Apto a Faturar'] == 'SIM']
    contagem_revisada = revisado['STATUS'].value_counts()
    total_revisado = contagem_revisada.sum()
    total_faturar_revisado = total_revisado * VALOR_UNITARIO
    y = desenhar_tabela(c, y, "Tabela 2: Situação Revisada - Após Análise", contagem_revisada, total_revisado, total_faturar_revisado)

    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora_br = datetime.now(fuso_br)
    data_hora = agora_br.strftime('%d/%m/%Y %H:%M')

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, f"Gerado em: {data_hora}")

    c.save()
    buffer.seek(0)
    return buffer

st.title("Analisador de Faturamento de Chips")

fornecedor = st.selectbox("Fornecedor", options=["B2", "DRY", "NUH"])
mes_referencia = st.text_input("Mês de Referência da Análise")

fornecedor_file = st.file_uploader("Base do Fornecedor (.xlsx)", type="xlsx")
interna_file = st.file_uploader("Base Interna (.xlsx)", type="xlsx")
aquisicao_file = st.file_uploader("Lista de Aquisição (.xlsx)", type="xlsx")
teste_file = st.file_uploader("Lista de Chips de Teste (.xlsx)", type="xlsx")

if st.button("Processar"):
    if None in (fornecedor_file, interna_file, aquisicao_file, teste_file):
        st.error("Por favor, envie todas as planilhas.")
    else:
        fornecedor_df = pd.read_excel(fornecedor_file)
        interna_df = pd.read_excel(interna_file, header=1)
        lista_aquisicao_df = pd.read_excel(aquisicao_file)
        chips_teste_df = pd.read_excel(teste_file, sheet_name='CHIP TESTES')
        merged_df = processar_bases(fornecedor_df, interna_df, lista_aquisicao_df, chips_teste_df)
        st.session_state['merged_df'] = merged_df
        st.session_state['fornecedor'] = fornecedor
        st.session_state['mes_referencia'] = mes_referencia
        st.success("Processamento concluído com sucesso. Agora você pode baixar os relatórios.")

if 'merged_df' in st.session_state:
    merged_df = st.session_state['merged_df']
    fornecedor = st.session_state.get('fornecedor', '')
    mes_referencia = st.session_state.get('mes_referencia', '')
    excel_buffer = BytesIO()
    merged_df.to_excel(excel_buffer, index=False)
    st.download_button("Baixar Relatório Detalhado (Excel)", excel_buffer.getvalue(), "relatorio_faturamento.xlsx")
    pdf_buffer = gerar_pdf_resumo(merged_df, fornecedor, mes_referencia)
    st.download_button("Baixar Resumo (PDF)", pdf_buffer.getvalue(), "resumo_faturamento.pdf")
