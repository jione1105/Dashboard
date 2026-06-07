import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==============================================================================
# 1. 페이지 기본 설정
# ==============================================================================
st.set_page_config(
    page_title="CBOT 농산물 선물 대시보드",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌾 CBOT 농산물 선물 실시간 및 트렌드 대시보드")
st.markdown("밀(Wheat), 옥수수(Corn), 대두(Soybeans), 쌀(Rough Rice)의 CBOT 선물 가격과 이동평균선을 모니터링합니다.")

# ==============================================================================
# 2. 사이드바 - 유저 인터랙션 제어
# ==============================================================================
st.sidebar.header("📊 대시보드 설정")

# 작물 선택 딕셔너리 (yfinance 심볼 매핑)
CROP_DICT = {
    "밀 (Wheat - SRW)": "W=F",
    "옥수수 (Corn)": "C=F",
    "대두 (Soybeans)": "S=F",
    "쌀 (Rough Rice)": "ZR=F"
}
selected_crop_label = st.sidebar.selectbox("🔎 분석할 작물 선택", list(CROP_DICT.keys()))
selected_ticker = CROP_DICT[selected_crop_label]

# 조회 기간 설정
st.sidebar.subheader("📅 조회 기간")
period_options = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "2년": "2y"}
selected_period_label = st.sidebar.selectbox("기간 선택", list(period_options.keys()), index=1)
selected_period = period_options[selected_period_label]

# 이동평균선(MA) 기간 설정
st.sidebar.subheader("📈 이동평균선(MA) 설정")
ma_short = st.sidebar.number_input("단기 이평선 기준일", min_value=2, max_value=50, value=5)
ma_long = st.sidebar.number_input("장기 이평선 기준일", min_value=10, max_value=200, value=20)

# ==============================================================================
# 3. 데이터 파이프라인 (Data Pipeline / Cache 처리)
# ==============================================================================
@st.cache_data(ttl=3600)  # 1시간 동안 캐시 유지 (불필요한 API 호출 방지)
def load_cbot_data(ticker, period):
    try:
        # yfinance 데이터 fetch
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            return None
        
        # 날짜 포맷 정리 및 필요한 컬럼만 추출
        data = data[['Open', 'High', 'Low', 'Close', 'Volume']]
        data.index = data.index.date
        return data
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return None

# 데이터 로드 실행
df = load_cbot_data(selected_ticker, selected_period)

# ==============================================================================
# 4. 메인 대시보드 화면 구성
# ==============================================================================
if df is not None and not df.empty:
    
    # 4-1. 기술적 지표 계산 (이동평균선)
    df[f'MA_{ma_short}'] = df['Close'].rolling(window=ma_short).mean()
    df[f'MA_{ma_long}'] = df['Close'].rolling(window=ma_long).mean()
    
    # 최신 데이터 및 이전 영업일 데이터 추출 (Metric Card용)
    latest_date = df.index[-1]
    latest_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2] if len(df) > 1 else latest_price
    price_change = latest_price - prev_price
    price_change_pct = (price_change / prev_price) * 100
    
    latest_volume = df['Volume'].iloc[-1]
    
    # 4-2. 상단 주요 지표 (Metric Cards) Layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            label=f"현재 가격 ({selected_crop_label.split(' ')[0]})", 
            value=f"${latest_price:,.2f}", 
            delta=f"{price_change:+,.2f} ({price_change_pct:+.2f}%)"
        )
    with col2:
        st.metric(label="최근 거래일", value=str(latest_date))
    with col3:
        st.metric(label="당일 거래량", value=f"{latest_volume:,}")
    with col4:
        # 단위 정보 노출
        unit = "부셸 (bu)" if "쌀" not in selected_crop_label else "백파운드 (cwt)"
        st.metric(label="거래 단위", value=unit)
        
    st.markdown("---")
    
    # 4-3. Plotly 활용 인터랙티브 캔들스틱/이평선 차트 시각화
    st.subheader(f"📊 {selected_crop_label} 가격 추이 및 이동평균선 ({selected_period_label})")
    
    fig = go.Figure()
    
    # 캔들스틱 차트 추가
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="가격 (Candle)"
    ))
    
    # 단기 이동평균선 추가
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[f'MA_{ma_short}'],
        mode='lines',
        line=dict(color='orange', width=1.5),
        name=f'{ma_short}일 이동평균선'
    ))
    
    # 장기 이동평균선 추가
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df[f'MA_{ma_long}'],
        mode='lines',
        line=dict(color='blue', width=1.5),
        name=f'{ma_long}일 이동평균선'
    ))
    
    # 레이아웃 스타일 설정
    fig.update_layout(
        xaxis_rangeslider_visible=False,  # 하단 범위 슬라이더 숨김 (깔끔한 UI용)
        template="plotly_white",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=20, b=20),
        height=550,
        yaxis=dict(title="가격 (USD)", tickformat="$,.2f")
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # 4-4. 하단 원시 데이터 뷰어 (Raw Data)
    st.markdown("---")
    with st.expander("📂 원시 데이터(Raw Data) 및 기술 지표 테이블 보기"):
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)

else:
    st.warning("선택한 조건의 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")