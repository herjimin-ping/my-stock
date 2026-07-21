import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ------------------------------------------------------------
# 기본 페이지 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="AI 반도체 전문 분석 대시보드",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 AI 반도체 전문 분석 대시보드")
st.caption("AI/반도체 밸류체인 핵심 종목의 주가, 밸류에이션, 기술적 지표를 한눈에 분석합니다.")

# ------------------------------------------------------------
# AI 반도체 밸류체인 종목 (카테고리별)
# ------------------------------------------------------------
SECTORS = {
    "GPU / AI 가속기": {
        "NVIDIA (NVDA)": "NVDA",
        "AMD (AMD)": "AMD",
        "Broadcom (AVGO)": "AVGO",
    },
    "파운드리 / 메모리": {
        "TSMC (TSM)": "TSM",
        "삼성전자 (005930.KS)": "005930.KS",
        "SK하이닉스 (000660.KS)": "000660.KS",
        "Micron (MU)": "MU",
    },
    "반도체 장비": {
        "ASML (ASML)": "ASML",
        "Applied Materials (AMAT)": "AMAT",
        "Lam Research (LRCX)": "LRCX",
        "KLA (KLAC)": "KLAC",
    },
    "데이터센터 / 서버": {
        "Marvell (MRVL)": "MRVL",
        "Super Micro (SMCI)": "SMCI",
        "Arista Networks (ANET)": "ANET",
    },
}

SECTOR_ETF = "SOXX"  # 반도체 섹터 벤치마크 ETF

ALL_TICKERS = {}
for cat, stocks in SECTORS.items():
    ALL_TICKERS.update(stocks)

# ------------------------------------------------------------
# 사이드바 - 설정
# ------------------------------------------------------------
st.sidebar.header("⚙️ 분석 설정")

category = st.sidebar.selectbox("카테고리", options=["전체"] + list(SECTORS.keys()))

if category == "전체":
    candidate_names = list(ALL_TICKERS.keys())
    default_names = ["NVIDIA (NVDA)", "AMD (AMD)", "TSMC (TSM)", "삼성전자 (005930.KS)"]
else:
    candidate_names = list(SECTORS[category].keys())
    default_names = candidate_names[: min(4, len(candidate_names))]

selected_names = st.sidebar.multiselect(
    "분석할 종목 선택",
    options=candidate_names,
    default=default_names,
)

period = st.sidebar.selectbox(
    "조회 기간",
    options=["3mo", "6mo", "1y", "2y", "3y", "5y", "ytd"],
    index=2,
)

ma_short = st.sidebar.number_input("단기 이동평균(일)", min_value=5, max_value=100, value=20)
ma_long = st.sidebar.number_input("장기 이동평균(일)", min_value=20, max_value=300, value=60)

tickers = [ALL_TICKERS[n] for n in selected_names]

if not tickers:
    st.warning("사이드바에서 종목을 하나 이상 선택해 주세요.")
    st.stop()

# ------------------------------------------------------------
# 데이터 로딩
# ------------------------------------------------------------
@st.cache_data(ttl=600)
def load_history(ticker, period):
    return yf.Ticker(ticker).history(period=period)

@st.cache_data(ttl=600)
def load_info(ticker):
    try:
        return yf.Ticker(ticker).info
    except Exception:
        return {}

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ------------------------------------------------------------
# 섹터 벤치마크 (SOXX) 현재가
# ------------------------------------------------------------
st.subheader("🏭 반도체 섹터 벤치마크")
soxx_hist = load_history(SECTOR_ETF, "5d")
if soxx_hist is not None and len(soxx_hist) >= 2:
    last = soxx_hist["Close"].iloc[-1]
    prev = soxx_hist["Close"].iloc[-2]
    change_pct = (last - prev) / prev * 100
    st.metric(label="iShares Semiconductor ETF (SOXX)", value=f"${last:,.2f}", delta=f"{change_pct:+.2f}%")
st.divider()

# ------------------------------------------------------------
# 종목별 현재가 및 밸류에이션 요약
# ------------------------------------------------------------
st.subheader("📌 종목 현재가 & 밸류에이션")

summary_rows = []
for name, tkr in zip(selected_names, tickers):
    hist = load_history(tkr, "5d")
    info = load_info(tkr)
    if hist is not None and len(hist) >= 2:
        last = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2]
        change_pct = (last - prev) / prev * 100
    else:
        last, change_pct = np.nan, np.nan

    summary_rows.append(
        {
            "종목": name,
            "현재가": last,
            "등락률(%)": change_pct,
            "시가총액(B)": (info.get("marketCap") or 0) / 1e9,
            "PER": info.get("trailingPE"),
            "PBR": info.get("priceToBook"),
            "매출성장률(%)": (info.get("revenueGrowth") or 0) * 100,
            "영업이익률(%)": (info.get("operatingMargins") or 0) * 100,
            "52주 최고": info.get("fiftyTwoWeekHigh"),
            "52주 최저": info.get("fiftyTwoWeekLow"),
        }
    )

summary_df = pd.DataFrame(summary_rows)
st.dataframe(
    summary_df.style.format(
        {
            "현재가": "{:.2f}",
            "등락률(%)": "{:+.2f}",
            "시가총액(B)": "{:.1f}",
            "PER": "{:.1f}",
            "PBR": "{:.1f}",
            "매출성장률(%)": "{:.1f}",
            "영업이익률(%)": "{:.1f}",
            "52주 최고": "{:.2f}",
            "52주 최저": "{:.2f}",
        },
        na_rep="N/A",
    ),
    use_container_width=True,
)

st.divider()

# ------------------------------------------------------------
# 종목별 상세 차트 (캔들 + 이동평균 + RSI)
# ------------------------------------------------------------
st.subheader("📊 종목별 기술적 분석")

for name, tkr in zip(selected_names, tickers):
    hist = load_history(tkr, period)
    if hist is None or hist.empty:
        st.warning(f"{name} 데이터를 불러올 수 없습니다.")
        continue

    hist = hist.reset_index()
    date_col = "Date" if "Date" in hist.columns else hist.columns[0]
    hist[f"MA{ma_short}"] = hist["Close"].rolling(window=ma_short).mean()
    hist[f"MA{ma_long}"] = hist["Close"].rolling(window=ma_long).mean()
    hist["RSI"] = compute_rsi(hist["Close"])

    with st.expander(f"📈 {name}", expanded=True):
        col1, col2 = st.columns([3, 1])

        with col1:
            fig = go.Figure()
            fig.add_trace(
                go.Candlestick(
                    x=hist[date_col],
                    open=hist["Open"],
                    high=hist["High"],
                    low=hist["Low"],
                    close=hist["Close"],
                    name=name,
                )
            )
            fig.add_trace(
                go.Scatter(x=hist[date_col], y=hist[f"MA{ma_short}"], name=f"MA{ma_short}", line=dict(width=1.5))
            )
            fig.add_trace(
                go.Scatter(x=hist[date_col], y=hist[f"MA{ma_long}"], name=f"MA{ma_long}", line=dict(width=1.5))
            )
            fig.update_layout(
                height=420,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_rangeslider_visible=False,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)

            rsi_fig = px.line(hist, x=date_col, y="RSI")
            rsi_fig.add_hline(y=70, line_dash="dash", line_color="red")
            rsi_fig.add_hline(y=30, line_dash="dash", line_color="green")
            rsi_fig.update_layout(height=200, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(rsi_fig, use_container_width=True)

        with col2:
            current_rsi = hist["RSI"].iloc[-1]
            st.metric("현재 RSI", f"{current_rsi:.1f}" if pd.notna(current_rsi) else "N/A")
            if pd.notna(current_rsi):
                if current_rsi >= 70:
                    st.warning("과매수 구간")
                elif current_rsi <= 30:
                    st.info("과매도 구간")
                else:
                    st.success("중립 구간")

            ma_s = hist[f"MA{ma_short}"].iloc[-1]
            ma_l = hist[f"MA{ma_long}"].iloc[-1]
            if pd.notna(ma_s) and pd.notna(ma_l):
                trend = "골든크로스 (상승추세)" if ma_s > ma_l else "데드크로스 (하락추세)"
                st.metric("추세 신호", trend)

st.divider()

# ------------------------------------------------------------
# 종목 간 상대 성과 비교 (정규화 수익률)
# ------------------------------------------------------------
st.subheader("📈 상대 성과 비교 (기간 시작 대비 수익률 %, 섹터 벤치마크 포함)")

compare_df = pd.DataFrame()
for name, tkr in zip(selected_names, tickers):
    hist = load_history(tkr, period)
    if hist is None or hist.empty:
        continue
    hist = hist.reset_index()
    date_col = "Date" if "Date" in hist.columns else hist.columns[0]
    normalized = hist["Close"] / hist["Close"].iloc[0] * 100 - 100
    temp = pd.DataFrame({"날짜": hist[date_col], "수익률(%)": normalized, "종목": name})
    compare_df = pd.concat([compare_df, temp], ignore_index=True)

soxx_full = load_history(SECTOR_ETF, period)
if soxx_full is not None and not soxx_full.empty:
    soxx_full = soxx_full.reset_index()
    date_col = "Date" if "Date" in soxx_full.columns else soxx_full.columns[0]
    normalized = soxx_full["Close"] / soxx_full["Close"].iloc[0] * 100 - 100
    temp = pd.DataFrame({"날짜": soxx_full[date_col], "수익률(%)": normalized, "종목": "SOXX (섹터 벤치마크)"})
    compare_df = pd.concat([compare_df, temp], ignore_index=True)

if not compare_df.empty:
    fig_compare = px.line(compare_df, x="날짜", y="수익률(%)", color="종목")
    fig_compare.update_layout(height=480)
    st.plotly_chart(fig_compare, use_container_width=True)

st.divider()

# ------------------------------------------------------------
# 상관관계 히트맵
# ------------------------------------------------------------
st.subheader("🔗 종목 간 상관관계 (일간 수익률 기준)")

returns_df = pd.DataFrame()
for name, tkr in zip(selected_names, tickers):
    hist = load_history(tkr, period)
    if hist is None or hist.empty:
        continue
    daily_return = hist["Close"].pct_change()
    returns_df[name] = daily_return.reset_index(drop=True)

if len(returns_df.columns) >= 2:
    corr = returns_df.corr()
    fig_corr = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        aspect="auto",
    )
    fig_corr.update_layout(height=450)
    st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("상관관계를 보려면 종목을 2개 이상 선택해 주세요.")

# ------------------------------------------------------------
# 원본 데이터
# ------------------------------------------------------------
with st.expander("🔍 원본 데이터 보기"):
    for name, tkr in zip(selected_names, tickers):
        st.markdown(f"**{name}**")
        st.dataframe(load_history(tkr, period), use_container_width=True)
