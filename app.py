import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ==========================================
# 0. 페이지 기본 설정 및 스타일 정의
# ==========================================
st.set_page_config(
    page_title="국제곡물 모니터링 대시보드",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 행정 보고서 스타일 및 UI 정돈을 위한 CSS 인젝션
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 세팅 */
    .reportview-container, .main { background-color: #f1f5f9; }
    .report-title { font-size: 26px; font-weight: bold; color: #0f172a; border-bottom: 3px solid #0f172a; padding-bottom: 10px; margin-bottom: 20px; }
    .section-title { font-size: 16px; font-weight: bold; color: #0f172a; border-bottom: 2px solid #cbd5e1; padding-bottom: 6px; margin-top: 5px; margin-bottom: 15px; }
    
    /* Metric Card 스타일 커스텀 */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #3b82f6;
        border-radius: 4px;
        padding: 12px;
        text-align: center;
    }
    /* 콩/옥수수 비율 카드 하이라이트 */
    div[data-testid="stMetric"]:nth-child(5) {
        border-top-color: #b45309;
        background-color: #fffbeb;
    }
    /* 단가 및 단위 가독성 밸런스 조정 */
    .unit-text { font-size: 12px; font-weight: normal; color: #64748b; margin-left: 2px; }
    .sub-text { font-size: 12px; font-weight: normal; color: #b45309; margin-left: 4px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="report-title">■ 국제곡물 모니터링 대시보드</div>', unsafe_allow_html=True)

# ==========================================
# 1. 실제 Yahoo Finance API 실시간 데이터 수집 펑션
# ==========================================
@st.cache_data(ttl=3600)  # 1시간 동안 데이터를 캐싱하여 불특정 다수 접속 시 API 차단 방지 및 속도 최적화
def get_realtime_data():
    # CBOT 선물 티커 매핑 (밀: ZW=F, 옥수수: ZC=F, 콩: ZS=F, 쌀: ZR=F)
    # 거시지표 티커 매핑 (WTI: CL=F, 브렌트유: BZ=F, 원달러환율: USDKRW=X)
    tickers = {
        '밀': 'ZW=F', '옥수수': 'ZC=F', '콩': 'ZS=F', '쌀': 'ZR=F',
        'WTI': 'CL=F', '브렌트': 'BZ=F', '환율': 'USDKRW=X'
    }
    
    end_date = datetime.today()
    start_date = end_date - timedelta(days=365 * 3) # 최대 3년치 확보
    
    df_list = []
    for name, ticker in tickers.items():
        try:
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)['Close']
            data.name = name
            df_list.append(data)
        except Exception as e:
            pass
            
    df = pd.concat(df_list, axis=1).ffill().dropna()
    
    # [단위 환산 및 지수 도출] 
    # CBOT 곡물 가격(센트/부셸 등)을 국제 기준인 '달러/톤'으로 대략적 환산 공식 적용
    df['밀_달러톤'] = df['밀'] * 0.36743 * 10
    df['옥수수_달러톤'] = df['옥수수'] * 0.39368 * 10
    df['콩_달러톤'] = df['콩'] * 0.36743 * 10
    df['쌀_달러톤'] = df['쌀'] * 22.0462  # 쌀 Cwt 단위 환산
    
    # 콩/옥수수 비율 계산
    df['콩_옥수수_비율'] = df['콩'] / df['옥수수']
    
    # 국제곡물 선물가격지수 계산 (밀 20%, 옥수수 40%, 콩 30%, 쌀 10% 가중평균)
    # 표준 인덱스화하기 위해 특정 시작점 기준(예: 100) 대신 가중 가격 자체를 지수 트렌드로 도출
    df['국제곡물_선물가격지수'] = (df['밀_달러톤'] * 0.20) + (df['옥수수_달러톤'] * 0.40) + (df['콩_달러톤'] * 0.30) + (df['쌀_달러톤'] * 0.10)
    
    return df

try:
    df_raw = get_realtime_data()
    latest = df_raw.iloc[-1]
    prev_day = df_raw.iloc[-2]
    prev_year = df_raw.iloc[-252] if len(df_raw) > 252 else df_raw.iloc[0] # 대략 1년 전 영업일
except:
    st.error("실시간 금융 데이터를 불러오는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.")
    st.stop()

# 변동률 계산 함수
def calc_chg(curr, base):
    return ((curr - base) / base) * 100

# ==========================================
# 2. 상단 상위 지표 영역 (Metric Cards)
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(label="🌾 밀 선물", 
              value=f"{int(latest['밀_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['밀_달러톤'], prev_day['밀_달러톤'] Gold):.1f}% (전일) | {calc_chg(latest['밀_달러톤'], prev_year['밀_달러톤']):.1f}% (전년)", delta_color="inverse")
with col2:
    st.metric(label="🌽 옥수수 선물", 
              value=f"{int(latest['옥수수_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['옥수수_달러톤'], prev_day['옥수수_달러톤']):.1f}% (전일) | {calc_chg(latest['옥수수_달러톤'], prev_year['옥수수_달러톤']):.1f}% (전년)", delta_color="inverse")
with col3:
    st.metric(label="🫘 콩 선물", 
              value=f"{int(latest['콩_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['콩_달러톤'], prev_day['콩_달러톤']):.1f}% (전일) | {calc_chg(latest['콩_달러톤'], prev_year['콩_달러톤']):.1f}% (전년)", delta_color="inverse")
with col4:
    st.metric(label="🍚 쌀 수출 (태국)", 
              value=f"{int(latest['쌀_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['쌀_달러톤'], prev_day['쌀_달러톤']):.1f}% (전일) | {calc_chg(latest['쌀_달러톤'], prev_year['쌀_달러톤']):.1f}% (전년)", delta_color="inverse")
with col5:
    # 콩/옥수수 비율에 적정 비율 가이드 결합
    st.markdown(f"""
    <div style="background-color: #fffbeb; border: 1px solid #e2e8f0; border-top: 4px solid #b45309; border-radius: 4px; padding: 12px; text-align: center; height:108px;">
        <div style="font-size: 13px; color: #334155; font-weight: bold;">📊 콩/옥수수 비율</div>
        <div style="font-size: 19px; font-weight: bold; color: #0f172a; margin-top:4px;">{latest['콩_옥수수_비율']:.2f}<span class="sub-text">(적정: 2.50)</span></div>
        <div style="font-size: 11px; color: #64748b; margin-top:4px;">전일 대비 변동: {calc_chg(latest['콩_옥수수_비율'], prev_day['콩_옥수수_비율']):+.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 3. 중간 분할 레이아웃 [좌측: 차트 인터페이스 / 우측: 뉴스 및 거시테이블]
# ==========================================
main_col_left, main_col_right = st.columns([3, 2])

with main_col_left:
    st.markdown('<div class="section-title">📊 곡물 가격 추이</div>', unsafe_allow_html=True)
    
    # 3.1. 컨트롤창 인터페이스 구성 (순서 요구사항 반영)
    c1, c2 = st.columns([2, 2])
    with c1:
        selected_grain = st.selectbox(
            "곡물 선택 :", 
            ["국제곡물 선물가격지수", "밀", "옥수수", "콩", "쌀"], 
            index=0
        )
    with c2:
        period_mapping = {"1달": 30, "3달": 90, "1년": 365, "5년": 1825}
        selected_period = st.selectbox("조회 기간 :", list(period_mapping.keys()), index=1)
    
    # 필터링 및 5MA 계산
    days_to_filter = period_mapping[selected_period]
    filtered_df = df_raw.tail(days_to_filter).copy()
    
    chart_target = '국제곡물_선물가격지수' if selected_grain == "국제곡물 선물가격지수" else f"{selected_grain}_달러톤"
    filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
    
    # Plotly dynamic 차트 생성 (요구한 범례 명칭 하드코딩 반영)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name=selected_grain, line=dict(color='#1e3a8a', width=2.5)))
    fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['5MA'], name="5일 이동평균", line=dict(color='#ea580c', width=2, dash='dash')))
    
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10),
        height=325,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template="plotly_white",
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    st.plotly_chart(fig, use_container_width=True)

with main_col_right:
    # 4.1. 국제곡물 주요 뉴스
    st.markdown('<div class="section-title">📰 국제곡물 주요 뉴스</div>', unsafe_allow_html=True)
    st.markdown("""
    * <span class="news-tag">USDA WASDE</span> 미국 및 남미 주요 곡물 주산지 기후 변동성 증대에 따른 기말재고량 재조정 가능성 언급
    * <span class="news-tag">물류/지정학</span> 흑해 주요 연안 곡물 수출 터미널 통항 정체 및 파나마 운하 통항 지수 변동성 모니터링 강화
    * <span class="news-tag">시장동향</span> 환율 상승 압력에 따른 주요 수입국별 선도구매 물량 헷징 비중 조절 움직임 포착
    """, unsafe_allow_html=True)
    
    # 4.2. 거시지표 추이
    st.markdown('<div class="section-title">🌐 거시지표 추이</div>', unsafe_allow_html=True)
    
    # 가상의 BCI, BSI 해상운임 데이터 생성용 로직 (야후에 해상운임이 없는 한계 보완 모사)
    bci_val, bsi_val = 2450, 1320
    
    macro_data = pd.DataFrame({
        '지표명': ['🛢️ 국제유가 (WTI)', '🛢️ 국제유가 (브렌트)', '🚢 해상운임 (BCI)', '🚢 해상운임 (BSI)', '💵 원/달러 환율'],
        '전일 가격': [f"${latest['WTI']:.2f} / bbl", f"${latest['브렌트']:.2f} / bbl", f"{bci_val} pt", f"{bsi_val} pt", f"{int(latest['환율'])} 원"],
        '전일 대비 증감': [f"{calc_chg(latest['WTI'], prev_day['WTI']):+.1f}%", f"{calc_chg(latest['브렌트'], prev_day['브렌트']):+.1f}%", "-1.0%", "+0.6%", f"{calc_chg(latest['환율'], prev_day['환율']):+.1f}%"],
        '전년 대비 증감': [f"{calc_chg(latest['WTI'], prev_year['WTI']):+.1f}%", f"{calc_chg(latest['브렌트'], prev_year['브렌트']):+.1f}%", "+12.4%", "-3.1%", f"{calc_chg(latest['환율'], prev_year['환율']):+.1f}%"]
    })
    
    # 컬럼명 줄바꿈 요건 반영을 위해 HTML 렌더링 우회 사용 가능하나 명칭 수정 배정
    macro_data.columns = ['지표명', '전일 가격', '전일 대비\n증감', '전년 대비\n증감']
    st.dataframe(macro_data, use_container_width=True, hide_index=True)

# ==========================================
# 5. 하단 수입 추이 영역 (식용 / 사료용 계층형 분할 테이블 모사)
# ==========================================
st.markdown('<div class="section-title">📋 수입 추이</div>', unsafe_allow_html=True)

import_data = pd.DataFrame([
    {"구분": "식용", "품목명": "제분용 밀", "당월 수입량 (톤)": "243,000", "당월 평균 수입단가(달러/톤)": "$282.10", "전월 대비 증감": "▼ -1.5%", "전년 대비 증감": "▼ -6.8%"},
    {"구분": "식용", "품목명": "가공용 옥수수", "당월 수입량 (톤)": "125,000", "당월 평균 수입단가(달러/톤)": "$245.50", "전월 대비 증감": "▲ +3.2%", "전년 대비 증감": "▼ -4.1%"},
    {"구분": "식용", "품목명": "식용 콩", "당월 수입량 (톤)": "15,000", "당월 평균 수입단가(달러/톤)": "$585.00", "전월 대비 증감": "0.0%", "전년 대비 증감": "▲ +1.5%"},
    {"구분": "식용", "품목명": "채유용 콩", "당월 수입량 (톤)": "89,000", "당월 평균 수입단가(달러/톤)": "$495.00", "전월 대비 증감": "▲ +0.8%", "전년 대비 증감": "▼ -9.3%"},
    {"구분": "사료용", "품목명": "사료용 밀", "당월 수입량 (톤)": "180,000", "당월 평균 수입단가(달러/톤)": "$255.00", "전월 대비 증감": "▼ -2.1%", "전년 대비 증감": "▼ -11.0%"},
    {"구분": "사료용", "품목명": "사료용 옥수수", "당월 수입량 (톤)": "310,000", "당월 평균 수입단가(달러/톤)": "$238.00", "전월 대비 증감": "▼ -5.4%", "전년 대비 증감": "▼ -7.2%"},
    {"구분": "사료용", "품목명": "대두박", "당월 수입량 (톤)": "145,000", "당월 평균 수입단가(달러/톤)": "$420.00", "전월 대비 증감": "▲ +1.7%", "전년 대비 증감": "▲ +0.5%"}
])

st.dataframe(import_data, use_container_width=True, hide_index=True)
