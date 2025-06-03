# Analisador de Faturamento de Chips

Aplicação web desenvolvida em **Streamlit** para realizar a análise automatizada de faturamento de chips, comparando bases de dados, gerando relatórios detalhados em **Excel** e **resumos em PDF** personalizados.

---

## ✅ **Funcionalidades**

- Upload das bases:  
  ✅ Base do Fornecedor  
  ✅ Base Interna  
  ✅ Lista de Aquisição  
  ✅ Lista de Chips de Teste  
  ✅ Logo institucional (opcional)

- Preenchimento prévio de:  
  ✅ **Fornecedor** → lista suspensa: A, B e C
  ✅ **Mês de Referência da Análise** → campo de texto

- Processamento com aplicação automática de regras de faturamento.  
- Geração de:  
  ✅ **Relatório Detalhado (Excel)**  
  ✅ **Resumo da Análise (PDF)** → com Fornecedor e Mês de Referência incluídos.  

- Sistema otimizado:  
  ✅ Processa **uma vez** → permite múltiplos downloads sem necessidade de repetir.

---

## ✅ **Como usar**

1. Acesse a aplicação no **Streamlit Cloud**:  
   ➡️ `https://SEU_LINK.streamlit.app`

2. Preencha:  
   - Fornecedor → selecione entre: **B2, DRY ou NUH**  
   - Mês de Referência → ex.: `04/2025`

3. Faça o upload de:  
   - Base do Fornecedor (.xlsx)  
   - Base Interna (.xlsx)  
   - Lista de Aquisição (.xlsx)  
   - Lista de Chips de Teste (.xlsx)  
   - Logo (.png ou .jpg) → opcional  

4. Clique em **“Processar”**.

5. Após processamento, baixe:  
   - ✅ Relatório Detalhado (Excel)  
   - ✅ Resumo da Análise (PDF)

---

## ✅ **Tecnologias Utilizadas**

- Python  
- Streamlit  
- Pandas  
- ReportLab  

---

## ✅ **Configuração Local (opcional)**

1. Clone o repositório:  
   ```bash
   git clone https://github.com/SEU_USUARIO/analise_faturamento_chips.git
   cd analise_faturamento_chips
