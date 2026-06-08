import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ==========================================
# 0. 페이지 기본 설정 및 스타일 정의
# ==========================================
st.set_page_config(
    page_title="국제곡물 모니터링 대시보드",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    .reportview-container, .main { background-color: #f1f5f9; }
    .report-title { font-size: 26px; font-weight: bold; color: #0f172a; border-bottom: 3px solid #0f172a; padding-bottom: 10px; margin-bottom: 20px; }
    .section-title { font-size: 16px; font-weight: bold; color: #0f172a; border-bottom: 2px solid #cbd5e1; padding-bottom: 6px; margin-top: 5px; margin-bottom: 15px; }
    
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #3b82f6;
        border-radius: 4px;
        padding: 12px;
        text-align: center;
    }
    div[data-testid="stMetric"]:nth-child(5) {
        border-top-color: #b45309;
        background-color: #fffbeb;
    }
    .unit-text { font-size: 12px; font-weight: normal; color: #64748b; margin-left: 2px; }
    .sub-text { font-size: 12px; font-weight: normal; color: #b45309; margin-left: 4px; }
    .news-tag { background-color: #f1f5f9; color: #475569; font-weight: bold; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 6px; }
    .news-item { margin-bottom: 10px; font-size: 13px; list-style-type: none; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="report-title">■ 국제곡물 모니터링 대시보드</div>', unsafe_allow_html=True)

# ==========================================
# 1. 구글 스프레드시트(엑셀) 연동 설정
# ==========================================
# 본인의 구글 스프레드시트 주소를 아래에 바르게 붙여넣으세요.
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/시트_아이디_작성_구역/edit?usp=sharing"

@st.cache_data(ttl=30) # 30초 간격으로 동기화하여 실시간성 극대화
def load_excel_data(base_url):
    try:
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        
        # 1) 시황 및 거시지표 로드
        url_macro = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=시황_거시지표"
        df_macro = pd.read_csv(url_macro)
        
        # 2) 시계열 수입 추이 로드
        url_import = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet=수입_추이"
        df_import = pd.read_csv(url_import)
        
        return df_macro, df_import
    except Exception as e:
        st.error(f"데이터 파일 연결 실패. 공유 권한 혹은 컬럼명을 확인하세요. 오류: {e}")
        return None, None

df_macro_raw, df_import_raw = load_excel_data(SPREADSHEET_URL)

if df_macro_raw is None or df_import_raw is None:
    st.stop()

# --- 데이터 가공 프로세스 ---
# 시황 처리
df_macro_raw['날짜'] = pd.to_datetime(df_macro_raw['날짜'])
df_macro = df_macro_raw.sort_values(by='날짜').set_index('날짜')
latest = df_macro.iloc[-1]
prev_day = df_macro.iloc[-2] if len(df_macro) > 1 else latest
prev_year = df_macro.iloc[-252] if len(df_macro) > 252 else df_macro.iloc[0]

# 가중치 복합 지수 연산 (밀20%, 옥수수40%, 콩30%, 쌀10%)
df_macro['국제곡물_선물가격지수'] = (df_macro['밀_달러톤'] * 0.20) + (df_macro['옥수수_달러톤'] * 0.40) + (df_macro['콩_달러톤'] * 0.30) + (df_macro['쌀_달러톤'] * 0.10)

# [신규 수정 기능] 수입 추이 시계열 중 가장 마지막 행(가장 최신 날짜) 데이터 자동 필터링 로직
df_import_raw['날짜'] = pd.to_datetime(df_import_raw['날짜'])
latest_import_date = df_import_raw['날짜'].max() # 시트에 입력된 가장 최신 날짜 확보
df_import_filtered = df_import_raw[df_import_raw['날짜'] == latest_import_date].copy()
df_import_final = df_import_filtered.drop(columns=['날짜']) # 화면 출력용으로 날짜 컬럼 제거

# 변동률 함수
def calc_chg(curr, base):
    if base == 0: return 0.0
    return ((curr - base) / base) * 100

# ==========================================
# 2. 상단 상위 지표 영역 (Metric Cards)
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(label="🌾 밀 선물", value=f"{int(latest['밀_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['밀_달러톤'], prev_day['밀_달러톤']):+.1f}% (전일) | {calc_chg(latest['밀_달러톤'], prev_year['밀_달러톤']):+.1f}% (전년)", delta_color="inverse")
with col2:
    st.metric(label="🌽 옥수수 선물", value=f"{int(latest['옥수수_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['옥수수_달러톤'], prev_day['옥수수_달러톤']):+.1f}% (전일) | {calc_chg(latest['옥수수_달러톤'], prev_year['옥수수_달러톤']):+.1f}% (전년)", delta_color="inverse")
with col3:
    st.metric(label="🥜 콩 선물", value=f"{int(latest['콩_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['콩_달러톤'], prev_day['콩_달러톤']):+.1f}% (전일) | {calc_chg(latest['콩_달러톤'], prev_year['콩_달러톤']):+.1f}% (전년)", delta_color="inverse")
with col4:
    st.metric(label="🍚 쌀 수출 (태국)", value=f"{int(latest['쌀_달러톤'])} 달러/톤", 
              delta=f"{calc_chg(latest['쌀_달러톤'], prev_day['쌀_달러톤']):+.1f}% (전일) | {calc_chg(latest['쌀_달러톤'], prev_year['쌀_달러톤']):+.1f}% (전년)", delta_color="inverse")
with col5:
    st.markdown(f"""
    <div style="background-color: #fffbeb; border: 1px solid #e2e8f0; border-top: 4px solid #b45309; border-radius: 4px; padding: 12px; text-align: center; height:108px;">
        <div style="font-size: 13px; color: #334155; font-weight: bold;">📊 콩/옥수수 비율</div>
        <div style="font-size: 19px; font-weight: bold; color: #0f172a; margin-top:4px;">{latest['콩_옥수수_비율']:.2f}<span class="sub-text">(적정: 2.50)</span></div>
        <div style="font-size: 11px; color: #64748b; margin-top:4px;">전일 대비 변동: {calc_chg(latest['콩_옥수수_비율'], prev_day['콩_옥수수_비율']):+.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 3. 실시간 뉴스 크롤링 연동 (자동화)
# ==========================================
@st.cache_data(ttl=600)
def fetch_realtime_news():
    news_items = []
    try:
        url = "https://news.google.com/rss/search?q=국제곡물+WASDE&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, features="xml")
        articles = soup.findAll("item")[:3]
        for article in articles:
            title = article.title.text.split(" - ")[0]
            source = article.title.text.split(" - ")[1] if " - " in article.title.text else "외신"
            news_items.append({"tag": source, "content": title})
    except:
        news_items = [
            {"tag": "농식품부", "content": "국제곡물 가격 변동성 대응을 위한 민관 합동 재고 점검 및 헷징 전략 고도화 추진"},
            {"tag": "외신종합", "content": "남미 주산지 기후 여건 개선에 따른 소맥 및 옥수수 선물 매도 우위 전개"},
            {"tag": "KREI", "content": "해외 곡물시장 동향 분석 보고서: 환율 압박에 따른 CIF 도입단가 방어 초점"}
        ]
    return news_items

real_news = fetch_realtime_news()

# ==========================================
# 4. 중간 분할 레이아웃
# ==========================================
main_col_left, main_col_right = st.columns([3, 2])

with main_col_left:
    st.markdown('<div class="section-title">📊 곡물 가격 추이</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 2])
    with c1:
        selected_grain = st.selectbox("곡물 선택 :", ["국제곡물 선물가격지수", "밀", "옥수수", "콩", "쌀"], index=0)
    with c2:
        period_mapping = {"1달": 30, "3달": 90, "1년": 365, "5년": 1825}
        selected_period = st.selectbox("조회 기간 :", list(period_mapping.keys()), index=1)
    
    days_to_filter = period_mapping[selected_period]
    filtered_df = df_macro.tail(days_to_filter).copy()
    
    chart_target = '국제곡물_선물가격지수' if selected_grain == "국제곡물 선물가격지수" else f"{selected_grain}_달러톤"
    filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name="국제곡물 선물가격지수" if selected_grain == "국제곡물 선물가격지수" else selected_grain, line=dict(color='#1e3a8a', width=2.5)))
    fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['5MA'], name="5일 이동평균", line=dict(color='#ea580c', width=2, dash='dash')))
    
    fig.update_layout(
        margin=dict(l=10, r=10, t=10, b=10), height=325,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

with main_col_right:
    st.markdown('<div class="section-title">📰 국제곡물 주요 뉴스</div>', unsafe_allow_html=True)
    for item in real_news:
        st.markdown(f'<li class="news-item"><span class="news-tag">{item["tag"]}</span>{item["content"]}</li>', unsafe_allow_html=True)
    
    # [수정 기능] 거시지표 내 해상운임 항목 BPI 및 BSI 전면 매핑
    st.markdown('<div class="section-title">🌐 거시지표 추이</div>', unsafe_allow_html=True)
    macro_data = pd.DataFrame({
        '지표명': ['🛢️ 국제유가 (WTI)', '🛢️ 국제유가 (브렌트)', '🚢 해상운임 (BPI)', '🚢 해상운임 (BSI)', '💵 원/달러 환율'],
        '전일 가격': [f"${latest['WTI']:.2f} / bbl", f"${latest['브렌트']:.2f} / bbl", f"{int(latest['BPI'])} pt", f"{int(latest['BSI'])} pt", f"{int(latest['환율'])} 원"],
        '전일 대비\n증감': [f"{calc_chg(latest['WTI'], prev_day['WTI']):+.1f}%", f"{calc_chg(latest['브렌트'], prev_day['브렌트']):+.1f}%", f"{calc_chg(latest['BPI'], prev_day['BPI']):+.1f}%", f"{calc_chg(latest['BSI'], prev_day['BSI']):+.1f}%", f"{calc_chg(latest['환율'], prev_day['환율']):+.1f}%"],
        '전년 대비\n증감': [f"{calc_chg(latest['WTI'], prev_year['WTI']):+.1f}%", f"{calc_chg(latest['브렌트'], prev_year['브렌트']):+.1f}%", f"{calc_chg(latest['BPI'], prev_year['BPI']):+.1f}%", f"{calc_chg(latest['BSI'], prev_year['BSI']):+.1f}%", f"{calc_chg(latest['환율'], prev_year['환율']):+.1f}%"]
    })
    st.dataframe(macro_data, use_container_width=True, hide_index=True)

# ==========================================
# 5. 하단 수입 추이 영역 (마지막 행 자동 업데이트 뷰 반영)
# ==========================================
formatted_date = latest_import_date.strftime('%Y년 %m월')
st.markdown(f'<div class="section-title">📋 수입 추이 <span style="font-size:12px; font-weight:normal; color:#64748b; margin-left:8px;">(* 가장 최신 데이터 수집 기준일: {formatted_date})</span></div>', unsafe_allow_html=True)
st.dataframe(df_import_final, use_container_width=True, hide_index=True)
