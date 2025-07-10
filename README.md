# 📊 Simulador de Investimentos - CDI x LCI x IPCA+

Este projeto é um **simulador de investimentos** construído em **Python com Streamlit**, permitindo comparar:

✅ CDI (103% CDI)  
✅ LCI (91% CDI, isento de IR)  
✅ IPCA+ (IPCA + juros reais anuais configuráveis)

Com **controle de aportes mensais, projeções de saldo mês a mês, gráfico de evolução e download de planilha Excel automática.**

Inclui também **cálculo de IR regressivo automático (22,5%, 20%, 17,5%, 15%) conforme o prazo do investimento, aportes mensais e reinvestimento automático dos juros**.

---

## 🚀 Funcionalidades

- Interface intuitiva via **Streamlit**
- Ajuste de:
  - Valor inicial
  - Aporte mensal
  - Prazo em anos
  - Spread IPCA+
  - IR flexível conforme prazo (regressivo) para CDI e IPCA+
- Gráfico comparativo de saldo ao longo do tempo
- Tabelas mensais detalhadas para cada tipo de investimento
- Resumo de rendimento total, aportes e saldo final
- **Download em Excel (.xlsx)** para análises adicionais

---
## 🛠️ Como rodar na WEB
  **Acessar o link abaixo**
 - https://simuladorinvestimentos.streamlit.app/

## 🛠️ Como rodar localmente

1️⃣ Clone o repositório:
```bash
git clone https://github.com/seuusuario/simulador-investimentos.git
cd simulador-investimentos
