import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote

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
    .title-thin { font-weight: 300; font-size: 18px; color: #475569; margin-left: 10px; }
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
    
    .reason-section-box {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .reason-card {
        background-color: #f8fafc;
        border-left: 4px solid #475569;
        padding: 10px 14px;
        margin-bottom: 8px;
        border-radius: 0 4px 4px 0;
    }
    .reason-card-title { font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 4px; }
    .reason-card-text { font-size: 12px; color: #475569; line-height: 1.5; }
    
    .color-up { color: #dc2626; font-weight: bold; }
    .color-down { color: #2563eb; font-weight: bold; }
    .color-flat { color: #64748b; font-weight: bold; }
    
    .news-tag { background-color: #f1f5f9; color: #475569; font-weight: bold; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 6px; display: inline-block; }
    .news-item { margin-bottom: 10px; font-size: 11px; list-style-type: none; color: #1e293b; }
    
    .dashboard-table { width:100%; border-collapse:collapse; font-size:12px; font-family:'Malgun Gothic', sans-serif; text-align:center; }
    .dashboard-table thead { background-color:#f8fafc; color:#475569; }
    .dashboard-table th { padding:8px; font-weight:bold; border-bottom:1px solid #cbd5e1; text-align:center !important; }
    .dashboard-table td { padding:8px; border-bottom:1px solid #f1f5f9; vertical-align:middle; color:#1e293b; text-align:center !important; }
    .dashboard-table tr:nth-child(even) { background-color:#f8fafc; }
    .table-text-left { text-align: left !important; font-weight: bold; }
    .category-cell-style { background-color: #f8fafc; font-weight: bold; color: #334155; border-right: 1px solid #e2e8f0; text-align:center !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. 구글 스프레드시트 데이터 연동 엔지니어링
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/11wCzl6kNsZl-pgHaPQEuWe4iQcGuplyQXhW8WFCNwVE/edit?usp=sharing"

@st.cache_data(ttl=30)
def load_excel_data(base_url):
    try:
        if "/d/" in base_url: sheet_id = base_url.split("/d/")[1].split("/")[0]
        else: sheet_id = base_url
            
        sheet_macro_encoded = quote("시황_거시지표")
        sheet_import_encoded = quote("수입_추이")
        sheet_fao_encoded = quote("FAO_지수")
        
        url_macro = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_macro_encoded}"
        df_macro = pd.read_csv(url_macro)
        
        url_import = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_import_encoded}"
        df_import = pd.read_csv(url_import)
        
        url_fao = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_fao_encoded}"
        df_fao = pd.read_csv(url_fao)
        
        return df_macro, df_import, df_fao
    except Exception as e:
        st.error(f"데이터 파일 연결 실패: {e}")
        return None, None, None

df_macro_raw, df_import_raw, df_fao_raw = load_excel_data(SPREADSHEET_URL)

if df_macro_raw is None or df_import_raw is None or df_fao_raw is None:
    st.stop()

# --- 데이터 가공 및 정렬 ---
df_macro_raw['날짜'] = pd.to_datetime(df_macro_raw['날짜'])
df_macro = df_macro_raw.sort_values(by='날짜').set_index('날짜')

latest = df_macro.iloc[-1]
prev_day = df_macro.iloc[-2] if len(df_macro) > 1 else latest
prev_year = df_macro.iloc[-252] if len(df_macro) > 252 else df_macro.iloc[0]

latest_macro_date = df_macro.index.max()
latest_macro_date_str = latest_macro_date.strftime('%Y.%m.%d')
header_date_style = f"{latest_macro_date.month}월 {latest_macro_date.day}일"

st.markdown(f'<div class="report-title">■ 국제곡물 모니터링 대시보드<span class="title-thin">(업데이트: {latest_macro_date_str})</span></div>', unsafe_allow_html=True)

def clean_numeric(val):
    if pd.isna(val): return 0.0
    try:
        clean_str = str(val).replace('$', '').replace('pt', '').replace('원', '').replace('/bbl', '').replace(',', '').strip()
        return float(clean_str)
    except: return 0.0

df_macro['국제곡물_선물가격지수'] = (df_macro['밀_달러톤'].apply(clean_numeric) * 0.32) + \
                          (df_macro['옥수수_달러톤'].apply(clean_numeric) * 0.28) + \
                          (df_macro['콩_달러톤'].apply(clean_numeric) * 0.38) + \
                          (df_macro['쌀_달러톤'].apply(clean_numeric) * 0.02)

all_nan_mask = df_macro[['밀_달러톤', '옥수수_달러톤', '콩_달러톤', '쌀_달러톤']].isna().all(axis=1)
df_macro.loc[all_nan_mask, '국제곡물_선물가격지수'] = None

# ==========================================
# 수치 판정 및 HTML 변환 유틸리티 함수
# ==========================================
def sanitize_string(val):
    if pd.isna(val): return ""
    return str(val).replace('\\', '').replace('"', '').replace("'", "").strip()

def get_colored_chg_html(curr, base):
    try:
        if pd.isna(curr) or pd.isna(base): return '<span class="color-flat">-</span>'
        c_num = float(str(curr).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        b_num = float(str(base).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        if b_num == 0: return '<span class="color-flat">-</span>'
        val = ((c_num - b_num) / b_num) * 100
        if val > 0: return f'<span class="color-up">▲+{val:.1f}%</span>'
        elif val < 0: return f'<span class="color-down">▼{val:.1f}%</span>'
        else: return f'<span class="color-flat">0.0%</span>'
    except: return '<span class="color-flat">-</span>'

def render_metric_card(label, curr_val, base_day, base_year, unit="달러/톤", is_ratio=False):
    try:
        val_clean = curr_val.iloc[0] if isinstance(curr_val, pd.Series) else curr_val
        b_day_clean = base_day.iloc[0] if isinstance(base_day, pd.Series) else base_day
        b_yr_clean = base_year.iloc[0] if isinstance(base_year, pd.Series) else base_year

        if is_ratio:
            value_html = f'<span class="metric-val-text">{float(val_clean):.2f}</span><span class="sub-text">(적정: 2.50)</span>'
            delta_html = f'<div style="font-size:11px; color:#64748b; margin-top:4px;">전일 대비 변동: {get_colored_chg_html(val_clean, b_day_clean)}</div>'
        else:
            value_html = f'<span class="metric-val-text">{int(float(str(val_clean).replace(",","")))}</span><span class="unit-text">{unit}</span>'
            delta_html = f'<div style="font-size:11px; margin-top:4px;">{get_colored_chg_html(val_clean, b_day_clean)} (전일) | {get_colored_chg_html(val_clean, b_yr_clean)} (전년)</div>'
    except:
        value_html = '<span class="metric-val-text">N/A</span>'
        delta_html = '<div style="font-size:11px; color:#64748b; margin-top:4px;">-</div>'

    card_bg = "#fffbeb" if is_ratio else "#f8fafc"
    card_border = "#3b82f6" if not is_ratio else "#b45309"
    
    st.markdown(f"""
    <div style="background-color: {card_bg}; border: 1px solid #e2e8f0; border-top: 4px solid {card_border}; border-radius: 4px; padding: 12px; text-align: center; height:108px; width:100%;">
        <div style="font-size: 13px; color: #334155; font-weight: bold;">{label}</div>
        <div style="margin-top:4px;">{value_html}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)

def format_macro_val(val, prefix="", suffix="", is_currency=False):
    if pd.isna(val): return "N/A"
    try:
        clean_val = float(str(val).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        if "bbl" in suffix: return f"{prefix}{clean_val:.2f}{suffix}"
        if is_currency or "pt" in suffix or "원" in suffix: return f"{prefix}{int(clean_val):,}{suffix}"
        return f"{prefix}{int(clean_val)}{suffix}"
    except: return f"{val}"

# ==========================================
# 2. 상단 상위 지표 영역
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)
with col1: render_metric_card("🌾 밀 선물", latest['밀_달러톤'], prev_day['밀_달러톤'], prev_year['밀_달러톤'])
with col2: render_metric_card("🌽 옥수수 선물", latest['옥수수_달러톤'], prev_day['옥수수_달러톤'], prev_year['옥수수_달러톤'])
with col3: render_metric_card("🥜 콩 선물", latest['콩_달러톤'], prev_day['콩_달러톤'], prev_year['콩_달러톤'])
with col4: render_metric_card("🍚 쌀 수출 (태국)", latest['쌀_달러톤'], prev_day['쌀_달러톤'], prev_year['쌀_달러톤'])
with col5: render_metric_card("📊 콩/옥수수 비율", latest['콩_옥수수_비율'], prev_day['콩_옥수수_비율'], None, is_ratio=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 3. 주요 곡물 일일 시황 영역
# ==========================================
try:
    sheet_reason_wheat = sanitize_string(latest.iloc[6]) if len(latest) >= 7 and pd.notna(latest.iloc[6]) else "작성된 밀 시황이 시트에 존재하지 않습니다."
    sheet_reason_corn = sanitize_string(latest.iloc[7]) if len(latest) >= 8 and pd.notna(latest.iloc[7]) else "작성된 옥수수 시황이 시트에 존재하지 않습니다."
    sheet_reason_soybean = sanitize_string(latest.iloc[8]) if len(latest) >= 9 and pd.notna(latest.iloc[8]) else "작성된 콩 시황이 시트에 존재하지 않습니다."
except:
    sheet_reason_wheat = "시황 컬럼(G) 구성 요소를 찾을 수 없습니다."
    sheet_reason_corn = "시황 컬럼(H) 구성 요소를 찾을 수 없습니다."
    sheet_reason_soybean = "시황 컬럼(I) 구성 요소를 찾을 수 없습니다."

st.markdown(f'<div class="section-title">💡 주요 곡물 일일 시황({header_date_style})</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="reason-section-box">
    <div class="reason-card" style="border-left-color: #1e3a8a;">
        <div class="reason-card-title">🌾 밀 선물 (Wheat Briefing)</div>
        <div class="reason-card-text">{sheet_reason_wheat}</div>
    </div>
    <div class="reason-card" style="border-left-color: #ea580c;">
        <div class="reason-card-title">🌽 옥수수 선물 (Corn Briefing)</div>
        <div class="reason-card-text">{sheet_reason_corn}</div>
    </div>
    <div class="reason-card" style="border-left-color: #b45309;">
        <div class="reason-card-title">🥜 콩 선물 (Soybean Briefing)</div>
        <div class="reason-card-text">{sheet_reason_soybean}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 4. 거시경제 주요 뉴스 자동 크롤링 영역
# ==========================================
@st.cache_data(ttl=600)
def fetch_global_macro_news():
    news_items = []
    macro_query = "(omdc OR 'crude oil' OR freight OR Fed interest OR logistics OR tariff) (reuters OR bloomberg)"
    try:
        url = f"https://news.google.com/rss/search?q={quote(macro_query)}&hl=ko&gl=KR&ceid=KR:ko"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, features="xml")
        articles = soup.findAll("item")
        for article in articles:
            title = article.title.text.split(" - ")[0]
            source = article.title.text.split(" - ")[1] if " - " in article.title.text else "외신종합"
            if any(k in title.lower() for k in ["cbot", "소맥", "옥수수 가격", "대두 가격"]): continue
            if any(k in source for k in ["KREI", "한국농촌경제연구원", "농촌경제연구원"]): continue
            news_items.append({"tag": source, "content": title})
            if len(news_items) == 4: break
    except: pass
    if not news_items:
        news_items = [
            {"tag": "Reuters", "content": "글로벌 달러 인덱스 혼조세 속 연준 금리 향방 불확실성에 원자재 리스크 연동 우려"},
            {"tag": "Bloomberg", "content": "해상 물류 공급망 긴장 고조 및 파나마 수에즈 운하 통항 수치 모니터링 강화"},
            {"tag": "외신종합", "content": "국제 유가 공급 역학 관계 재편 가능성에 따른 원자재 자금 유출입 변동 전개"},
            {"tag": "에너지포커스", "content": "글로벌 비료 원료 공급 안정성 점검 및 유가 변동성에 따른 운임 압박 지속"}
        ]
    return news_items

macro_news_list = fetch_global_macro_news()

# ==========================================
# 5. 중간 분할 레이아웃
# ==========================================
main_col_left, main_col_right = st.columns([3, 2])

with main_col_left:
    # ----------------------------------------------------
    # 파트 A: 곡물 가격 추이 섹션
    # ----------------------------------------------------
    st.markdown('<div class="section-title">📊 곡물 가격 추이</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([2, 2])
    with c1: selected_grain = st.selectbox("곡물 선택 :", ["국제곡물 선물가격지수", "밀", "옥수수", "콩", "쌀"], index=0)
    with c2:
        period_options = ["1개월", "6개월", "1년", "3년", "5년", "10년", "기간 설정"]
        selected_period = st.selectbox("조회 기간 :", period_options, index=2)
    
    max_available_date = df_macro.index.max()
    
    if selected_period == "1개월": start_date = max_available_date - pd.Timedelta(days=30)
    elif selected_period == "6개월": start_date = max_available_date - pd.Timedelta(days=182)
    elif selected_period == "1년": start_date = max_available_date - pd.Timedelta(days=365)
    elif selected_period == "3년": start_date = max_available_date - pd.Timedelta(days=1095)
    elif selected_period == "5년": start_date = max_available_date - pd.Timedelta(days=1825)
    elif selected_period == "10년": start_date = max_available_date - pd.Timedelta(days=3650)
    else:
        st.markdown("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True)
        date_range = st.date_input(
            "분석 범위 지정:",
            value=(max_available_date - pd.Timedelta(days=365), max_available_date),
            min_value=df_macro.index.min().to_pydatetime(),
            max_value=max_available_date.to_pydatetime()
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        else:
            start_date, end_date = max_available_date - pd.Timedelta(days=365), max_available_date

    if selected_period != "기간 설정": end_date = max_available_date

    filtered_df = df_macro.loc[start_date:end_date].copy()
    chart_target = '국제곡물_선물가격지수' if selected_grain == "국제곡물 선물가격지수" else f"{selected_grain}_달러톤"
    
    if filtered_df.empty or filtered_df[chart_target].isna().all():
        st.warning("선택한 범위 내에 분석할 가격 시황 데이터가 시트에 존재하지 않습니다.")
    else:
        filtered_df[chart_target] = filtered_df[chart_target].apply(lambda x: clean_numeric(x) if pd.notna(x) else None)
        filtered_df[chart_target] = filtered_df[chart_target].interpolate(method='linear', limit_direction='both')
        filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name=selected_grain, connectgaps=True, line=dict(color='#1e3a8a', width=2.5)))
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['5MA'], name="5일 이동평균", connectgaps=True, line=dict(color='#ea580c', width=2, dash='dot')))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

    # ----------------------------------------------------
    # 파트 B: [고도화 반영] FAO 식품가격지수 추이 분석 섹션
    # ----------------------------------------------------
    st.markdown('<div class="section-title">🇺🇳 FAO 식품가격지수 분석</div>', unsafe_allow_html=True)
    
    if df_fao_raw.empty or len(df_fao_raw) < 1:
        st.info("💡 구글 스프레드시트의 'FAO_지수' 데이터를 파싱하는 데 실패했습니다.")
    else:
        try:
            df_fao_raw['날짜'] = pd.to_datetime(df_fao_raw['날짜'])
            df_fao_base = df_fao_raw.sort_values(by='날짜').copy()
            
            # 수치형 전처리 정제 보증
            fao_cols_map = {
                '식품가격지수': '식품가격지수', '곡물': '곡물', '유지류': '유지류', 
                '축산물': '축산물', '유제품': '유제품', '설탕': '설탕'
            }
            for col in fao_cols_map.keys():
                if col in df_fao_base.columns:
                    df_fao_base[col] = df_fao_base[col].apply(clean_numeric)

            # [요청 3] 지수 선택 필터 세팅
            f_col1, f_col2 = st.columns([2, 2])
            with f_col1:
                selected_fao_idx = st.selectbox(
                    "지수 선택 :", 
                    ["전체 지수 보기", "식품가격지수", "곡물", "유지류", "축산물", "유제품", "설탕"], 
                    index=0,
                    key="fao_idx_select"
                )
            with f_col2:
                selected_fao_period = st.selectbox(
                    "조회 기간 :", 
                    ["6개월", "1년", "3년", "5년", "전체 기간", "기간 설정"], 
                    index=2,
                    key="fao_period_select"
                )

            max_fao_date = df_fao_base['날짜'].max()
            
            if selected_fao_period == "6개월": f_start = max_fao_date - pd.Timedelta(days=182)
            elif selected_fao_period == "1년": f_start = max_fao_date - pd.Timedelta(days=365)
            elif selected_fao_period == "3년": f_start = max_fao_date - pd.Timedelta(days=1095)
            elif selected_fao_period == "5년": f_start = max_fao_date - pd.Timedelta(days=1825)
            elif selected_fao_period == "전체 기간": f_start = df_fao_base['날짜'].min()
            else:
                st.markdown("<div style='margin-top: -10px;'></div>", unsafe_allow_html=True)
                fao_range = st.date_input(
                    "FAO 분석 범위 지정:",
                    value=(max_fao_date - pd.Timedelta(days=1095), max_fao_date),
                    min_value=df_fao_base['날짜'].min().to_pydatetime(),
                    max_value=max_fao_date.to_pydatetime(),
                    key="fao_date_picker"
                )
                if isinstance(fao_range, tuple) and len(fao_range) == 2:
                    f_start, f_end = pd.Timestamp(fao_range[0]), pd.Timestamp(fao_range[1])
                else:
                    f_start, f_end = max_fao_date - pd.Timedelta(days=1095), max_fao_date

            if selected_fao_period != "기간 설정": f_end = max_fao_date

            df_fao_filtered = df_fao_base[(df_fao_base['날짜'] >= f_start) & (df_fao_base['날짜'] <= f_end)].copy()

            fig_fao = go.Figure()
            
            # 트레이스 정의용 사전 세팅 (지정 순서 및 라인 스타일 수치화 정의)
            trace_specs = [
                {'col': '식품가격지수', 'name': '식품가격지수', 'color': '#0f172a', 'width': 3.5, 'dash': 'solid', 'mode': 'lines'},
                {'col': '곡물', 'name': '곡물', 'color': '#ea580c', 'width': 2.5, 'dash': 'solid', 'mode': 'lines+markers'},
                {'col': '유지류', 'name': '유지류', 'color': '#2563eb', 'width': 2.5, 'dash': 'solid', 'mode': 'lines'},
                {'col': '축산물', 'name': '축산물', 'color': '#94a3b8', 'width': 1.2, 'dash': 'dot', 'mode': 'lines'},
                {'col': '유제품', 'name': '유제품', 'color': '#cbd5e1', 'width': 1.2, 'dash': 'dot', 'mode': 'lines'},
                {'col': '설탕', 'name': '설탕', 'color': '#e2e8f0', 'width': 1.2, 'dash': 'dashdot', 'mode': 'lines'}
            ]

            for spec in trace_specs:
                if spec['col'] in df_fao_filtered.columns:
                    # 특정 지수만 선택한 경우, 선택되지 않은 트레이스는 패스
                    if selected_fao_idx != "전체 지수 보기" and selected_fao_idx != spec['name']:
                        continue
                        
                    fig_fao.add_trace(go.Scatter(
                        x=df_fao_filtered['날짜'], 
                        y=df_fao_filtered[spec['col']], 
                        name=spec['name'],  # [요청 2] 아이콘 제거된 깨끗한 명칭 매핑
                        mode=spec['mode'],
                        line=dict(color=spec['color'], width=spec['width'], dash=spec['dash']),
                        marker=dict(size=4) if 'markers' in spec['mode'] else None
                    ))
            
            # [요청 1] 그래프 제목 설정 및 레이아웃 정의
            fig_fao.update_layout(
                title=dict(text="FAO 식품가격지수 추이", font=dict(size=14, color="#0f172a", family="Malgun Gothic")),
                margin=dict(l=10, r=10, t=40, b=10), 
                height=260, 
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="left", 
                    x=0,
                    traceorder="normal" # 스펙 배열 순서대로 노출 유도 보증
                ), 
                template="plotly_white",
                xaxis=dict(tickformat="%Y-%m")
            )
            st.plotly_chart(fig_fao, use_container_width=True)
        except Exception as fao_err:
            st.error(f"FAO 지수 필터 가공 에러: {fao_err}")

with main_col_right:
    st.markdown(f'<div class="section-title">📰 주요 뉴스({header_date_style})</div>', unsafe_allow_html=True)
    for item in macro_news_list:
        st.markdown(f'<li class="news-item"><span class="news-tag">{item["tag"]}</span>{item["content"]}</li>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">🌐 거시지표 추이</div>', unsafe_allow_html=True)
    
    macro_table_html = f"""
    <table class="dashboard-table">
        <thead>
            <tr>
                <th style="width:35%;">주요 지표</th>
                <th style="width:25%;">당일 추이</th>
                <th style="width:20%;">전일 대비</th>
                <th style="width:20%;">전년 대비</th>
            </tr>
        </thead>
        <tbody>
            <tr><td class="table-text-left">⛽ 국제유가 (WTI)</td><td>{format_macro_val(latest['WTI'], "$", " / bbl")}</td><td>{get_colored_chg_html(latest['WTI'], prev_day['WTI'])}</td><td>{get_colored_chg_html(latest['WTI'], prev_year['WTI'])}</td></tr>
            <tr><td class="table-text-left">⛽ 국제유가 (브렌트)</td><td>{format_macro_val(latest['브렌트'], "$", " / bbl")}</td><td>{get_colored_chg_html(latest['브렌트'], prev_day['브렌트'])}</td><td>{get_colored_chg_html(latest['브렌트'], prev_year['브렌트'])}</td></tr>
            <tr><td class="table-text-left">🚢 해상운임 (BPI)</td><td>{format_macro_val(latest['BPI'], "", " pt")}</td><td>{get_colored_chg_html(latest['BPI'], prev_day['BPI'])}</td><td>{get_colored_chg_html(latest['BPI'], prev_year['BPI'])}</td></tr>
            <tr><td class="table-text-left">🚢 해상운임 (BSI)</td><td>{format_macro_val(latest['BSI'], "", " pt")}</td><td>{get_colored_chg_html(latest['BSI'], prev_day['BSI'])}</td><td>{get_colored_chg_html(latest['BSI'], prev_year['BSI'])}</td></tr>
            <tr><td class="table-text-left">💵 원/달러 환율</td><td>{format_macro_val(latest['환율'], "", " 원", is_currency=True)}</td><td>{get_colored_chg_html(latest['환율'], prev_day['환율'])}</td><td>{get_colored_chg_html(latest['환율'], prev_year['환율'])}</td></tr>
        </tbody>
    </table>
    """
    st.markdown(macro_table_html, unsafe_allow_html=True)

# ==========================================
# 6. 하단 수입 추이 영역
# ==========================================
df_import_raw['날짜'] = pd.to_datetime(df_import_raw['날짜'])
latest_import_date = df_import_raw['날짜'].max()
formatted_date = latest_import_date.strftime('%Y년 %m월')
st.markdown(f'<div class="section-title">🚢 수입 추이 <span style="font-size:12px; font-weight:normal; color:#64748b; margin-left:8px;">(* 가장 최신 데이터 수집 기준일: {formatted_date})</span></div>', unsafe_allow_html=True)

df_clean_imp = df_import_raw.copy()
df_clean_imp['평균 수입단가(달러/톤)'] = df_clean_imp['평균 수입단가(달러/톤)'].apply(clean_numeric)
pivot_price = df_clean_imp.pivot_table(index='날짜', columns='품목명', values='평균 수입단가(달러/톤)', aggfunc='first')

df_import_filtered = df_import_raw[df_import_raw['날짜'] == latest_import_date].copy()
food_df = df_import_filtered[df_import_filtered['구분'] == '식용']
feed_df = df_import_filtered[df_import_filtered['구분'] == '사료용']

import_rows_html = ""

# --- 식용 데이터 연산 루프 ---
for idx, row in enumerate(food_df.to_dict('records')):
    item_name = sanitize_string(row.get('품목명', ''))
    w_clean = str(row.get('수입량(톤)', 'N/A')).replace(',', '').strip()
    p_curr = clean_numeric(row.get('평균 수입단가(달러/톤)', 0))
    
    weight_display = f"{int(float(w_clean)):,}" if pd.notna(row.get('수입량(톤)')) and w_clean.lower() != 'n/a' else "N/A"
    price_display = f"${p_curr:.2f}" if p_curr > 0 else "N/A"
    
    p_prev_month, p_prev_year = 0.0, 0.0
    if item_name in pivot_price.columns:
        past_months = pivot_price.index[pivot_price.index < latest_import_date]
        if len(past_months) > 0: p_prev_month = pivot_price.loc[past_months[-1], item_name]
        past_years = pivot_price.index[(pivot_price.index.year == latest_import_date.year - 1) & (pivot_price.index.month == latest_import_date.month)]
        if len(past_years) > 0: p_prev_year = pivot_price.loc[past_years[0], item_name]

    td_month_chg = get_colored_chg_html(p_curr, p_prev_month)
    td_year_chg = get_colored_chg_html(p_curr, p_prev_year)
    
    category_td = f'<td class="category-cell-style" rowspan="{len(food_df)}">식용</td>' if idx == 0 else ""
    import_rows_html += "<tr>" + category_td + "<td class='table-text-left'>" + item_name + "</td><td>" + weight_display + "</td><td>" + price_display + "</td><td>" + td_month_chg + "</td><td>" + td_year_chg + "</td></tr>"

# --- 사료용 데이터 연산 루프 ---
for idx, row in enumerate(feed_df.to_dict('records')):
    item_name = sanitize_string(row.get('품목명', ''))
    w_clean = str(row.get('수입량(톤)', 'N/A')).replace(',', '').strip()
    p_curr = clean_numeric(row.get('평균 수입단가(달러/톤)', 0))
    
    weight_display = f"{int(float(w_clean)):,}" if pd.notna(row.get('수입량(톤)')) and w_clean.lower() != 'n/a' else "N/A"
    price_display = f"${p_curr:.2f}" if p_curr > 0 else "N/A"
    
    p_prev_month, p_prev_year = 0.0, 0.0
    if item_name in pivot_price.columns:
        past_months = pivot_price.index[pivot_price.index < latest_import_date]
        if len(past_months) > 0: p_prev_month = pivot_price.loc[past_months[-1], item_name]
        past_years = pivot_price.index[(pivot_price.index.year == latest_import_date.year - 1) & (pivot_price.index.month == latest_import_date.month)]
        if len(past_years) > 0: p_prev_year = pivot_price.loc[past_years[0], item_name]

    td_month_chg = get_colored_chg_html(p_curr, p_prev_month)
    td_year_chg = get_colored_chg_html(p_curr, p_prev_year)
    
    category_td = f'<td class="category-cell-style" rowspan="{len(feed_df)}">사료용</td>' if idx == 0 else ""
    import_rows_html += "<tr>" + category_td + "<td class='table-text-left'>" + item_name + "</td><td>" + weight_display + "</td><td>" + price_display + "</td><td>" + td_month_chg + "</td><td>" + td_year_chg + "</td></tr>"

import_table_html = """
<table class="dashboard-table">
    <thead>
        <tr>
            <th style="width:10%;">구분</th>
            <th style="width:18%;">품목명</th>
            <th style="width:18%;">수입량(톤)</th>
            <th style="width:22%;">수입단가(달러/톤)</th>
            <th style="width:16%;">전월 대비 증감률</th>
            <th style="width:16%;">전년 대비 증감률</th>
        </tr>
    </thead>
    <tbody>
""" + import_rows_html + """
    </tbody>
</table>
"""

st.markdown(import_table_html, unsafe_allow_html=True)
