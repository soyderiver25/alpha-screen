
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands
from ta.volume import OnBalanceVolumeIndicator
import streamlit as st
import json
import os

FAV_FILE = "favoritos.json"

def cargar_favoritos():
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, "r") as f:
            return json.load(f)
    return []

def guardar_favoritos(favs):
    with open(FAV_FILE, "w") as f:
        json.dump(favs, f)

def descargar_datos(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return pd.DataFrame()

def compute_indicators(ticker):
    df = descargar_datos(ticker)
    if df.empty or len(df) < 60:
        return None

    df.dropna(inplace=True)
    if df["Close"].iloc[-1] < 3:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    rsi = RSIIndicator(close).rsi().iloc[-1]
    stoch = StochasticOscillator(high, low, close).stoch().iloc[-1]
    macd = MACD(close).macd_diff().iloc[-1]
    boll = BollingerBands(close)
    bb_dist = close.iloc[-1] - boll.bollinger_mavg().iloc[-1]
    obv = OnBalanceVolumeIndicator(close, volume).on_balance_volume().iloc[-1]
    adx = ADXIndicator(high, low, close).adx().iloc[-1]
    ema20 = EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = EMAIndicator(close, window=50).ema_indicator().iloc[-1]
    ema_cross = 1 if ema20 > ema50 else 0

    indicators = {
        "Ticker": ticker,
        "Price": round(close.iloc[-1], 2),
        "RSI": round(rsi, 2),
        "Stoch": round(stoch, 2),
        "MACD_diff": round(macd, 3),
        "Boll_Dist": round(bb_dist, 2),
        "OBV": round(obv, 2),
        "ADX": round(adx, 2),
        "EMA_Cross": ema_cross
    }

    score = get_score(indicators)
    signal = get_signal(score)
    indicators["Score"] = score
    indicators["Signal"] = signal
    return indicators

def get_score(ind):
    score = 0
    score += 0.35 if ind["RSI"] < 30 else 0
    score += 0.25 if ind["MACD_diff"] > 0 else 0
    score += 0.10 if ind["ADX"] > 25 else 0
    score += 0.10 if ind["OBV"] > 0 else 0
    score += 0.10 if ind["EMA_Cross"] == 1 else 0
    score += 0.05 if ind["Boll_Dist"] < 0 else 0
    score += 0.05 if ind["Stoch"] < 20 else 0
    return round(score, 2)

def get_signal(score):
    if score >= 0.75:
        return "Compra fuerte"
    elif score >= 0.55:
        return "Compra débil"
    elif score >= 0.4:
        return "Neutral"
    elif score >= 0.15:
        return "Venta débil"
    else:
        return "Venta fuerte"

# Interfaz Streamlit
st.title("📈 ALPHA SCREEN - Screener técnico de acciones")
ticker_input = st.text_input("Ingresá los tickers separados por coma:", "AAPL, MSFT, GOOGL, NVDA")
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

st.markdown("---")
st.subheader("⭐ Tus acciones favoritas")
favoritos = st.session_state.get("favoritos", cargar_favoritos())

nuevo = st.text_input("Agregar nuevo ticker a favoritos")
if st.button("➕ Agregar a favoritos") and nuevo:
    nuevo = nuevo.strip().upper()
    if nuevo not in favoritos:
        favoritos.append(nuevo)
        guardar_favoritos(favoritos)
        st.success(f"{nuevo} agregado a favoritos.")
        st.session_state.favoritos = favoritos

eliminar = st.selectbox("Seleccioná un favorito para eliminar", [""] + favoritos)
if st.button("❌ Eliminar seleccionado") and eliminar:
    favoritos.remove(eliminar)
    guardar_favoritos(favoritos)
    st.success(f"{eliminar} eliminado de favoritos.")
    st.session_state.favoritos = favoritos

def analizar_tickers(tickers, titulo):
    st.markdown(f"### {titulo}")
    results = []
    for ticker in tickers:
        indicators = compute_indicators(ticker)
        if indicators:
            results.append(indicators)

    if not results:
        st.error("⚠️ No se encontraron datos válidos.")
        return

    df = pd.DataFrame(results)
    df.sort_values(by="Score", ascending=False, inplace=True)
    df["Ranking"] = range(1, len(df) + 1)
    df = df[["Ranking", "Ticker", "Price", "RSI", "Stoch", "MACD_diff", "Boll_Dist", "OBV", "ADX", "EMA_Cross", "Score", "Signal"]]

    st.dataframe(df)
    df.to_excel("todos_validos.xlsx", index=False)
    with open("todos_validos.xlsx", "rb") as f:
        st.download_button("📥 Descargar Excel", f, file_name="todos_validos.xlsx")

    st.markdown("🏆 **Top 10 oportunidades de compra fuerte:**")
    st.dataframe(df[df["Signal"] == "Compra fuerte"].head(10))

    st.markdown("🚨 **Top 10 señales de venta fuerte:**")
    st.dataframe(df[df["Signal"] == "Venta fuerte"].head(10))

if st.button("🔍 Ejecutar análisis manual") and tickers:
    analizar_tickers(tickers, "📊 Resultados de tu análisis manual")
