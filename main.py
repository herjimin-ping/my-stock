import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ------------------------------------------------------------
# 기본 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="글로벌 주식 대시보드",
    page_icon="📈",
    layout="wide",
)

st.title("📈 글로벌 주요 주식 대시보드")
st.caption("Yahoo Finance(yfinance) 데이터를 기반으로 한 실시간 주가 대시보드")

# ------------------------------------------------------------
# 주요 종목 목록
# ------------------------------------------------------------
TICKERS = {
    "Apple (AAPL)": "AAPL",
    "Microsoft (MSFT)": "MSFT",
    "Alphabet (GOOGL)": "GOOGL",
    "Amazon (AMZN)": "AMZN",
    "NVIDIA (NVDA)": "NVDA",
    "Tesla (TSLA)": "TSLA",
    "Meta (META)": "META",
    "삼성전자 (005930.KS)": "005930.KS",
    "SK하이닉스 (000660.KS)": "000660.KS",
    "Toyota (7203.T)": "7203.T",
    "TSMC (TSM)": "TSM",
    "Alibaba (BABA)": "BABA",
}

INDICES = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "다우존스": "^DJI",
    "코스피": "^KS11",
    "니케이225": "^N225",
    "항셍지수": "^HSI",
}

# ------------------------------------------------------------
# 사이드바 - 설정
# ------------------------------------------------------------
st.sidebar.header("⚙️ 설정")

selected_names = st.sidebar.multiselect(
    "종목 선택 (여러 개 가능)",
    options=list(TICKERS.keys()),
    default=["Apple (AAPL)", "NVIDIA (NVDA)", "삼성전자 (005930.KS)"],
)

custom_ticker = st.sidebar.text_input(
    "티커 직접 입력 (선택, 예: GOOG, 000660.KS)", value=""
)

period = st.sidebar.selectbox(
    "조회 기간",
    options=["1mo", "3mo", "6mo", "1y", "2y", "5y", "ytd", "max"],
    index=3,
)

interval = st.sidebar.selectbox(
    "데이터 간격",
    options=["1d", "1wk", "1mo"],
    index=0,
)

chart_kind = st.sidebar.radio("차트 종류", ["캔들스틱", "선그래프"])

tickers = [TICKERS[n] for n in selected_names]
if custom_ticker.strip():
    tickers.append(custom_ticker.strip())

if not tickers:
    st.warning("사이드바에서 종목을 하나 이상 선택하거나 입력해 주세요.")
    st.stop()

# ------------------------------------------------------------
# 데이터 로딩
# ------------------------------------------------------------
@st.cache_data(ttl=600)
def load_history(ticker, period, interval):
    data = yf.Ticker(ticker).history(period=period, interval=interval)
    return data

@st.cache_data(ttl=600)
def load_index_data(period, interval):
    result = {}
    for name, sym in INDICES.items():
        try:
            hist = yf.Ticker(sym).history(period=period, interval=interval)
            result[name] = hist
        except Exception:
            pass
    return result

# ------------------------------------------------------------
# 주요 글로벌 지수 요약
# ------------------------------------------------------------
st.subheader("🌍 주요 글로벌 지수")
index_data = load_index_data("5d", "1d")
idx_cols = st.columns(len(INDICES))
for i, (name, hist) in enumerate(index_data.items()):
    with idx_cols[i]:
        if hist is not None and len(hist) >= 2:
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            change_pct = (last - prev) / prev * 100
            st.metric(label=name, value=f"{last:,.2f}", delta=f"{change_pct:+.2f}%")
        else:
            st.metric(label=name, value="N/A")

st.divider()

# ------------------------------------------------------------
# 개별 종목 KPI
# ------------------------------------------------------------
st.subheader("📌 선택 종목 현재가")
kpi_cols = st.columns(len(tickers))
for i, tkr in enumerate(tickers):
    with kpi_cols[i]:
        hist = load_history(tkr, "5d", "1d")
        if hist is not None and len(hist) >= 2:
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            change_pct = (last - prev) / prev * 100
            st.metric(label=tkr, value=f"{last:,.2f}", delta=f"{change_pct:+.2f}%")
        else:
            st.metric(label=tkr, value="N/A")

st.divider()

# ------------------------------------------------------------
# 개별 차트 (캔들스틱 or 선그래프)
# ------------------------------------------------------------
st.subheader("📊 종목별 차트")

for tkr in tickers:
    hist = load_history(tkr, period, interval)
    if hist is None or hist.empty:
        st.warning(f"{tkr} 데이터를 불러올 수 없습니다.")
        continue

    hist = hist.reset_index()
    date_col = "Date" if "Date" in hist.columns else hist.columns[0]

    st.markdown(f"**{tkr}**")

    if chart_kind == "캔들스틱":
        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=hist[date_col],
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name=tkr,
                )
            ]
        )
    else:
        fig = px.line(hist, x=date_col, y="Close", title=None)

    fig.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------------------------------------
# 종목 비교 (정규화된 수익률)
# ------------------------------------------------------------
st.subheader("📈 종목 비교 (기간 시작 대비 수익률 %)")

compare_df = pd.DataFrame()
for tkr in tickers:
    hist = load_history(tkr, period, interval)
    if hist is None or hist.empty:
        continue
    hist = hist.reset_index()
    date_col = "Date" if "Date" in hist.columns else hist.columns[0]
    normalized = hist["Close"] / hist["Close"].iloc[0] * 100 - 100
    temp = pd.DataFrame({"날짜": hist[date_col], "수익률(%)": normalized, "종목": tkr})
    compare_df = pd.concat([compare_df, temp], ignore_index=True)

if not compare_df.empty:
    fig_compare = px.line(compare_df, x="날짜", y="수익률(%)", color="종목")
    fig_compare.update_layout(height=450)
    st.plotly_chart(fig_compare, use_container_width=True)

# ------------------------------------------------------------
# 원본 데이터 보기
# ------------------------------------------------------------
with st.expander("🔍 원본 데이터 보기"):
    for tkr in tickers:
        st.markdown(f"**{tkr}**")
        st.dataframe(load_history(tkr, period, interval), use_container_width=True)
