import streamlit as st
import pandas as pd
import numpy as np
import requests
import re
import os
import io
import datetime
import plotly.graph_objects as go
import plotly.express as px

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="International Cost of Capital Calculator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for sleek executive appearance
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #f8fafc 0%, #edf2f7 100%);
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 12px;
    }
    .metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-val {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a202c;
    }
    .metric-sub {
        font-size: 0.8rem;
        color: #718096;
    }
    .source-box {
        background-color: #f7fafc;
        border-left: 4px solid #3182ce;
        padding: 10px 14px;
        margin: 8px 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
    }
    .badge-override {
        background-color: #fed7d7;
        color: #9b2c2c;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-auto {
        background-color: #c6f6d5;
        color: #22543d;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Data Directories & Constants
# ---------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
BETAS_CSV_PATH = os.path.join(DATA_DIR, "industry_betas.csv")
TAX_CSV_PATH = os.path.join(DATA_DIR, "oecd_tax_rates.csv")
YIELDS_CSV_PATH = os.path.join(DATA_DIR, "fallback_yields.csv")

COUNTRY_TRADING_ECONOMICS_SLUGS = {
    'United States': ('united-states', 'USD', '$'),
    'Australia': ('australia', 'AUD', 'A$'),
    'Austria': ('austria', 'EUR', '€'),
    'Belgium': ('belgium', 'EUR', '€'),
    'Brazil': ('brazil', 'BRL', 'R$'),
    'Canada': ('canada', 'CAD', 'C$'),
    'Chile': ('chile', 'CLP', 'CLP$'),
    'China': ('china', 'CNY', '¥'),
    'Colombia': ('colombia', 'COP', 'COL$'),
    'Czech Republic': ('czech-republic', 'CZK', 'Kč'),
    'Denmark': ('denmark', 'DKK', 'kr'),
    'Finland': ('finland', 'EUR', '€'),
    'France': ('france', 'EUR', '€'),
    'Germany': ('germany', 'EUR', '€'),
    'Greece': ('greece', 'EUR', '€'),
    'Hungary': ('hungary', 'HUF', 'Ft'),
    'India': ('india', 'INR', '₹'),
    'Indonesia': ('indonesia', 'IDR', 'Rp'),
    'Ireland': ('ireland', 'EUR', '€'),
    'Israel': ('israel', 'ILS', '₪'),
    'Italy': ('italy', 'EUR', '€'),
    'Japan': ('japan', 'JPY', '¥'),
    'Mexico': ('mexico', 'MXN', 'Mex$'),
    'Netherlands': ('netherlands', 'EUR', '€'),
    'New Zealand': ('new-zealand', 'NZD', 'NZ$'),
    'Norway': ('norway', 'NOK', 'kr'),
    'Poland': ('poland', 'PLN', 'zł'),
    'Portugal': ('portugal', 'EUR', '€'),
    'Singapore': ('singapore', 'SGD', 'S$'),
    'South Africa': ('south-africa', 'ZAR', 'R'),
    'South Korea': ('south-korea', 'KRW', '₩'),
    'Spain': ('spain', 'EUR', '€'),
    'Sweden': ('sweden', 'SEK', 'kr'),
    'Switzerland': ('switzerland', 'CHF', 'CHF'),
    'Turkey': ('turkey', 'TRY', '₺'),
    'United Kingdom': ('united-kingdom', 'GBP', '£')
}

DEFAULT_DAMODARAN_BBB_SPREAD = 1.11  # 1.11% as of January 2026

# ---------------------------------------------------------
# Data Fetching & Caching
# ---------------------------------------------------------

@st.cache_data(ttl=3600, show_spinner=False)
def load_industry_betas():
    """
    Retrieves industry betas from Aswath Damodaran's website.
    URL: https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls
    Falls back to cached local CSV if network call fails.
    """
    source_url = "https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls"
    date_str = "January 2026 (Annual Update)"
    is_live = False

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
        resp = requests.get(source_url, headers=headers, timeout=6)
        if resp.status_code == 200:
            import xlrd
            book = xlrd.open_workbook(file_contents=resp.content)
            sheet = book.sheet_by_name('Industry Averages')
            
            # Read metadata date if available
            try:
                date_val = sheet.cell_value(0, 1)
                if isinstance(date_val, (int, float)):
                    dt = xlrd.xldate_as_tuple(date_val, 0)
                    date_str = f"{datetime.date(dt[0], dt[1], dt[2]).strftime('%B %d, %Y')}"
            except Exception:
                pass

            rows = []
            for r in range(10, sheet.nrows):
                ind = str(sheet.cell_value(r, 0)).strip()
                if not ind:
                    continue
                num_firms = sheet.cell_value(r, 1)
                beta = sheet.cell_value(r, 2)
                de_ratio = sheet.cell_value(r, 3)
                eff_tax = sheet.cell_value(r, 4)
                u_beta = sheet.cell_value(r, 5)
                cash_val = sheet.cell_value(r, 6)
                u_beta_cash = sheet.cell_value(r, 7)
                rows.append({
                    'Industry': ind,
                    'Number of Firms': int(num_firms) if isinstance(num_firms, (int, float)) and num_firms == int(num_firms) else num_firms,
                    'Beta': round(float(beta), 4) if isinstance(beta, (int, float)) else beta,
                    'DE_Ratio': round(float(de_ratio), 4) if isinstance(de_ratio, (int, float)) else de_ratio,
                    'Effective_Tax_Rate': round(float(eff_tax), 4) if isinstance(eff_tax, (int, float)) else eff_tax,
                    'Unlevered_Beta': round(float(u_beta), 4) if isinstance(u_beta, (int, float)) else u_beta,
                    'Cash_Firm_Value': round(float(cash_val), 4) if isinstance(cash_val, (int, float)) else cash_val,
                    'Unlevered_Beta_Cash_Corrected': round(float(u_beta_cash), 4) if isinstance(u_beta_cash, (int, float)) else u_beta_cash
                })
            df = pd.DataFrame(rows)
            is_live = True
            return df, source_url, date_str, is_live
    except Exception as e:
        pass

    # Fallback to local pre-compiled file
    if os.path.exists(BETAS_CSV_PATH):
        df = pd.read_csv(BETAS_CSV_PATH)
        return df, source_url, date_str, False

    return pd.DataFrame(), source_url, date_str, False


@st.cache_data(ttl=3600, show_spinner=False)
def load_damodaran_bbb_spread():
    """
    Retrieves Baa2/BBB borrowing spread for large non-financial service firms.
    Source: https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/ratings.html
    """
    source_url = "https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/ratings.html"
    date_str = "January 2026"
    is_live = False

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(source_url, headers=headers, timeout=6)
        if resp.status_code == 200:
            html = resp.text
            # Look for Baa2/BBB row spread
            # Table has: 2.999999 ... Baa2/BBB ... 1.11%
            m = re.search(r'Baa2/BBB.*?([0-9\.]+)%', html, re.DOTALL)
            if m:
                spread = float(m.group(1))
                is_live = True
                return spread, source_url, date_str, is_live
    except Exception:
        pass

    return DEFAULT_DAMODARAN_BBB_SPREAD, source_url, date_str, False


@st.cache_data(ttl=3600, show_spinner=False)
def load_tax_rates():
    """
    Loads statutory corporate income tax rates.
    Source: OECD Corporate Tax Statistics (2024/2026 publication)
    https://www.oecd.org/en/publications/corporate-tax-statistics-2024_9c27d6e8-en.html
    """
    source_url = "https://www.oecd.org/en/publications/corporate-tax-statistics-2024_9c27d6e8-en/full-report/statutory-corporate-income-tax-rates_440f9286.html"
    date_str = "OECD Corporate Tax Statistics 2024"

    if os.path.exists(TAX_CSV_PATH):
        df = pd.read_csv(TAX_CSV_PATH)
    else:
        df = pd.DataFrame([
            {'Country': 'United States', 'ISO': 'USA', 'Tax_Rate': 25.8, 'Currency': 'USD', 'Currency_Symbol': '$', 'Notes': 'Federal 21% + state weighted avg'}
        ])
    return df, source_url, date_str


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_government_yield(country_name):
    """
    Retrieves latest 10-year government bond yield from Trading Economics.
    URL: https://tradingeconomics.com/{country}/government-bond-yield
    Falls back to latest available curated snapshot.
    """
    slug_info = COUNTRY_TRADING_ECONOMICS_SLUGS.get(country_name, ('united-states', 'USD', '$'))
    slug = slug_info[0]
    source_url = f"https://tradingeconomics.com/{slug}/government-bond-yield"
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

    try:
        resp = requests.get(source_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            m = re.findall(r'<meta[^>]*name=\"description\"[^>]*content=\"([^\"]+)\"', resp.text, re.I)
            if m:
                desc = m[0]
                val_m = re.search(r'(?:at|to|eased to|rose to|traded at|around|yield\s+was)\s+([0-9\.\-]+)\s*%', desc, re.I)
                if not val_m:
                    val_m = re.search(r'([0-9\.]+)\s*%', desc)
                date_m = re.search(r'on\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})', desc)
                if val_m:
                    yield_val = float(val_m.group(1))
                    date_val = date_m.group(1) if date_m else "Latest"
                    return yield_val, date_val, source_url, True
    except Exception:
        pass

    # Fallback to local snapshot
    if os.path.exists(YIELDS_CSV_PATH):
        df_y = pd.read_csv(YIELDS_CSV_PATH)
        match = df_y[df_y['Country'] == country_name]
        if not match.empty:
            row = match.iloc[0]
            return float(row['Yield_10Y']), str(row['Date']), source_url, False

    # Default fallback
    return 5.14 if country_name == 'United States' else 3.50, "November 2026 Snapshot", source_url, False


# ---------------------------------------------------------
# Sidebar: Global Parameters & Selection
# ---------------------------------------------------------
st.sidebar.title("🌐 Project Parameters")

# Refresh button
if st.sidebar.button("🔄 Refresh Live Data", help="Clears cache and re-fetches latest yields, betas, and spreads"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")

# 1. Industry Selection
df_betas, betas_source_url, betas_date, betas_is_live = load_industry_betas()
industry_list = sorted(df_betas['Industry'].tolist()) if not df_betas.empty else ["Software (System & Application)"]

default_ind_index = 0
if "Software (System & Application)" in industry_list:
    default_ind_index = industry_list.index("Software (System & Application)")

selected_industry = st.sidebar.selectbox(
    "1. Industry (Damodaran)",
    industry_list,
    index=default_ind_index,
    help="Select an industry to retrieve its unlevered beta from Aswath Damodaran's dataset."
)

# 2. Country Selection
df_tax, tax_source_url, tax_date = load_tax_rates()
all_countries = sorted(list(COUNTRY_TRADING_ECONOMICS_SLUGS.keys()))
default_country_index = all_countries.index("United States") if "United States" in all_countries else 0

selected_country = st.sidebar.selectbox(
    "2. Target Country",
    all_countries,
    index=default_country_index,
    help="Select the foreign/target country to compare against the U.S. dollar project."
)

target_currency = COUNTRY_TRADING_ECONOMICS_SLUGS.get(selected_country, ('', 'USD', '$'))[1]
target_currency_sym = COUNTRY_TRADING_ECONOMICS_SLUGS.get(selected_country, ('', 'USD', '$'))[2]

# 3. Capital Structure & ERP
st.sidebar.markdown("---")
st.sidebar.subheader("3. Capital Structure & Risk")

equity_risk_premium_input = st.sidebar.number_input(
    "Equity Risk Premium (ERP, %)",
    min_value=0.0,
    max_value=25.0,
    value=6.5,
    step=0.25,
    help="Default is 6.5%. Applied to both USD and foreign project cost of equity calculations."
)
erp = equity_risk_premium_input / 100.0

debt_share_input = st.sidebar.number_input(
    "Target Debt Share (D/V, %)",
    min_value=0.0,
    max_value=95.0,
    value=30.0,
    step=5.0,
    help="Debt-to-firm value ratio (D / (D + E)). Default is 30%."
)
debt_share = debt_share_input / 100.0
equity_share = 1.0 - debt_share
de_ratio = debt_share / equity_share if equity_share > 0 else 0.0

# 4. Project Tax Rate Switch (Required Button)
st.sidebar.markdown("---")
st.sidebar.subheader("4. Project Corporate Tax Rate")

# Fetch default tax rates
us_tax_row = df_tax[df_tax['Country'] == 'United States']
us_default_tax = float(us_tax_row['Tax_Rate'].iloc[0]) if not us_tax_row.empty else 25.8

fc_tax_row = df_tax[df_tax['Country'] == selected_country]
fc_default_tax = float(fc_tax_row['Tax_Rate'].iloc[0]) if not fc_tax_row.empty else 25.8

tax_choice = st.sidebar.radio(
    "Select Project Tax Rate Choice:",
    [f"U.S. Corporate Tax Rate ({us_default_tax:.1f}%)", f"{selected_country} Tax Rate ({fc_default_tax:.1f}%)"],
    index=0,
    help="As per requirements, both currency evaluations must use the SAME chosen project tax rate."
)

# ---------------------------------------------------------
# Sidebar: Manual Overrides
# ---------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("🛠️ Manual Overrides & Custom Inputs", expanded=False):
    st.markdown("<small>Check any box to overwrite the automatically fetched or calculated data.</small>", unsafe_allow_html=True)
    
    # Unlevered Beta
    raw_ubeta = 1.2254
    if not df_betas.empty:
        ind_row = df_betas[df_betas['Industry'] == selected_industry]
        if not ind_row.empty:
            raw_ubeta = float(ind_row['Unlevered_Beta'].iloc[0])

    override_ubeta = st.checkbox("Overwrite Unlevered Beta", value=False)
    unlevered_beta = st.number_input(
        "Unlevered Beta (β_U)",
        value=float(raw_ubeta),
        step=0.05,
        disabled=not override_ubeta
    ) if override_ubeta else float(raw_ubeta)

    # US Bond Yield
    us_yield_fetched, us_yield_date, us_yield_url, us_yield_live = fetch_government_yield("United States")
    override_us_yield = st.checkbox("Overwrite U.S. 10Y Yield", value=False)
    us_rf = st.number_input(
        "U.S. 10Y Yield (%)",
        value=float(us_yield_fetched),
        step=0.1,
        disabled=not override_us_yield
    ) / 100.0 if override_us_yield else us_yield_fetched / 100.0

    # Foreign Bond Yield
    fc_yield_fetched, fc_yield_date, fc_yield_url, fc_yield_live = fetch_government_yield(selected_country)
    override_fc_yield = st.checkbox(f"Overwrite {selected_country} 10Y Yield", value=False)
    fc_rf = st.number_input(
        f"{selected_country} 10Y Yield (%)",
        value=float(fc_yield_fetched),
        step=0.1,
        disabled=not override_fc_yield
    ) / 100.0 if override_fc_yield else fc_yield_fetched / 100.0

    # Tax Rates Override
    override_us_tax = st.checkbox("Overwrite U.S. Tax Rate", value=False)
    custom_us_tax = st.number_input(
        "U.S. Tax Rate (%)",
        value=float(us_default_tax),
        step=0.5,
        disabled=not override_us_tax
    ) if override_us_tax else us_default_tax

    override_fc_tax = st.checkbox(f"Overwrite {selected_country} Tax Rate", value=False)
    custom_fc_tax = st.number_input(
        f"{selected_country} Tax Rate (%)",
        value=float(fc_default_tax),
        step=0.5,
        disabled=not override_fc_tax
    ) if override_fc_tax else fc_default_tax

    # USD BBB Spread
    damodaran_spread, bbb_url, bbb_date, bbb_is_live = load_damodaran_bbb_spread()
    override_usd_spread = st.checkbox("Overwrite USD BBB Spread", value=False)
    usd_bbb_spread = st.number_input(
        "USD BBB Spread (%)",
        value=float(damodaran_spread),
        step=0.1,
        disabled=not override_usd_spread
    ) / 100.0 if override_usd_spread else damodaran_spread / 100.0

    # Foreign BBB Spread: Manual vs Auto
    st.markdown("---")
    st.markdown("<b>Foreign Country BBB Spread</b>", unsafe_allow_html=True)
    
    # Auto calculation methods:
    # 1. Fisher Parity: spread_FC = spread_USD * (1 + fc_rf) / (1 + us_rf)
    # 2. Constant Spread: spread_FC = spread_USD
    auto_foreign_spread_fisher = usd_bbb_spread * ((1.0 + fc_rf) / (1.0 + us_rf)) if (1.0 + us_rf) > 0 else usd_bbb_spread
    
    auto_spread_method = st.radio(
        "Auto Calculation Methodology:",
        ["Fisher Interest Parity Adjusted", "Constant Basis Points Spread"],
        index=0,
        help="Fisher Parity scales the spread by relative nominal bond yields: Spread_FC = Spread_USD * (1+Rf_FC)/(1+Rf_US)."
    )
    
    calculated_fc_spread = auto_foreign_spread_fisher if "Fisher" in auto_spread_method else usd_bbb_spread

    override_fc_spread = st.checkbox("Overwrite Foreign BBB Spread", value=False)
    if override_fc_spread:
        fc_bbb_spread = st.number_input(
            f"Manual {selected_country} BBB Spread (%)",
            value=float(calculated_fc_spread * 100.0),
            step=0.1
        ) / 100.0
    else:
        fc_bbb_spread = calculated_fc_spread
        st.info(f"Auto-Calculated Spread: **{fc_bbb_spread*100.0:.3f}%**")

# Determine active project tax rate T
if "U.S." in tax_choice:
    project_tax_rate = custom_us_tax / 100.0
    tax_source_label = "U.S. Corporate Tax Rate"
else:
    project_tax_rate = custom_fc_tax / 100.0
    tax_source_label = f"{selected_country} Corporate Tax Rate"

# ---------------------------------------------------------
# Core International Finance Calculations
# ---------------------------------------------------------
# 1. Beta Levering (Hamada Equation)
# Beta_L = Beta_U * [1 + (1 - T) * (D/E)]
levered_beta = unlevered_beta * (1.0 + (1.0 - project_tax_rate) * de_ratio)

# 2. Cost of Equity
# USD: CAPM
cost_of_equity_usd = us_rf + (levered_beta * erp)

# Foreign Currency:
# Standard International CAPM / Fisher relationship
# Fisher parity: (1 + Re_FC) = (1 + Re_USD) * (1 + Rf_FC) / (1 + Rf_US)
cost_of_equity_fc_fisher = ((1.0 + cost_of_equity_usd) * ((1.0 + fc_rf) / (1.0 + us_rf))) - 1.0
# Linear approximation / International CAPM: Re_FC = Rf_FC + Beta_L * ERP
cost_of_equity_fc_linear = fc_rf + (levered_beta * erp)
# We use the exact Fisher Parity as primary, and provide linear in detailed comparisons
cost_of_equity_fc = cost_of_equity_fc_fisher

# 3. Cost of Debt
# USD
pretax_debt_cost_usd = us_rf + usd_bbb_spread
aftertax_debt_cost_usd = pretax_debt_cost_usd * (1.0 - project_tax_rate)

# Foreign Currency
pretax_debt_cost_fc = fc_rf + fc_bbb_spread
aftertax_debt_cost_fc = pretax_debt_cost_fc * (1.0 - project_tax_rate)

# 4. WACC
# WACC = (E/V) * Re + (D/V) * Rd * (1 - T)
wacc_usd = (equity_share * cost_of_equity_usd) + (debt_share * aftertax_debt_cost_usd)
wacc_fc = (equity_share * cost_of_equity_fc) + (debt_share * aftertax_debt_cost_fc)

# Fisher Parity WACC benchmark
wacc_fc_parity_benchmark = ((1.0 + wacc_usd) * ((1.0 + fc_rf) / (1.0 + us_rf))) - 1.0


# ---------------------------------------------------------
# Main App Header & Data Transparency Dashboard
# ---------------------------------------------------------
st.title("🌐 International Cost of Capital & WACC Calculator")
st.markdown(
    "Compare a multinational project's **Cost of Equity**, **Cost of Debt**, and **WACC** in "
    "**USD** and the currency of any selected target economy using corporate finance principles."
)

# Collapsible Live Data & Sources Status
with st.expander("📊 Data Sources, Live Fetch Status & Update Timestamps", expanded=False):
    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
    with s_col1:
        st.markdown(f"**Damodaran Betas** {'🟢 Live' if betas_is_live else '📁 Cached'}")
        st.caption(f"Date: {betas_date}")
        st.caption(f"Unlevered β for *{selected_industry}*: **{unlevered_beta:.4f}**")
        st.markdown(f"[Source Dataset]({betas_source_url})")
    with s_col2:
        st.markdown(f"**Damodaran BBB Spread** {'🟢 Live' if bbb_is_live else '📁 Cached'}")
        st.caption(f"Date: {bbb_date}")
        st.caption(f"USD BBB Spread: **{usd_bbb_spread*100.0:.2f}%**")
        st.markdown(f"[Source Page]({bbb_url})")
    with s_col3:
        st.markdown(f"**OECD Tax Statistics** 🏛️")
        st.caption(f"Date: {tax_date}")
        st.caption(f"US: **{custom_us_tax:.1f}%** | {selected_country}: **{custom_fc_tax:.1f}%**")
        st.markdown(f"[OECD Report]({tax_source_url})")
    with s_col4:
        st.markdown(f"**Trading Economics Bonds** 📈")
        st.caption(f"US 10Y: **{us_rf*100.0:.2f}%** ({us_yield_date})")
        st.caption(f"{selected_country} 10Y: **{fc_rf*100.0:.2f}%** ({fc_yield_date})")
        st.markdown(f"[US Bond]({us_yield_url}) | [{selected_country} Bond]({fc_yield_url})")

st.markdown("<br>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Executive KPI Metric Cards
# ---------------------------------------------------------
kpi1, kpi2, kpi3 = st.columns(3)

with kpi1:
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #3B82F6;">
        <div class="metric-title">Cost of Equity (r_e)</div>
        <div class="metric-val">{cost_of_equity_usd*100.0:.2f}% <span style="font-size: 1rem; color:#6B7280;">USD</span></div>
        <div style="font-size: 1.3rem; font-weight: 600; color: #1D4ED8; margin-top: 4px;">
            {cost_of_equity_fc*100.0:.2f}% <span style="font-size: 0.9rem; color:#6B7280;">{target_currency}</span>
        </div>
        <div class="metric-sub" style="margin-top: 6px;">Levered β: <b>{levered_beta:.3f}</b> | ERP: <b>{erp*100.0:.2f}%</b></div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #10B981;">
        <div class="metric-title">After-Tax Cost of Debt [r_d(1-T)]</div>
        <div class="metric-val">{aftertax_debt_cost_usd*100.0:.2f}% <span style="font-size: 1rem; color:#6B7280;">USD</span></div>
        <div style="font-size: 1.3rem; font-weight: 600; color: #047857; margin-top: 4px;">
            {aftertax_debt_cost_fc*100.0:.2f}% <span style="font-size: 0.9rem; color:#6B7280;">{target_currency}</span>
        </div>
        <div class="metric-sub" style="margin-top: 6px;">Project Tax Rate (T): <b>{project_tax_rate*100.0:.1f}%</b></div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    spread_diff = (wacc_fc - wacc_usd) * 100.0
    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid #8B5CF6; background: linear-gradient(135deg, #F3E8FF 0%, #EDE9FE 100%);">
        <div class="metric-title" style="color: #6B21A8;">Weighted Average Cost of Capital (WACC)</div>
        <div class="metric-val" style="color: #4C1D95;">{wacc_usd*100.0:.2f}% <span style="font-size: 1rem; color:#6D28D9;">USD</span></div>
        <div style="font-size: 1.4rem; font-weight: 700; color: #5B21B6; margin-top: 4px;">
            {wacc_fc*100.0:.2f}% <span style="font-size: 0.9rem; color:#6D28D9;">{target_currency}</span>
        </div>
        <div class="metric-sub" style="color: #6D28D9; margin-top: 6px;">
            Currency Wedge: <b>{spread_diff:+.2f}%</b> | Debt Share: <b>{debt_share*100.0:.0f}%</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# Tabbed Views
# ---------------------------------------------------------
tab_comparison, tab_charts, tab_theory, tab_all_industries, tab_export = st.tabs([
    "📊 Side-by-Side Comparison",
    "📈 Interactive Visualizations",
    "📘 Methodology & Assumptions",
    "🏢 All-Industry Benchmark (96 Sectors)",
    "💾 Export & Download"
])

# ---------------------------------------------------------
# Tab 1: Side-by-Side Comparison
# ---------------------------------------------------------
with tab_comparison:
    st.subheader(f"Side-by-Side Capital Cost Breakdown: USD vs. {selected_country} ({target_currency})")
    
    summary_data = [
        {
            "Metric / Input": "10-Year Risk-Free Yield (r_f)",
            "USD Project": f"{us_rf*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{fc_rf*100.0:.2f}%",
            "Formula / Source": "Trading Economics 10-Yr Benchmark Yield",
            "Status": "Overridden" if override_us_yield or override_fc_yield else "Live / Fetched"
        },
        {
            "Metric / Input": "Industry Unlevered Beta (β_U)",
            "USD Project": f"{unlevered_beta:.4f}",
            f"{selected_country} Project ({target_currency})": f"{unlevered_beta:.4f}",
            "Formula / Source": f"Damodaran Industry Beta ({selected_industry})",
            "Status": "Overridden" if override_ubeta else "Damodaran"
        },
        {
            "Metric / Input": "Target Debt Share (D/V)",
            "USD Project": f"{debt_share*100.0:.1f}%",
            f"{selected_country} Project ({target_currency})": f"{debt_share*100.0:.1f}%",
            "Formula / Source": "User Input (Default: 30%)",
            "Status": "Common Assumption"
        },
        {
            "Metric / Input": "Debt-to-Equity Ratio (D/E)",
            "USD Project": f"{de_ratio:.4f}",
            f"{selected_country} Project ({target_currency})": f"{de_ratio:.4f}",
            "Formula / Source": "(D/V) / (1 - D/V)",
            "Status": "Computed"
        },
        {
            "Metric / Input": "Project Corporate Tax Rate (T)",
            "USD Project": f"{project_tax_rate*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{project_tax_rate*100.0:.2f}%",
            "Formula / Source": f"{tax_source_label} (OECD)",
            "Status": "Selected by User"
        },
        {
            "Metric / Input": "Levered Equity Beta (β_L)",
            "USD Project": f"{levered_beta:.4f}",
            f"{selected_country} Project ({target_currency})": f"{levered_beta:.4f}",
            "Formula / Source": "Hamada: β_U × [1 + (1 - T) × (D/E)]",
            "Status": "Computed"
        },
        {
            "Metric / Input": "Equity Risk Premium (ERP)",
            "USD Project": f"{erp*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{erp*100.0:.2f}%",
            "Formula / Source": "Market ERP Assumption (Default: 6.5%)",
            "Status": "User Input"
        },
        {
            "Metric / Input": "Cost of Equity (r_e)",
            "USD Project": f"{cost_of_equity_usd*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{cost_of_equity_fc*100.0:.2f}%",
            "Formula / Source": "USD: CAPM | Foreign: Fisher Interest Rate Parity",
            "Status": "Primary Output"
        },
        {
            "Metric / Input": "BBB Default Borrowing Spread",
            "USD Project": f"{usd_bbb_spread*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{fc_bbb_spread*100.0:.2f}%",
            "Formula / Source": "USD: Damodaran Baa2/BBB | Foreign: Parity Auto",
            "Status": "Overridden" if override_fc_spread else "Auto Calculated"
        },
        {
            "Metric / Input": "Pre-Tax Cost of Debt (r_d)",
            "USD Project": f"{pretax_debt_cost_usd*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{pretax_debt_cost_fc*100.0:.2f}%",
            "Formula / Source": "r_d = r_f + BBB Spread",
            "Status": "Computed"
        },
        {
            "Metric / Input": "After-Tax Cost of Debt [r_d × (1 - T)]",
            "USD Project": f"{aftertax_debt_cost_usd*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{aftertax_debt_cost_fc*100.0:.2f}%",
            "Formula / Source": "r_d × (1 - T)",
            "Status": "Computed"
        },
        {
            "Metric / Input": "WACC (Weighted Average Cost of Capital)",
            "USD Project": f"{wacc_usd*100.0:.2f}%",
            f"{selected_country} Project ({target_currency})": f"{wacc_fc*100.0:.2f}%",
            "Formula / Source": "(E/V) × r_e + (D/V) × r_d × (1 - T)",
            "Status": "Final Hurdle Rate"
        }
    ]
    
    df_comparison = pd.DataFrame(summary_data)
    st.table(df_comparison)

    st.markdown("""
    > **Note on Parity Consistency:** Under Fisher Parity and Uncovered Interest Parity, the nominal cost of capital in a foreign currency 
    reflects both the real risk profile of the business project and the expected currency depreciation / appreciation driven by inflation differentials.
    """)

# ---------------------------------------------------------
# Tab 2: Visualizations
# ---------------------------------------------------------
with tab_charts:
    st.subheader("Component Comparison & Sensitivity Analysis")
    
    col_c1, col_c2 = st.columns(2)
    
    with col_c1:
        # Side-by-side Bar Chart
        categories = ['Cost of Equity (r_e)', 'Pre-Tax Debt (r_d)', 'After-Tax Debt [r_d(1-T)]', 'WACC']
        usd_vals = [cost_of_equity_usd*100, pretax_debt_cost_usd*100, aftertax_debt_cost_usd*100, wacc_usd*100]
        fc_vals = [cost_of_equity_fc*100, pretax_debt_cost_fc*100, aftertax_debt_cost_fc*100, wacc_fc*100]
        
        fig_bar = go.Figure(data=[
            go.Bar(name='USD Project', x=categories, y=usd_vals, marker_color='#1E3A8A', text=[f"{v:.2f}%" for v in usd_vals], textposition='auto'),
            go.Bar(name=f'{selected_country} ({target_currency})', x=categories, y=fc_vals, marker_color='#0D9488', text=[f"{v:.2f}%" for v in fc_vals], textposition='auto')
        ])
        fig_bar.update_layout(
            title="Capital Cost Component Comparison (%)",
            barmode='group',
            yaxis_title="Rate (%)",
            template="plotly_white",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_c2:
        # Capital Structure Stacked Chart
        fig_donut = go.Figure(data=[go.Pie(
            labels=['Equity Weight (E/V)', 'Debt Weight (D/V)'],
            values=[equity_share*100, debt_share*100],
            hole=.55,
            marker_colors=['#2563EB', '#64748B']
        )])
        fig_donut.update_layout(
            title=f"Capital Structure Allocation (D/V = {debt_share*100:.0f}%, E/V = {equity_share*100:.0f}%)",
            template="plotly_white",
            height=400
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # Sensitivity Analysis: WACC vs. Target Debt Share
    st.markdown("### WACC Sensitivity to Target Debt Share (0% to 80%)")
    d_shares = np.linspace(0.0, 0.80, 17)
    sens_usd = []
    sens_fc = []
    for d in d_shares:
        e = 1.0 - d
        de = d / e if e > 0 else 0
        b_l = unlevered_beta * (1.0 + (1.0 - project_tax_rate) * de)
        re_u = us_rf + (b_l * erp)
        re_f = ((1.0 + re_u) * ((1.0 + fc_rf) / (1.0 + us_rf))) - 1.0
        w_u = (e * re_u) + (d * aftertax_debt_cost_usd)
        w_f = (e * re_f) + (d * aftertax_debt_cost_fc)
        sens_usd.append(w_u * 100.0)
        sens_fc.append(w_f * 100.0)

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(x=d_shares*100, y=sens_usd, mode='lines+markers', name='USD WACC', line=dict(color='#1E3A8A', width=3)))
    fig_sens.add_trace(go.Scatter(x=d_shares*100, y=sens_fc, mode='lines+markers', name=f'{selected_country} ({target_currency}) WACC', line=dict(color='#0D9488', width=3, dash='dash')))
    fig_sens.update_layout(
        title="WACC Curve Across Debt Share Levels (Evaluating Tax Shield Trade-off)",
        xaxis_title="Target Debt Share (D/V, %)",
        yaxis_title="WACC (%)",
        template="plotly_white",
        height=380
    )
    st.plotly_chart(fig_sens, use_container_width=True)

# ---------------------------------------------------------
# Tab 3: Methodology & Assumptions
# ---------------------------------------------------------
with tab_theory:
    st.subheader("International Cost of Capital Theoretical Framework")
    
    st.markdown(r"""
    When evaluating an international capital budgeting project, corporate finance theory requires consistency between the currency of the cash flows and the discount rate:
    * **USD cash flows** must be discounted at the **USD WACC**.
    * **Foreign currency cash flows** must be discounted at the **Foreign Currency WACC**.
    
    Both evaluations should yield consistent Net Present Values (NPVs) under Uncovered Interest Parity and Purchasing Power Parity.
    """)

    st.markdown("#### 1. Beta Relevering (Hamada Equation)")
    st.latex(r"\beta_L = \beta_U \left[ 1 + (1 - T) \frac{D}{E} \right]")
    st.markdown(f"""
    * **$\\beta_U$ (Unlevered Beta):** Measured from Damodaran's U.S. comparable industry peers for **{selected_industry}** ($\beta_U = {unlevered_beta:.4f}$).
    * **$T$ (Project Tax Rate):** **{project_tax_rate*100.0:.2f}%** (selected via the project tax toggle).
    * **$D/E$ (Debt-to-Equity):** Derived from target debt share $D/V = {debt_share*100.0:.1f}\\% \\implies D/E = {de_ratio:.4f}$.
    * **Resulting Levered Beta ($\\beta_L$):** **{levered_beta:.4f}**.
    """)

    st.markdown("#### 2. Cost of Equity: Domestic & International")
    st.latex(r"r_e^{USD} = r_f^{USD} + \beta_L \times \text{ERP}")
    st.latex(r"1 + r_e^{FC} = (1 + r_e^{USD}) \times \frac{1 + r_f^{FC}}{1 + r_f^{USD}} \implies r_e^{FC} = (1 + r_e^{USD}) \frac{1 + r_f^{FC}}{1 + r_f^{USD}} - 1")
    st.markdown(f"""
    * **USD Cost of Equity:** Evaluated using standard CAPM:
      $$r_e^{{USD}} = {us_rf*100.0:.2f}\\% + {levered_beta:.4f} \\times {erp*100.0:.2f}\\% = {cost_of_equity_usd*100.0:.2f}\\%$$
    * **Foreign Cost of Equity (Fisher Parity):** Under international integration, expected inflation differentials scale the nominal discount rate:
      $$r_e^{{FC}} = (1 + {cost_of_equity_usd:.4f}) \\times \\frac{{1 + {fc_rf:.4f}}}{{1 + {us_rf:.4f}}} - 1 = {cost_of_equity_fc*100.0:.2f}\\%$$
    * **Linear International CAPM approximation:**
      $$r_e^{{FC}} \\approx r_f^{{FC}} + \\beta_L \\times \\text{{ERP}} = {fc_rf*100.0:.2f}\\% + {levered_beta:.4f} \\times {erp*100.0:.2f}\\% = {cost_of_equity_fc_linear*100.0:.2f}\\%$$
    """)

    st.markdown("#### 3. Borrowing Cost & Foreign Spread Auto-Calculation")
    st.latex(r"r_d^{USD} = r_f^{USD} + \text{Spread}_{BBB}^{USD}")
    st.latex(r"\text{Spread}_{BBB}^{FC} = \text{Spread}_{BBB}^{USD} \times \frac{1 + r_f^{FC}}{1 + r_f^{USD}}")
    st.markdown(f"""
    * **USD BBB Spread:** **{usd_bbb_spread*100.0:.2f}%** (Damodaran Baa2/BBB default spread for large non-financial firms).
    * **Foreign Spread Auto-Calculation:** By debt parity, nominal credit spreads scale with nominal interest rates:
      $$\\text{{Spread}}_{{BBB}}^{{FC}} = {usd_bbb_spread*100.0:.2f}\\% \\times \\frac{{1 + {fc_rf:.4f}}}{{1 + {us_rf:.4f}}} = {fc_bbb_spread*100.0:.3f}\\%$$
    * **After-Tax Cost of Debt:**
      $$r_d^{{USD}}(1 - T) = {pretax_debt_cost_usd*100.0:.2f}\\% \\times (1 - {project_tax_rate:.4f}) = {aftertax_debt_cost_usd*100.0:.2f}\\%$$
      $$r_d^{{FC}}(1 - T) = {pretax_debt_cost_fc*100.0:.2f}\\% \\times (1 - {project_tax_rate:.4f}) = {aftertax_debt_cost_fc*100.0:.2f}\\%$$
    """)

    st.markdown("#### 4. Weighted Average Cost of Capital (WACC)")
    st.latex(r"\text{WACC} = \left(\frac{E}{V}\right) r_e + \left(\frac{D}{V}\right) r_d (1 - T)")
    st.markdown(f"""
    * **WACC in USD:**
      $$\\text{{WACC}}_{{USD}} = ({equity_share:.2f} \\times {cost_of_equity_usd*100.0:.2f}\\%) + ({debt_share:.2f} \\times {aftertax_debt_cost_usd*100.0:.2f}\\%) = {wacc_usd*100.0:.2f}\\%$$
    * **WACC in {selected_country} ({target_currency}):**
      $$\\text{{WACC}}_{{FC}} = ({equity_share:.2f} \\times {cost_of_equity_fc*100.0:.2f}\\%) + ({debt_share:.2f} \\times {aftertax_debt_cost_fc*100.0:.2f}\\%) = {wacc_fc*100.0:.2f}\\%$$
    * **Direct Fisher Parity Benchmark of USD WACC:**
      $$\\text{{WACC}}_{{FC}}^{{\\text{{Parity}}}} = (1 + \\text{{WACC}}_{{USD}}) \\times \\frac{{1 + r_f^{{FC}}}}{{1 + r_f^{{USD}}}} - 1 = {wacc_fc_parity_benchmark*100.0:.2f}\\%$$
    """)

# ---------------------------------------------------------
# Tab 4: All-Industry Benchmark (96 Sectors)
# ---------------------------------------------------------
with tab_all_industries:
    st.subheader("All-Industry Cost of Capital Comparison (Damodaran 96 Sectors)")
    st.markdown(
        f"Cross-industry comparison using the active parameters: **D/V = {debt_share*100:.0f}%**, "
        f"**ERP = {erp*100:.1f}%**, **Tax Rate = {project_tax_rate*100:.1f}%**, "
        f"and target country **{selected_country} ({target_currency})**."
    )
    
    if not df_betas.empty:
        all_ind_rows = []
        for idx, row in df_betas.iterrows():
            ind_name = str(row['Industry'])
            u_b = float(row['Unlevered_Beta']) if pd.notnull(row['Unlevered_Beta']) else 1.0
            
            # Relever beta
            l_b = u_b * (1.0 + (1.0 - project_tax_rate) * de_ratio)
            
            # Cost of equity
            re_u = us_rf + (l_b * erp)
            re_f = ((1.0 + re_u) * ((1.0 + fc_rf) / (1.0 + us_rf))) - 1.0
            
            # WACC
            w_u = (equity_share * re_u) + (debt_share * aftertax_debt_cost_usd)
            w_f = (equity_share * re_f) + (debt_share * aftertax_debt_cost_fc)
            
            all_ind_rows.append({
                'Industry': ind_name,
                'Unlevered_Beta': round(u_b, 4),
                'Levered_Beta': round(l_b, 4),
                'Cost_of_Equity_USD (%)': round(re_u * 100.0, 2),
                f'Cost_of_Equity_{target_currency} (%)': round(re_f * 100.0, 2),
                'WACC_USD (%)': round(w_u * 100.0, 2),
                f'WACC_{target_currency} (%)': round(w_f * 100.0, 2),
                'WACC_Spread (%)': round((w_f - w_u) * 100.0, 2)
            })
            
        df_all_ind = pd.DataFrame(all_ind_rows)
        
        # Search filter
        search_query = st.text_input("🔍 Filter Industries by Name:", "")
        if search_query:
            df_filtered = df_all_ind[df_all_ind['Industry'].str.contains(search_query, case=False, na=False)]
        else:
            df_filtered = df_all_ind
            
        st.dataframe(df_filtered, use_container_width=True, height=400)
        
        # Scatter visualization
        fig_scatter = px.scatter(
            df_all_ind,
            x='Levered_Beta',
            y='WACC_USD (%)',
            hover_name='Industry',
            title="WACC vs. Levered Beta Across All 96 Industries",
            labels={'Levered_Beta': 'Levered Beta (β_L)', 'WACC_USD (%)': 'USD WACC (%)'},
            template="plotly_white",
            color='WACC_USD (%)',
            color_continuous_scale='Blues'
        )
        # Highlight currently selected industry
        curr_row = df_all_ind[df_all_ind['Industry'] == selected_industry]
        if not curr_row.empty:
            fig_scatter.add_trace(go.Scatter(
                x=[curr_row['Levered_Beta'].iloc[0]],
                y=[curr_row['WACC_USD (%)'].iloc[0]],
                mode='markers+text',
                marker=dict(color='red', size=14, symbol='star'),
                name=f'Selected: {selected_industry}',
                text=[f"★ {selected_industry}"],
                textposition="top center"
            ))
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.warning("Industry betas dataset not available.")

# ---------------------------------------------------------
# Tab 5: Export & Download
# ---------------------------------------------------------
with tab_export:
    st.subheader("💾 Download Calculation Results")
    st.markdown("Export complete valuation schedules for audit, spreadsheet models, and class presentations.")
    
    col_dl1, col_dl2 = st.columns(2)
    
    with col_dl1:
        st.markdown("#### Project Summary Report")
        st.caption("Exports all inputs, market benchmarks, intermediate beta levering, and final WACC.")
        
        export_summary = pd.DataFrame([
            {"Parameter": "Valuation Date", "Value": str(datetime.date.today())},
            {"Parameter": "Selected Industry", "Value": selected_industry},
            {"Parameter": "Selected Target Country", "Value": selected_country},
            {"Parameter": "Target Currency", "Value": target_currency},
            {"Parameter": "U.S. 10Y Yield (r_f)", "Value": f"{us_rf*100.0:.3f}%"},
            {"Parameter": f"{selected_country} 10Y Yield (r_f)", "Value": f"{fc_rf*100.0:.3f}%"},
            {"Parameter": "Unlevered Beta (Beta_U)", "Value": f"{unlevered_beta:.4f}"},
            {"Parameter": "Target Debt Share (D/V)", "Value": f"{debt_share*100.0:.1f}%"},
            {"Parameter": "Debt-to-Equity Ratio (D/E)", "Value": f"{de_ratio:.4f}"},
            {"Parameter": "Project Tax Rate (T)", "Value": f"{project_tax_rate*100.0:.2f}%"},
            {"Parameter": "Project Tax Choice", "Value": tax_source_label},
            {"Parameter": "Levered Beta (Beta_L)", "Value": f"{levered_beta:.4f}"},
            {"Parameter": "Equity Risk Premium (ERP)", "Value": f"{erp*100.0:.2f}%"},
            {"Parameter": "Cost of Equity USD", "Value": f"{cost_of_equity_usd*100.0:.3f}%"},
            {"Parameter": f"Cost of Equity {target_currency}", "Value": f"{cost_of_equity_fc*100.0:.3f}%"},
            {"Parameter": "USD BBB Spread", "Value": f"{usd_bbb_spread*100.0:.3f}%"},
            {"Parameter": f"{target_currency} BBB Spread", "Value": f"{fc_bbb_spread*100.0:.3f}%"},
            {"Parameter": "Pre-tax Cost of Debt USD", "Value": f"{pretax_debt_cost_usd*100.0:.3f}%"},
            {"Parameter": f"Pre-tax Cost of Debt {target_currency}", "Value": f"{pretax_debt_cost_fc*100.0:.3f}%"},
            {"Parameter": "After-tax Cost of Debt USD", "Value": f"{aftertax_debt_cost_usd*100.0:.3f}%"},
            {"Parameter": f"After-tax Cost of Debt {target_currency}", "Value": f"{aftertax_debt_cost_fc*100.0:.3f}%"},
            {"Parameter": "WACC USD", "Value": f"{wacc_usd*100.0:.3f}%"},
            {"Parameter": f"WACC {target_currency}", "Value": f"{wacc_fc*100.0:.3f}%"}
        ])
        
        csv_proj = export_summary.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Project Summary CSV",
            data=csv_proj,
            file_name=f"international_wacc_{selected_industry.replace(' ', '_')}_{selected_country}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_dl2:
        st.markdown("#### All-Industry Benchmark Dataset")
        st.caption("Exports WACC and cost of capital for all 96 Damodaran sectors in USD and target currency.")
        
        if 'df_all_ind' in locals() and not df_all_ind.empty:
            csv_all = df_all_ind.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download All-Industry Benchmark CSV",
                data=csv_all,
                file_name=f"all_industries_wacc_{selected_country}.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.button("Benchmark data not ready", disabled=True)

# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------
st.markdown("---")
st.caption(
    "International Cost of Capital App | Built for International Finance (Kellogg School of Management) | "
    "Data Sources: Damodaran Online (Stern NYU), OECD Corporate Tax Statistics, Trading Economics."
)
