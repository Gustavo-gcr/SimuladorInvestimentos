import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from io import BytesIO
import numpy as np

# Configura a página do Streamlit
st.set_page_config(page_title="Simulador de Investimentos", layout="wide")

# --- Funções de busca de dados de Renda Fixa (CDI e IPCA) ---
@st.cache_data(show_spinner=False)
def get_cdi():
    try:
        data = requests.get(
            'https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1?formato=json'
        ).json()[0]
        return float(data['valor']) / 100
    except:
        return 0.0039

@st.cache_data(show_spinner=False)
def get_ipca():
    try:
        data = requests.get(
            'https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json'
        ).json()[0]
        return float(data['valor']) / 100
    except:
        return 0.0040

# --- Funções para Criptomoedas ---
@st.cache_data(show_spinner=False)
def get_crypto_current_price(crypto_ids):
    """
    Busca o preço atual das criptomoedas usando o endpoint simple/price.
    """
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(crypto_ids),
        "vs_currencies": "brl"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar preços atuais: {e}")
        return {}

@st.cache_data(show_spinner=False)
def get_crypto_monthly_returns(crypto_id):
    """
    Busca o histórico de preços de uma criptomoeda dos últimos 6 meses (180 dias)
    e calcula a média dos retornos mensais para simulação.
    """
    url = f"https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart"
    params = {
        "vs_currency": "brl",
        "days": 180
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices_df = pd.DataFrame(data['prices'], columns=['timestamp', 'price'])
        prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'], unit='ms')
        prices_df.set_index('timestamp', inplace=True)
        
        monthly_prices = prices_df['price'].resample('M').last()
        monthly_returns = monthly_prices.pct_change().dropna().tolist()
        
        if not monthly_returns:
            raise ValueError("Dados insuficientes para calcular retornos mensais.")

        return monthly_returns
    except (requests.exceptions.RequestException, ValueError) as e:
        st.error(f"Erro ao buscar dados de '{crypto_id}': {e}")
        return [0.05, -0.02, 0.1, -0.03, 0.07, -0.01]

fixed_crypto_returns = {
    'bitcoin': [0.03, 0.02, -0.01, 0.05, 0.03, -0.02, 0.04, 0.01, -0.03, 0.06, 0.03, 0.01, 0.02, -0.01, 0.03],
    'ethereum': [0.04, 0.03, -0.03, 0.06, 0.02, -0.04, 0.05, 0.02, -0.05, 0.07, 0.04, 0.02, 0.03, -0.02, 0.04],
    'solana': [0.05, 0.01, -0.05, 0.08, 0.01, -0.07, 0.07, 0.03, -0.08, 0.09, 0.05, 0.03, 0.04, -0.03, 0.06]
}
# --- Funções de formatação ---
def format_brl(x):
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")

# --- Função de simulação para Renda Fixa ---
def simular_renda_fixa(valor_inicial, aporte_mensal, meses, tipo, ir_rate=0.0, spread_ipca=10.0):
    cdi_diario = get_cdi()
    cdi_anual = (1 + cdi_diario) ** 252 - 1
    ipca_mensal = get_ipca()
    
    taxa_mensal = 0
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

    saldo_inicial = valor_inicial
    total_aportes = 0
    historico = []

    for mes in range(1, meses + 1):
        saldo_inicial = saldo_inicial * (1 + taxa_mensal) + aporte_mensal
        total_aportes += aporte_mensal

        historico.append({
            'Mês': mes,
            'Data': (datetime.today() + pd.DateOffset(months=mes)).strftime('%m/%Y'),
            'Saldo (R$)': round(saldo_inicial, 2)
        })

    saldo_final = historico[-1]['Saldo (R$)'] if historico else valor_inicial
    total_aportado = valor_inicial + total_aportes
    rendimento_total = saldo_final - total_aportado
    
    df = pd.DataFrame(historico)
    return df, rendimento_total, saldo_final

# --- Função de simulação para Criptomoedas com modelo realista (dados fixos) ---
def simular_cripto(valor_inicial, aporte_mensal, meses, crypto_id_api):
    monthly_returns_crypto = fixed_crypto_returns.get(crypto_id_api, [0.015, -0.01, 0.03])
    
    saldo_inicial = valor_inicial
    total_aportes = 0
    historico = []
    
    for mes in range(1, meses + 1):
        avg_monthly_return = np.mean(monthly_returns_crypto)
        std_dev_returns = np.std(monthly_returns_crypto)
        
        taxa_mensal = np.random.normal(avg_monthly_return, std_dev_returns)
        
        saldo_inicial = saldo_inicial * (1 + taxa_mensal) + aporte_mensal
        total_aportes += aporte_mensal

        historico.append({
            'Mês': mes,
            'Data': (datetime.today() + pd.DateOffset(months=mes)).strftime('%m/%Y'),
            'Saldo (R$)': round(saldo_inicial, 2)
        })

    saldo_final = historico[-1]['Saldo (R$)'] if historico else valor_inicial
    total_aportado = valor_inicial + total_aportes
    rendimento_total = saldo_final - total_aportado
    
    df = pd.DataFrame(historico)
    return df, rendimento_total, saldo_final

# --- Interface ---
st.title("📊 Simulador de Investimentos Detalhado: Renda Fixa vs. Criptos")
st.markdown("---")

# Seção de valores atuais das criptomoedas (usando valores padrão para evitar o erro)
st.subheader("💰 Cotações Atuais (valores aproximados)")
crypto_prices = get_crypto_current_price(['bitcoin', 'ethereum', 'solana'])
if crypto_prices:
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Bitcoin (BTC)", f"R$ {format_brl(crypto_prices.get('bitcoin', {}).get('brl', 0))}")
    with col2:
        st.metric("Ethereum (ETH)", f"R$ {format_brl(crypto_prices.get('ethereum', {}).get('brl', 0))}")
    with col3:
        st.metric("Solana (SOL)", f"R$ {format_brl(crypto_prices.get('solana', {}).get('brl', 0))}")

st.markdown("---")

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

# --- Simulações ---
cd_df, cd_rendimento, cd_sf = simular_renda_fixa(valor_inicial, aporte_mensal, meses, 'CDI', ir_rate=ir_cdi)
lc_df, lc_rendimento, lc_sf = simular_renda_fixa(valor_inicial, aporte_mensal, meses, 'LCI')
ip_df, ip_rendimento, ip_sf = simular_renda_fixa(valor_inicial, aporte_mensal, meses, 'IPCA+', ir_rate=ir_ipca, spread_ipca=spread_ipca)

# Cripto com volatilidade diferenciada, usando dados fixos
btc_df, btc_rendimento, btc_sf = simular_cripto(valor_inicial, aporte_mensal, meses, 'bitcoin')
eth_df, eth_rendimento, eth_sf = simular_cripto(valor_inicial, aporte_mensal, meses, 'ethereum')
sol_df, sol_rendimento, sol_sf = simular_cripto(valor_inicial, aporte_mensal, meses, 'solana')

# --- Gráfico comparativo com controle de exibição ---
display_option = st.radio(
    "Escolha a categoria para visualizar no gráfico e no resumo:",
    ("Renda Fixa", "Cripto")
)
st.subheader("📊 Evolução Mensal- Simulação")
st.subheader( "(Em investimento nunca teremos algo concreto e sim variavel)")
chart_data = pd.DataFrame()

if display_option == "Renda Fixa":
    chart_data[f'CDI 103% (IR {ir_cdi}%)'] = cd_df['Saldo (R$)']
    chart_data['LCI 91% (isento)'] = lc_df['Saldo (R$)']
    chart_data[f'IPCA+{spread_ipca:.1f}% (IR {ir_ipca}%)'] = ip_df['Saldo (R$)']
elif display_option == "Cripto":
    chart_data['Bitcoin (simulado)'] = btc_df['Saldo (R$)']
    chart_data['Ethereum (simulado)'] = eth_df['Saldo (R$)']
    chart_data['Solana (simulado)'] = sol_df['Saldo (R$)']

if not chart_data.empty:
    st.line_chart(chart_data)
else:
    st.warning("Selecione uma opção para visualizar o gráfico.")

# --- Tabelas detalhadas ---
st.subheader("📅 Tabelas Mensais Detalhadas")
tabs = st.tabs(["CDI", "LCI", "IPCA+", "Bitcoin", "Ethereum", "Solana"])
with tabs[0]: st.dataframe(cd_df)
with tabs[1]: st.dataframe(lc_df)
with tabs[2]: st.dataframe(ip_df)
with tabs[3]: st.dataframe(btc_df)
with tabs[4]: st.dataframe(eth_df)
with tabs[5]: st.dataframe(sol_df)

# --- Resumo detalhado (AGORA FILTRADO) ---
st.subheader("📈 Resumo de Aportes e Rendimentos Detalhado")

if display_option == "Renda Fixa":
    resumo = pd.DataFrame({
        'Investimento': ['CDI 103%', 'LCI 91%', f'IPCA+{spread_ipca:.1f}%'],
        'IR (%)': [ir_cdi, 0.0, ir_ipca],
        'Valor Inicial (R$)': [valor_inicial] * 3,
        'Total Aportes (R$)': [aporte_mensal * meses] * 3,
        'Total Aportado (R$)': [valor_inicial + aporte_mensal * meses] * 3,
        'Rendimento Total (R$)': [cd_rendimento, lc_rendimento, ip_rendimento],
        'Saldo Final (R$)': [cd_sf, lc_sf, ip_sf]
    })
elif display_option == "Cripto":
    resumo = pd.DataFrame({
        'Investimento': ['Bitcoin', 'Ethereum', 'Solana'],
        'IR (%)': ['N/A', 'N/A', 'N/A'],
        'Valor Inicial (R$)': [valor_inicial] * 3,
        'Total Aportes (R$)': [aporte_mensal * meses] * 3,
        'Total Aportado (R$)': [valor_inicial + aporte_mensal * meses] * 3,
        'Rendimento Total (R$)': [btc_rendimento, eth_rendimento, sol_rendimento],
        'Saldo Final (R$)': [btc_sf, eth_sf, sol_sf]
    })

for col in ['Valor Inicial (R$)', 'Total Aportes (R$)', 'Total Aportado (R$)',
            'Rendimento Total (R$)', 'Saldo Final (R$)']:
    resumo[col] = resumo[col].apply(format_brl)

st.dataframe(resumo)

# --- Download Excel ---
def to_excel(dfs, names):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for df, name in zip(dfs, names):
            df.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

excel_data = to_excel(
    [cd_df, lc_df, ip_df, btc_df, eth_df, sol_df],
    ['CDI_103%', 'LCI_91%', f'IPCA+{spread_ipca:.1f}%', 'Bitcoin', 'Ethereum', 'Solana']
)

st.subheader("⬇️ Baixar Planilha Excel (.xlsx)")
st.download_button(
    "📥 Baixar Planilha Excel",
    data=excel_data,
    file_name="simulador_investimentos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)