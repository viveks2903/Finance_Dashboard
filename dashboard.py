import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt

# Title of the dashboard
st.title('Enhanced Finance Dashboard')

# Define tickers
tickers = ('TSLA', 'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'BTC-USD', 'ETH-USD', 'DOGE-USD', 'SPY', 'QQQ')
dropdown = st.multiselect('Pick your assets', tickers)

# Define date input
start = st.date_input('Start', value=pd.to_datetime('2021-01-01'))
end = st.date_input('End', value=pd.to_datetime('today'))

# Moving averages options
ma_options = st.multiselect('Overlay Moving Averages (days)', [10, 20, 50, 100, 200], default=[20, 50])

# Function to calculate relative returns
def relativeret(df):
    rel = df.pct_change()
    cumret = (1 + rel).cumprod() - 1
    cumret = cumret.fillna(0)
    return cumret

def calculate_risk_metrics(df):
    # Calculate daily returns, dropping NaN values
    daily_returns = df.pct_change().dropna()

    if daily_returns.empty:
        return pd.DataFrame({'Message': ['No data available for risk metrics']})

    # Cumulative returns for max drawdown calculation
    cumulative_returns = (1 + daily_returns).cumprod()
    max_drawdown = (cumulative_returns / cumulative_returns.cummax() - 1).min()

    # Calculate risk metrics
    annualized_volatility = daily_returns.std().mean() * np.sqrt(252)
    annualized_return = daily_returns.mean().mean() * 252
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility != 0 else 0
    sortino_ratio = (
        annualized_return
        / (daily_returns[daily_returns < 0].std().mean() * np.sqrt(252))
        if (daily_returns[daily_returns < 0].std().mean() * np.sqrt(252)) != 0
        else 0
    )

    metrics = {
        'Annualized Volatility': annualized_volatility,
        'Annualized Return': annualized_return,
        'Sharpe Ratio': sharpe_ratio,
        'Max Drawdown': max_drawdown,
        'Sortino Ratio': sortino_ratio,
    }

    # Convert to DataFrame
    return pd.DataFrame(metrics, index=['Value'])


# Fetch and process data if tickers are selected
if len(dropdown) > 0:
    df = yf.download(dropdown, start, end)['Adj Close']
    cumret = relativeret(df)
    
    # Display raw data preview
    st.header('Raw Data')
    st.write(df)

    # Display correlation matrix
    st.header('Correlation Matrix')
    st.write(df.pct_change().corr())

    # Display cumulative returns with moving averages
    st.header('Returns of {}'.format(dropdown))
    chart_data = cumret.copy()
    for ma in ma_options:
        for asset in dropdown:
            chart_data[f'{asset} MA {ma}'] = df[asset].rolling(window=ma).mean()
    st.line_chart(chart_data)

    # Display risk metrics
    st.header('Risk Metrics')
    if not df.empty:
        risk_metrics = calculate_risk_metrics(df)
        st.write(risk_metrics)
    else:
        st.write("No data available to calculate risk metrics.")

    # Candlestick charts with moving averages
    st.header('Candlestick Charts')
    for asset in dropdown:
        asset_data = yf.download(asset, start, end)
        asset_data['MA20'] = asset_data['Close'].rolling(window=20).mean()
        asset_data['MA50'] = asset_data['Close'].rolling(window=50).mean()
        
        st.subheader(f'Candlestick Chart for {asset}')
        base = alt.Chart(asset_data.reset_index()).encode(
            x='Date:T',
            tooltip=['Date:T', 'Open:Q', 'High:Q', 'Low:Q', 'Close:Q']
        )
        
        rule = base.mark_rule().encode(
            y='Low:Q',
            y2='High:Q'
        )
        
        bars = base.mark_bar().encode(
            y='Open:Q',
            y2='Close:Q',
            color=alt.condition("datum.Open < datum.Close", alt.value("green"), alt.value("red"))
        )
        
        ma20 = alt.Chart(asset_data.reset_index()).mark_line(color='blue').encode(
            x='Date:T',
            y='MA20:Q'
        )
        
        ma50 = alt.Chart(asset_data.reset_index()).mark_line(color='orange').encode(
            x='Date:T',
            y='MA50:Q'
        )
        
        candlestick_chart = rule + bars + ma20 + ma50
        
        st.altair_chart(candlestick_chart, use_container_width=True)
