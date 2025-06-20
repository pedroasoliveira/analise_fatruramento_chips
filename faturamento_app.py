import streamlit as st
st.set_page_config(layout="centered")

import pandas as pd
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from datetime import datetime
import pytz

VALOR_UNITARIO = 21.51

def gerar_motivo(row, competencia_fim):
    status = row['STATUS']
    ativacao = row['DATA DE ATIVAÇÃO']
    cancelamento = row['DATA DE CANCELAMENTO']
    suspensao = row['DATA DE SUSPENSÃO']
    constabase = row['CONSTA BASE B2']
    lista_aquisicao = row['LISTA DE AQUISIÇÃO RNP']
    chip_teste = row['CHIP TESTE']

    if chip_teste == 'SIM':
        if status == 'EXTRAVIADO':
            return 'Status inválido - Extraviado'
        if status == 'INATIVO':
            return ''

    if status == 'INATIVO':
        return 'Status inválido - Inativo'
    if status == 'EXTRAVIADO':
        return 'Status inválido - Extraviado'
    if status == 'ATIVO':
        return 'Ativação fora do mês competência'
    if status == 'CANCELADO':
        return 'Cancelamento fora do mês competência'
    if status == 'SUSPENSO':
        return 'Suspensão fora das regras'
    if constabase == 'NÃO' and lista_aquisicao == 'NÃO':
        return 'Fora da base B2 e fora da lista de aquisição RNP'
    return 'Status válido: não identificado'

def processar_bases(fornecedor_df, interna_df, lista_aquisicao_df, chips_teste_df, mes_referencia):
    if not mes_referencia:
        st.error("Mês de Referência não informado. Use o formato YYYY-MM, exemplo: 2025-05.")
        return pd.DataFrame()
    try:
        competencia_fim = pd.to_datetime(mes_referencia + '-01') + pd.offsets.MonthEnd(0)
    except Exception:
        st.error("Formato inválido para o Mês de Referência. Use o formato YYYY-MM, exemplo: 2025-05.")
        return pd.DataFrame()
        
    fornecedor_df['ICCID'] = fornecedor_df['Iccid'].astype(str).str.strip().str.zfill(19)
    interna_df.columns = interna_df.columns.str.strip()
    interna_df['ICCID'] = interna_df['ICCID'].astype(str).str.strip().str.zfill(19)
    lista_aquisicao_df['iccid'] = lista_aquisicao_df['iccid'].astype(str).str.strip()
    chips_teste_df['ICCID'] = chips_teste_df['ICCID'].astype(str).str.strip()
    
    merged_df = pd.merge(fornecedor_df[['ICCID']], interna_df, on='ICCID', how='left')
    merged_df['STATUS'] = merged_df['STATUS'].fillna('NÃO CONSTA NA B2')
    merged_df['CONSTA BASE B2'] = merged_df['STATUS'].apply(lambda x: 'SIM' if x != 'NÃO CONSTA NA B2' else 'NÃO')
    merged_df['LISTA DE AQUISIÇÃO RNP'] = merged_df['ICCID'].isin(lista_aquisicao_df['iccid']).map({True: 'SIM', False: 'NÃO'})
    merged_df['CHIP TESTE'] = merged_df['ICCID'].isin(chips_teste_df['ICCID']).map({True: 'SIM', False: 'NÃO'})
    
    def verifica_faturamento(row):
        status = row['STATUS']
        ativacao = row['DATA DE ATIVAÇÃO']
        cancelamento = row['DATA DE CANCELAMENTO']
        suspensao = row['DATA DE SUSPENSÃO']
        chip_teste = row['CHIP TESTE']
        constabase = row['CONSTA BASE B2']
        lista_aquisicao = row['LISTA DE AQUISIÇÃO RNP']

        if chip_teste == 'SIM':
            if status == 'EXTRAVIADO':
                return 'NÃO'
            if status == 'INATIVO':
                return 'SIM'
            if status == 'ATIVO':
                return 'SIM' if pd.notnull(ativacao) and ativacao <= competencia_fim else 'NÃO'
            if status == 'CANCELADO':
                return 'SIM' if pd.notnull(cancelamento) and cancelamento.month == competencia_fim.month and cancelamento.year == competencia_fim.year else 'NÃO'
            if status == 'SUSPENSO':
                if pd.notnull(suspensao) and pd.notnull(ativacao):
                    fidelidade_limite = ativacao + pd.Timedelta(days=90)
                    if suspensao.month == competencia_fim.month and suspensao.year == competencia_fim.year:
                        return 'SIM'
                    if suspensao <= fidelidade_limite and fidelidade_limite >= competencia_fim:
                        return 'SIM'
                return 'NÃO'
            if constabase == 'NÃO':
                return 'SIM' if lista_aquisicao == 'SIM' else 'NÃO'
            return 'NÃO'

        if constabase == 'NÃO' and lista_aquisicao == 'NÃO':
            return 'NÃO'
        if status in ['EXTRAVIADO', 'INATIVO']:
            return 'NÃO'
        if status == 'ATIVO':
            return 'SIM' if pd.notnull(ativacao) and ativacao <= competencia_fim else 'NÃO'
        if status == 'CANCELADO':
            return 'SIM' if pd.notnull(cancelamento) and cancelamento.month == competencia_fim.month and cancelamento.year == competencia_fim.year else 'NÃO'
        if status == 'SUSPENSO':
            if pd.notnull(suspensao) and pd.notnull(ativacao):
                fidelidade_limite = ativacao + pd.Timedelta(days=90)
                if suspensao.month == competencia_fim.month and suspensao.year == competencia_fim.year:
                    return 'SIM'
                if suspensao <= fidelidade_limite and fidelidade_limite >= competencia_fim:
                    return 'SIM'
            return 'NÃO'
        return 'NÃO'

    for col in ['DATA DE ATIVAÇÃO', 'DATA DE CANCELAMENTO', 'DATA DE SUSPENSÃO']:
        merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce').dt.strftime('%d/%m/%Y')

    merged_df['DATA DE ATIVAÇÃO'] = pd.to_datetime(merged_df['DATA DE ATIVAÇÃO'], errors='coerce')
    merged_df['DATA DE CANCELAMENTO'] = pd.to_datetime(merged_df['DATA DE CANCELAMENTO'], errors='coerce')
    merged_df['DATA DE SUSPENSÃO'] = pd.to_datetime(merged_df['DATA DE SUSPENSÃO'], errors='coerce')

    merged_df['Apto a Faturar'] = merged_df.apply(verifica_faturamento, axis=1)
    merged_df['Motivo Não Faturamento'] = merged_df.apply(
        lambda x: '' if x['Apto a Faturar'] == 'SIM' else gerar_motivo(x, competencia_fim), axis=1)

    limite_fidelidade = merged_df['DATA DE ATIVAÇÃO'] + pd.Timedelta(days=90)
    merged_df['DATA LIMITE FIDELIDADE (90 DIAS APÓS ATIVAÇÃO)'] = ''
    merged_df.loc[merged_df['STATUS'] == 'SUSPENSO', 'DATA LIMITE FIDELIDADE (90 DIAS APÓS ATIVAÇÃO)'] = limite_fidelidade[
        merged_df['STATUS'] == 'SUSPENSO'].dt.date
    
    # Reorganiza as colunas para posicionar a coluna de fidelidade após 'DATA DE SUSPENSÃO'
    cols = list(merged_df.columns)
    if 'DATA DE SUSPENSÃO' in cols and 'DATA LIMITE FIDELIDADE (90 DIAS APÓS ATIVAÇÃO)' in cols:
        idx = cols.index('DATA DE SUSPENSÃO') + 1
        cols.insert(idx, cols.pop(cols.index('DATA LIMITE FIDELIDADE (90 DIAS APÓS ATIVAÇÃO)')))
        merged_df = merged_df[cols]

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

def desenhar_nao_faturados(c, y, df):
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Tabela 2.1: Chips Não Aptos a Faturamento")
    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Status")
    c.drawString(200, y, "Motivo")
    c.drawRightString(400, y, "Qtde de Chips")
    y -= 15
    c.setFont("Helvetica", 9)

    resumo = df[df['Apto a Faturar'] == 'NÃO'].groupby(['STATUS', 'Motivo Não Faturamento']).size().reset_index(name='quantidade')
    total_nao_apto = 0

    for _, row in resumo.iterrows():
        c.drawString(50, y, str(row['STATUS']))
        c.drawString(200, y, str(row['Motivo Não Faturamento'])[:40])
        c.drawRightString(400, y, f"{row['quantidade']:,}".replace(",", "."))
        total_nao_apto += row['quantidade']
        y -= 15

    # Linha total
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Total de ICCID's Não Aptos")
    c.drawRightString(400, y, f"{total_nao_apto:,}".replace(",", "."))
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
    
    nao_apto = merged_df[merged_df['Apto a Faturar'] == 'NÃO']
    y = desenhar_nao_faturados(c, y, merged_df)
    
    fuso_br = pytz.timezone('America/Sao_Paulo')
    agora_br = datetime.now(fuso_br)
    data_hora = agora_br.strftime('%d/%m/%Y %H:%M')
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, y, f"Gerado em: {data_hora}")

    c.save()
    buffer.seek(0)
    return buffer

st.title("Analisador de Faturamento de Chips")

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

fornecedor = st.selectbox("Fornecedor", options=["A", "B", "C"])
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
        merged_df = processar_bases(fornecedor_df, interna_df, lista_aquisicao_df, chips_teste_df, mes_referencia)
        st.session_state['merged_df'] = merged_df
        st.session_state['fornecedor'] = fornecedor
        st.session_state['mes_referencia'] = mes_referencia
        st.success("Processamento concluído com sucesso. Agora você pode baixar os relatórios.")

if 'merged_df' in st.session_state:
    merged_df = st.session_state['merged_df']
    fornecedor = st.session_state.get('fornecedor', '')
    mes_referencia = st.session_state.get('mes_referencia', '')
   
    # ✅ Formatando as datas no formato dd/mm/yyyy
    colunas_data = ['DATA DE ATIVAÇÃO', 'DATA DE CANCELAMENTO', 'DATA DE SUSPENSÃO']
    for coluna in colunas_data:
        if coluna in merged_df.columns:
            merged_df[coluna] = pd.to_datetime(merged_df[coluna], errors='coerce').dt.strftime('%d/%m/%Y')

        # Formatar colunas de data para exibir apenas a data (sem hora)
    for col in ['DATA DE CANCELAMENTO', 'DATA DE SUSPENSÃO', 'DATA DE ATIVAÇÃO']:
        if col in merged_df.columns:
            merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce').dt.date
        
    # ✅ Exportando para Excel   
    excel_buffer = BytesIO()
    merged_df.to_excel(excel_buffer, index=False)
    st.download_button("Baixar Relatório Detalhado (Excel)", excel_buffer.getvalue(), "relatorio_faturamento.xlsx")

    # Formatar colunas de data para exibir apenas a data (sem hora)
    for col in ['DATA DE CANCELAMENTO', 'DATA DE SUSPENSÃO', 'DATA DE ATIVAÇÃO']:
        if col in merged_df.columns:
            merged_df[col] = pd.to_datetime(merged_df[col], errors='coerce').dt.date

    # ✅ Exportando para PDF
    pdf_buffer = gerar_pdf_resumo(merged_df, fornecedor, mes_referencia)
    st.download_button("Baixar Resumo (PDF)", pdf_buffer.getvalue(), "resumo_faturamento.pdf")
