# 🌐 International Cost of Capital & WACC Calculator

An interactive Streamlit application developed for **International Finance at the Kellogg School of Management**. The app compares an international capital budgeting project's **Cost of Equity**, **Cost of Debt**, and **Weighted Average Cost of Capital (WACC)** evaluated in **U.S. Dollars (USD)** versus the local currency of any selected target economy.

---

## 📌 Executive Summary & Key Features

* **Side-by-Side Currency Comparison:** Evaluates hurdle rates and capital costs in USD and the foreign currency simultaneously.
* **Live Financial Data Retrieval:**
  * **Industry Unlevered Betas:** Dynamically fetched from [Aswath Damodaran's NYU Stern dataset](https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls) (96 industries).
  * **USD BBB Borrowing Spread:** Scraped from [Damodaran Credit Ratings & Spreads](https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/ratings.html) (1.11% for Baa2/BBB non-financial service firms).
  * **Corporate Statutory Tax Rates:** Sourced from the [OECD Corporate Tax Statistics](https://www.oecd.org/en/publications/corporate-tax-statistics-2024_9c27d6e8-en/full-report/statutory-corporate-income-tax-rates_440f9286.html).
  * **10-Year Sovereign Yields:** Scraped from [Trading Economics](https://tradingeconomics.com/bonds) across 35+ global economies.
* **Interactive Project Tax Rate Switch:** Toggle between U.S. and foreign country tax rates with a single click, applying the chosen rate uniformly across both currency evaluations.
* **Foreign BBB Spread Auto-Calculation:** Automatically computes the foreign borrowing spread using **Fisher Interest Rate Parity** ($\text{Spread}_{FC} = \text{Spread}_{USD} \times \frac{1 + r_f^{FC}}{1 + r_f^{USD}}$) or constant credit spread, with full manual override capabilities.
* **Full Manual Overrides:** Allows users to overwrite any fetched data point (unlevered beta, tax rates, risk-free yields, spreads).
* **All-Industry Benchmark (96 Sectors):** Generates and visualizes cross-industry WACCs and betas for the selected country.
* **Data Refresh & Export:** Includes a live cache refresh button and one-click CSV export of project valuations and industry benchmarks.

---

## 🎯 Default Baseline Settings

When the application opens, it initializes to the required benchmark scenario:
* **Industry:** `Software (System & Application)` ($\beta_U = 1.2254$)
* **Selected Country:** `United States` (USD domestic benchmark)
* **Project Corporate Tax Rate:** `U.S. Tax Rate` ($25.8\%$)
* **Equity Risk Premium (ERP):** `6.5%`
* **Target Debt Share ($D/V$):** `30%` ($D/E \approx 42.86\%$)

---

## 📐 Mathematical Formulation & Financial Theory

### 1. Beta Relevering (Hamada Equation)
Given the target capital structure debt share $D/V$, the debt-to-equity ratio is:
$$\frac{D}{E} = \frac{D/V}{1 - D/V}$$

The equity beta is levered using the project corporate tax rate $T$:
$$\beta_L = \beta_U \left[ 1 + (1 - T)\frac{D}{E} \right]$$

### 2. Cost of Equity ($r_e$)
* **USD Cost of Equity (CAPM):**
  $$r_e^{USD} = r_f^{USD} + \beta_L \times \text{ERP}$$
* **Foreign Currency Cost of Equity (Fisher Parity):**
  Under integrated capital markets and Uncovered Interest Parity:
  $$1 + r_e^{FC} = (1 + r_e^{USD}) \times \frac{1 + r_f^{FC}}{1 + r_f^{USD}} \implies r_e^{FC} = (1 + r_e^{USD}) \frac{1 + r_f^{FC}}{1 + r_f^{USD}} - 1$$
* **Linear International CAPM Approximation:**
  $$r_e^{FC} \approx r_f^{FC} + \beta_L \times \text{ERP}$$

### 3. Cost of Debt ($r_d$) & Spread Auto-Calculation
* **USD Pre-Tax Debt Cost:**
  $$r_d^{USD} = r_f^{USD} + \text{Spread}_{BBB}^{USD}$$
* **Foreign Borrowing Spread (Auto-Calculation via Parity):**
  $$\text{Spread}_{BBB}^{FC} = \text{Spread}_{BBB}^{USD} \times \frac{1 + r_f^{FC}}{1 + r_f^{USD}}$$
* **Foreign Pre-Tax Debt Cost:**
  $$r_d^{FC} = r_f^{FC} + \text{Spread}_{BBB}^{FC}$$
* **After-Tax Cost of Debt:**
  $$r_{d,\text{after-tax}} = r_d \times (1 - T)$$

### 4. Weighted Average Cost of Capital (WACC)
Both currency evaluations use the consistent capital weights and project tax rate:
$$\text{WACC}_{USD} = \left(\frac{E}{V}\right) r_e^{USD} + \left(\frac{D}{V}\right) r_d^{USD}(1 - T)$$
$$\text{WACC}_{FC} = \left(\frac{E}{V}\right) r_e^{FC} + \left(\frac{D}{V}\right) r_d^{FC}(1 - T)$$

---

## 🚀 How to Run Locally

### 1. Prerequisites
Ensure Python 3.9+ is installed on your machine.

### 2. Installation
Clone the repository and install required packages:
```bash
git clone <your-github-repo-url>
cd "Cost of International Capital App"
pip install -r requirements.txt
```

### 3. Launching the App
Run the Streamlit application:
```bash
streamlit run app.py
```
Streamlit will automatically open the app in your default browser at:
`http://localhost:8501`

---

## ☁️ How to Deploy on Streamlit Community Cloud

Deploying your app to the public web takes under 2 minutes:

1. **Push your code to GitHub:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit of International Cost of Capital App"
   git branch -M main
   git remote add origin https://github.com/<your-username>/<your-repo-name>.git
   git push -u origin main
   ```
2. **Open Streamlit Community Cloud:**
   * Go to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
3. **Deploy New App:**
   * Click **New App**.
   * Select your repository (`<your-username>/<your-repo-name>`).
   * Branch: `main`.
   * Main file path: `app.py`.
   * Click **Deploy!**
4. Your live app will be accessible at:
   `https://<your-app-name>.streamlit.app`

---

## 📁 Repository Structure

```
├── app.py                     # Main interactive Streamlit application
├── requirements.txt           # Python dependencies (streamlit, pandas, xlrd, plotly, requests)
├── README.md                  # Complete documentation, theory & deployment guide
├── .streamlit/
│   └── config.toml            # UI theme styling and server configuration
└── data/
    ├── industry_betas.csv     # Damodaran 96-industry betas dataset
    ├── oecd_tax_rates.csv     # OECD Corporate Tax Statistics dataset
    └── fallback_yields.csv    # Trading Economics 10Y sovereign yields snapshot
```

---

## 📚 Data Sources & References

1. **Aswath Damodaran (NYU Stern):**
   * *Industry Betas:* [betas.xls](https://pages.stern.nyu.edu/~adamodar/pc/datasets/betas.xls)
   * *Ratings & Default Spreads:* [ratings.html](https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/ratings.html)
2. **OECD Corporate Tax Statistics:**
   * *Statutory Corporate Tax Rates:* [OECD Corporate Tax Statistics](https://www.oecd.org/en/publications/corporate-tax-statistics-2024_9c27d6e8-en/full-report/statutory-corporate-income-tax-rates_440f9286.html)
3. **Trading Economics:**
   * *10-Year Government Bond Yields:* [Trading Economics Bonds](https://tradingeconomics.com/bonds)
