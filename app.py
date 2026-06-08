import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote  # 한글 인코딩을 위한 라이브러리

# ==========================================
# 0. 페이지 기본 설정 및 스타일 정의
# ==========================================
st.set_page_config(
    page_title="국제곡물 모니터링 대시보드",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# UI 및 컬러 마크업 규격 CSS 정의
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
    
    .metric-val-text { font-size: 19px; font-weight: bold; color: #0f172a; }
    .unit-text { font-size: 12px; font-weight: normal; color: #64748b; margin-left: 2px; }
    .sub-text { font-size: 12px; font-weight: normal; color: #b45309; margin-left: 4px; }
    
    /* 동적 컬러 텍스트 양식 */
    .color-up { color: #dc2626; font-weight: bold; }
    .color-down { color: #2563eb; font-weight: bold; }
    .color-flat { color: #64748b; font-weight: bold; }
    
    .news-tag { background-color: #f1f5f9; color: #475569; font-weight: bold; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 6px; }
    .news-item { margin-bottom: 10px; font-size: 13px; list-style-type: none; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="report-title">■ 국제곡물 모니터링 대시보드</div>', unsafe_allow_html=True)

# ==========================================
# 1. 구글 스프레드시트(엑셀) 연동 설정
# ==========================================
# 본인의 구글 스프레드시트 주소를 아래에 바르게 붙여넣으세요.
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/11wCzl6kNsZl-pgHaPQEuWe4iQcGuplyQXhW8WFCNwVE/edit?usp=sharing"

@st.cache_data(ttl=30)
def load_excel_data(base_url):
    try:
        sheet_id = base_url.split("/d/")[1].split("/")[0]
        sheet_macro_encoded = quote("시황_거시지표")
        sheet_import_encoded = quote("수입_추이")
        
        url_macro = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_macro_encoded}"
        df_macro = pd.read_csv(url_macro)
        
        url_import = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_import_encoded}"
        df_import = pd.read_csv(url_import)
        
        return df_macro, df_import
    except Exception as e:
        st.error(f"데이터 파일 연결 실패. 공유 권한 혹은 컬럼명을 확인하세요. 오류: {e}")
        return None, None

df_macro_raw, df_import_raw = load_excel_data(SPREADSHEET_URL)

if df_macro_raw is None or df_import_raw is None:
    st.stop()

# --- 데이터 가공 및 정렬 ---
df_macro_raw['날짜'] = pd.to_datetime(df_macro_raw['날짜'])
df_macro = df_macro_raw.sort_values(by='날짜').set_index('날짜')

latest = df_macro.iloc[-1]
prev_day = df_macro.iloc[-2] if len(df_macro) > 1 else latest
prev_year = df_macro.iloc[-252] if len(df_macro) > 252 else df_macro.iloc[0]

# 가중치 비율 세팅 (밀 32%, 옥수수 28%, 콩 38%, 쌀 2%)
df_macro['국제곡물_선물가격지수'] = (df_macro['밀_달러톤'].fillna(0) * 0.32) + \
                          (df_macro['옥수수_달러톤'].fillna(0) * 0.28) + \
                          (df_macro['콩_달러톤'].fillna(0) * 0.38) + \
                          (df_macro['쌀_달러톤'].fillna(0) * 0.02)

all_nan_mask = df_macro[['밀_달러톤', '옥수수_달러톤', '콩_달러톤', '쌀_달러톤']].isna().all(axis=1)
df_macro.loc[all_nan_mask, '국제곡물_선물가격지수'] = None

# 수입 추이 데이터 필터링
df_import_raw['날짜'] = pd.to_datetime(df_import_raw['날짜'])
latest_import_date = df_import_raw['날짜'].max()
df_import_filtered = df_import_raw[df_import_raw['날짜'] == latest_import_date].copy()
df_import_final = df_import_filtered.drop(columns=['날짜'])

# ==========================================
# 수치 판정 및 HTML 변환 유틸리티 함수
# ==========================================
def get_colored_chg_html(curr, base):
    if pd.isna(curr) or pd.isna(base) or base == 0:
        return '<span class="color-flat">-</span>'
    
    val = ((curr - base) / base) * 100
    if val > 0:
        return f'<span class="color-up">▲+{val:.1f}%</span>'
    elif val < 0:
        return f'<span class="color-down">▼{val:.1f}%</span>'
    else:
        return f'<span class="color-flat">0.0%</span>'

def render_metric_card(label, curr_val, base_day, base_year, unit="달러/톤", is_ratio=False):
    if pd.isna(curr_val):
        value_html = '<span class="metric-val-text">N/A</span>'
        delta_html = '<div style="font-size:11px; color:#64748b; margin-top:4px;">-</div>'
    else:
        if is_ratio:
            value_html = f'<span class="metric-val-text">{curr_val:.2f}</span><span class="sub-text">(적정: 2.50)</span>'
            chg_day = get_colored_chg_html(curr_val, base_day)
            delta_html = f'<div style="font-size:11px; color:#64748b; margin-top:4px;">전일 대비 변동: {chg_day}</div>'
        else:
            value_html = f'<span class="metric-val-text">{int(float(curr_val))}</span><span class="unit-text">{unit}</span>'
            chg_day = get_colored_chg_html(curr_val, base_day)
            chg_yr = get_colored_chg_html(curr_val, base_year)
            delta_html = f'<div style="font-size:11px; margin-top:4px;">{chg_day} (전일) | {chg_yr} (전년)</div>'

    card_bg = "#fffbeb" if is_ratio else "#f8fafc"
    card_border = "#b45309" if is_ratio else "#3b82f6"
    
    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid #e2e8f0; border-top: 4px solid {card_border}; border-radius: 4px; padding: 12px; text-align: center; height:108px; width:100%;">
        <div style="font-size: 13px; color: #334155; font-weight: bold;">{label}</div>
        <div style="margin-top:4px;">{value_html}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def format_macro_val(val, prefix="", suffix=""):
    if pd.isna(val): return "N/A"
    try:
        if "bbl" in suffix: return f"{prefix}{float(val):.2f}{suffix}"
        return f"{prefix}{int(float(val))}{suffix}"
    except: return f"{val}"

# ==========================================
# 2. 상단 상위 지표 영역 (Metric Cards)
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    render_metric_card("🌾 밀 선물", latest['밀_달러톤'], prev_day['밀_달러톤'], prev_year['밀_달러톤'])
with col2:
    render_metric_card("🌽 옥수수 선물", latest['옥수수_달러톤'], prev_day['옥수수_달러톤'], prev_year['옥수수_달러톤'])
with col3:
    render_metric_card("🫘 콩 선물", latest['콩_달러톤'], prev_day['콩_달러톤'], prev_year['콩_달러톤'])
with col4:
    render_metric_card("🍚 쌀 수출 (태국)", latest['쌀_달러톤'], prev_day['쌀_달러톤'], prev_year['쌀_달러톤'])
with col5:
    render_metric_card("📊 콩/옥수수 비율", latest['콩_옥수수_비율'], prev_day['콩_옥수수_비율'], None, is_ratio=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 3. 실시간 뉴스 크롤링 연동 ([해결책] 한글 쿼리 인코딩 적용)
# ==========================================
@st.cache_data(ttl=600)
def fetch_realtime_news():
    news_items = []
    try:
        # [수정] 뉴스 검색어 주소창의 한글 파트를 quote()로 묶어 아스키 에러 완전 방지
        query_encoded = quote("국제곡물 WASDE")
        url = f"https://news.google.com/rss/search?q={query_encoded}&hl=ko&gl=KR&ceid=KR:ko"
        
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
    
    if filtered_df[chart_target].isna().all():
        st.warning("선택한 기간 내에 분석할 시황 데이터가 엑셀에 존재하지 않습니다.")
    else:
        # 선형 보간법(Linear Interpolation) 적용 후 5MA 연산 (결측 단절 방지)
        filtered_df[chart_target] = filtered_df[chart_target].interpolate(method='linear', limit_direction='both')
        filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name="국제곡물 선물가격지수" if selected_grain == "국제곡물 선물가격지수" else selected_grain, connectgaps=True, line=dict(color='#1e3a8a', width=2.5)))
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['5MA'], name="5일 이동평균", connectgaps=True, line=dict(color='#ea580c', width=2, dash='dash')))
        
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
    
    st.markdown('<div class="section-title">🌐 거시지표 추이</div>', unsafe_allow_html=True)
    
    # 거시지표 동적 컬러 마크업 연동 html 테이블 구조화
    macro_table_html = f"""
    <table style="width:100%; border-collapse:collapse; font-size:12px; text-align:center;">
        <thead style="background-color:#f8fafc; color:#475569;">
            <tr style="border-bottom:1px solid #cbd5e1;">
                <th style="padding:8px; text-align:left;">지표명</th>
                <th style="padding:8px;">전일 가격</th>
                <th style="padding:8px;">전일 대비<br>증감</th>
                <th style="padding:8px;">전년 대비<br>증감</th>
            </tr>
        </thead>
        <tbody style="color:#1e293b;">
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:8px; text-align:left; font-weight:bold;">🛢️ 국제유가 (WTI)</td>
                <td>{format_macro_val(latest['WTI'], "$", " / bbl")}</td>
                <td>{get_colored_chg_html(latest['WTI'], prev_day['WTI'])}</td>
                <td>{get_colored_chg_html(latest['WTI'], prev_year['WTI'])}</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:8px; text-align:left; font-weight:bold;">🛢️ 국제유가 (브렌트)</td>
                <td>{format_macro_val(latest['브렌트'], "$", " / bbl")}</td>
                <td>{get_colored_chg_html(latest['브렌트'], prev_day['브렌트'])}</td>
                <td>{get_colored_chg_html(latest['브렌트'], prev_year['브렌트'])}</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:8px; text-align:left; font-weight:bold;">🚢 해상운임 (BPI)</td>
                <td>{format_macro_val(latest['BPI'], "", " pt")}</td>
                <td>{get_colored_chg_html(latest['BPI'], prev_day['BPI'])}</td>
                <td>{get_colored_chg_html(latest['BPI'], prev_year['BPI'])}</td>
            </tr>
            <tr style="border-bottom:1px solid #f1f5f9;">
                <td style="padding:8px; text-align:left; font-weight:bold;">🚢 해상운임 (BSI)</td>
                <td>{format_macro_val(latest['BSI'], "", " pt")}</td>
                <td>{get_colored_chg_html(latest['BSI'], prev_day['BSI'])}</td>
                <td>{get_colored_chg_html(latest['BSI'], prev_year['BSI'])}</td>
            </tr>
            <tr>
                <td style="padding:8px; text-align:left; font-weight:bold;">💵 원/달러 환율</td>
                <td>{format_macro_val(latest['환율'], "", " 원")}</td>
                <td>{get_colored_chg_html(latest['환율'], prev_day['환율'])}</td>
                <td>{get_colored_chg_html(latest['환율'], prev_year['환율'])}</td>
            </tr>
        </tbody>
    </table>
    """
    st.markdown(macro_table_html, unsafe_allow_html=True)

# ==========================================
# 5. 하단 수입 추이 영역
# ==========================================
formatted_date = latest_import_date.strftime('%Y년 %m월')
st.markdown(f'<div class="section-title">📋 수입 추이 <span style="font-size:12px; font-weight:normal; color:#64748b; margin-left:8px;">(* 가장 최신 데이터 수집 기준일: {formatted_date})</span></div>', unsafe_allow_html=True)

df_import_final = df_import_final.fillna("N/A")
st.dataframe(df_import_final, use_container_width=True, hide_index=True)
