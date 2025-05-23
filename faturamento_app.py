
import streamlit as st
import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader

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

def gerar_pdf_resumo(merged_df, logo_path):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    if logo_path:
        logo = ImageReader(logo_path)
        c.drawImage(logo, 50, height - 100, width=100, preserveAspectRatio=True)
    total_fornecedor = len(merged_df)
    total_aptos = merged_df['Apto a Faturar'].value_counts().get('SIM', 0)
    total_excluidos = total_fornecedor - total_aptos
    excluidos_status = merged_df[merged_df['Apto a Faturar'] == 'NÃO']['STATUS'].value_counts()
    c.drawString(50, height - 120, "Resumo da Análise de Faturamento")
    c.drawString(50, height - 140, f"Total de chips recebidos: {total_fornecedor}")
    c.drawString(50, height - 160, f"Total de chips aptos: {total_aptos}")
    c.drawString(50, height - 180, f"Total de chips excluídos: {total_excluidos}")
    c.drawString(50, height - 200, "Status dos chips excluídos:")
    y = height - 220
    for status, count in excluidos_status.items():
        c.drawString(70, y, f"{status}: {count}")
        y -= 20
    c.save()
    buffer.seek(0)
    return buffer

st.title("Analisador de Faturamento de Chips")
fornecedor_file = st.file_uploader("Base do Fornecedor (.xlsx)", type="xlsx")
interna_file = st.file_uploader("Base Interna (.xlsx)", type="xlsx")
aquisicao_file = st.file_uploader("Lista de Aquisição (.xlsx)", type="xlsx")
teste_file = st.file_uploader("Lista de Chips de Teste (.xlsx)", type="xlsx")
logo_file = st.file_uploader("Logo (.png ou .jpg)", type=["png", "jpg", "jpeg"])

if st.button("Processar"):
    if None in (fornecedor_file, interna_file, aquisicao_file, teste_file):
        st.error("Por favor, envie todas as planilhas.")
    else:
        fornecedor_df = pd.read_excel(fornecedor_file)
        interna_df = pd.read_excel(interna_file, header=1)
        lista_aquisicao_df = pd.read_excel(aquisicao_file)
        chips_teste_df = pd.read_excel(teste_file, sheet_name='CHIP TESTES')
        merged_df = processar_bases(fornecedor_df, interna_df, lista_aquisicao_df, chips_teste_df)
        excel_buffer = BytesIO()
        merged_df.to_excel(excel_buffer, index=False)
        st.download_button("Baixar Relatório Detalhado (Excel)", excel_buffer.getvalue(), "relatorio_faturamento.xlsx")
        pdf_buffer = gerar_pdf_resumo(merged_df, logo_file)
        st.download_button("Baixar Resumo (PDF)", pdf_buffer.getvalue(), "resumo_faturamento.pdf")
        st.success("Processamento concluído com sucesso.")
