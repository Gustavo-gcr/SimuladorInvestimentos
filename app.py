import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from io import BytesIO

st.set_page_config(page_title="Simulador de Investimentos", layout="wide")

@st.cache_data(show_spinner=False)
def get_cdi():
    try:
        data = requests.get(
            'https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1?formato=json'
        ).json()[0]
        return float(data['valor']) / 100  # CDI diário em decimal
    except:
        st.warning("Erro ao buscar CDI, usando 0.39% dia (≈10,65% a.a.) padrão.")
        return 0.0039

@st.cache_data(show_spinner=False)
def get_ipca():
    try:
        data = requests.get(
            'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json'
        ).json()[0]
        return float(data['valor']) / 100  # IPCA mensal em decimal
    except:
        st.warning("Erro ao buscar IPCA, usando 0.40% mês padrão.")
        return 0.0040

def format_brl(x):
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_ir_regressivo(prazo_dias):
    """Retorna a alíquota de IR regressivo de acordo com o prazo."""
    if prazo_dias <= 180:
        return 22.5
    elif prazo_dias <= 360:
        return 20.0
    elif prazo_dias <= 720:
        return 17.5
    else:
        return 15.0

def simular_investimento(valor_inicial, aporte_mensal, meses, tipo, ir_rate=0.0, spread_ipca=10.0):
    cdi_diario = get_cdi()
    cdi_anual = (1 + cdi_diario) ** 252 - 1
    ipca_mensal = get_ipca()

    if tipo == 'CDI':
        taxa_bruta_anual = cdi_anual * 1.03
        taxa_liquida_anual = taxa_bruta_anual * (1 - ir_rate / 100)
        taxa_mensal = (1 + taxa_liquida_anual) ** (1 / 12) - 1
    elif tipo == 'LCI':
        taxa_bruta_anual = cdi_anual * 0.91
        taxa_mensal = (1 + taxa_bruta_anual) ** (1 / 12) - 1
    elif tipo == 'IPCA+':
        taxa_juros_real_mensal = (spread_ipca / 100) / 12
        taxa_mensal = (1 + ipca_mensal) * (1 + taxa_juros_real_mensal) - 1
    else:
        raise ValueError("Tipo inválido")

    saldo_inicial = valor_inicial
    aportes = []
    historico = []

    for mes in range(1, meses + 1):
        saldo_inicial *= (1 + taxa_mensal)

        if aporte_mensal > 0:
            aportes.append({'valor': aporte_mensal})

        saldo_aportes = 0
        for aporte in aportes:
            aporte['valor'] *= (1 + taxa_mensal)
            saldo_aportes += aporte['valor']

        saldo_total = saldo_inicial + saldo_aportes

        historico.append({
            'Mês': mes,
            'Data': (datetime.today() + pd.DateOffset(months=mes)).strftime('%m/%Y'),
            'Saldo (R$)': round(saldo_total, 2)
        })

    total_aportes = aporte_mensal * meses

    # Aplicar IR para IPCA+ só depois do loop
    if tipo == 'IPCA+':
        inflacao_acumulada = (1 + ipca_mensal) ** meses - 1
        total_investido = valor_inicial + total_aportes
        ganho_bruto = (saldo_total / total_investido) - 1
        ganho_real = (1 + ganho_bruto) / (1 + inflacao_acumulada) - 1
        ir_valor = ganho_real * (ir_rate / 100) * total_investido
        saldo_final_liquido = saldo_total - ir_valor
        rendimento_valor_inicial = saldo_final_liquido - valor_inicial - total_aportes
        saldo_final = saldo_final_liquido
    else:
        rendimento_valor_inicial = saldo_inicial - valor_inicial
        saldo_final = saldo_total

    rendimento_aportes = saldo_aportes - total_aportes
    saldo_final = valor_inicial + total_aportes + rendimento_valor_inicial + rendimento_aportes
    df = pd.DataFrame(historico)
    return df, rendimento_valor_inicial, rendimento_aportes, saldo_final




# --- Interface
st.title("📊 Simulador de Investimentos Detalhado: CDI x LCI x IPCA+")

with st.sidebar:
    st.header("🔧 Parâmetros")
    valor_inicial = st.number_input("Valor Inicial (R$)", min_value=0.0, value=10000.0, step=100.0, format="%.2f")
    aporte_mensal = st.number_input("Aporte Mensal (R$)", min_value=0.0, value=1000.0, step=50.0, format="%.2f")
    anos = st.slider("Prazo (anos)", min_value=1, max_value=30, value=10)
    meses = anos * 12
    ir_options = [22.5, 17.5, 15.0, 12.5]
    ir_cdi = st.selectbox("Alíquota IR CDI (%)", ir_options, index=1)
    ir_ipca = st.selectbox("Alíquota IR IPCA+ (%)", ir_options, index=2)
    spread_ipca = st.number_input("Spread IPCA+ (% a.a.)", min_value=0.0, value=10.0, step=0.5)

# Simulações
cd_df, cd_rvi, cd_ra, cd_sf = simular_investimento(valor_inicial, aporte_mensal, meses, 'CDI', ir_rate=ir_cdi)
lc_df, lc_rvi, lc_ra, lc_sf = simular_investimento(valor_inicial, aporte_mensal, meses, 'LCI')
ip_df, ip_rvi, ip_ra, ip_sf = simular_investimento(valor_inicial, aporte_mensal, meses, 'IPCA+', ir_rate=ir_ipca, spread_ipca=spread_ipca)

# --- Gráfico comparativo
st.subheader("📊 Evolução Mensal")
chart_data = pd.DataFrame({
    f'CDI 103% (IR {ir_cdi}%)': cd_df['Saldo (R$)'],
    'LCI 91% (isento)': lc_df['Saldo (R$)'],
    f'IPCA+{spread_ipca:.1f}% (IR {ir_ipca}%)': ip_df['Saldo (R$)']
})
st.line_chart(chart_data)

# --- Tabelas detalhadas
st.subheader("📅 Tabelas Mensais Detalhadas")
tabs = st.tabs(["CDI", "LCI", "IPCA+"])
with tabs[0]: st.dataframe(cd_df)
with tabs[1]: st.dataframe(lc_df)
with tabs[2]: st.dataframe(ip_df)

# --- Resumo detalhado
resumo = pd.DataFrame({
    'Investimento': [f'CDI 103%', 'LCI 91%', f'IPCA+{spread_ipca:.1f}%'],
    'IR (%)': [ir_cdi, 0.0, ir_ipca],
    'Valor Inicial (R$)': [valor_inicial] * 3,
    'Total Aportes (R$)': [aporte_mensal * meses] * 3,
    'Total Aportado (R$)': [valor_inicial + aporte_mensal * meses] * 3,
    'Rendimento Total (R$)': [cd_rvi + cd_ra, lc_rvi + lc_ra, ip_rvi + ip_ra],
    'Saldo Final (R$)': [cd_sf, lc_sf, ip_sf]
})

for col in ['Valor Inicial (R$)', 'Total Aportes (R$)', 'Total Aportado (R$)',
           'Rendimento Total (R$)', 'Saldo Final (R$)']:
    resumo[col] = resumo[col].apply(format_brl)

st.subheader("📈 Resumo de Aportes e Rendimentos Detalhado")
st.dataframe(resumo)

# --- Download Excel
def to_excel(dfs, names):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df, name in zip(dfs, names):
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

excel_data = to_excel(
    [cd_df, lc_df, ip_df],
    ['CDI_103%', 'LCI_91%', f'IPCA+{spread_ipca:.1f}%']
)

st.subheader("⬇️ Baixar Planilha Excel (.xlsx)")
st.download_button(
    "📥 Baixar Planilha Excel",
    data=excel_data,
    file_name="simulador_investimentos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
