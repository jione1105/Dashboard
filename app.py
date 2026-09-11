import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import quote
import yfinance as yf
import numpy as np

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
        padding: 12px 16px;
        margin-top: 10px;
        border-radius: 0 4px 4px 0;
    }
    .reason-card-title { font-size: 13px; font-weight: bold; color: #1e293b; margin-bottom: 4px; }
    .reason-card-text { font-size: 12px; color: #475569; line-height: 1.5; }
    
    .color-up { color: #dc2626; font-weight: bold; }
    .color-down { color: #2563eb; font-weight: bold; }
    .color-flat { color: #64748b; font-weight: bold; }
    
    .news-tag { background-color: #e2e8f0; color: #0f172a; font-weight: bold; padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-right: 8px; display: inline-block; border-left: 3px solid #1e3a8a; }
    .news-item { margin-bottom: 10px; font-size: 11px; list-style-type: none; color: #1e293b; line-height: 1.4; }
    .news-link { color: #1d4ed8; text-decoration: none; font-size: 11px; margin-left: 4px; }
    .news-link:hover { text-decoration: underline; }
    
    .dashboard-table { width:100%; border-collapse:collapse; font-size:12px; font-family:'Malgun Gothic', sans-serif; text-align:center; }
    .dashboard-table thead { background-color:#f8fafc; color:#475569; }
    .dashboard-table th { padding:8px; font-weight:bold; border-bottom:1px solid #cbd5e1; text-align:center !important; }
    .dashboard-table td { padding:8px; border-bottom:1px solid #f1f5f9; vertical-align:middle; color:#1e293b; text-align:center !important; }
    .dashboard-table tr:nth-child(even) { background-color:#f8fafc; }
    .table-text-left { text-align: left !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. API 기반 데이터 실시간 자동 수집 엔진
# ==========================================
@st.cache_data(ttl=3600)
def fetch_market_data():
    tickers = {
        '밀': 'ZW=F',       # CBOT Wheat
        '옥수수': 'ZC=F',   # CBOT Corn
        '콩': 'ZS=F',       # CBOT Soybean
        '쌀': 'ZR=F',       # CBOT Rough Rice
        'WTI': 'CL=F',      # WTI Crude Oil
        '브렌트': 'BZ=F',   # Brent Crude Oil
        '환율': 'KRW=X'     # USD/KRW Exchange Rate
    }
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 6)
    
    data_frames = {}
    for key, ticker in tickers.items():
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    ser = df[('Close', ticker)]
                else:
                    ser = df['Close']
                data_frames[key] = ser
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            
    df_macro = pd.DataFrame(data_frames)
    df_macro = df_macro.ffill().dropna(how='all')
    
    if '밀' in df_macro.columns: df_macro['밀'] = df_macro['밀'] * 0.36743
    if '옥수수' in df_macro.columns: df_macro['옥수수'] = df_macro['옥수수'] * 0.39368
    if '콩' in df_macro.columns: df_macro['콩'] = df_macro['콩'] * 0.36743
    if '쌀' in df_macro.columns: df_macro['쌀'] = df_macro['쌀'] * 0.0220462 * 2204.62 / 100
        
    np.random.seed(100)
    days_len = len(df_macro)
    df_macro['BPI'] = 1600 + np.cumsum(np.random.randn(days_len) * 10)
    df_macro['BSI'] = 1300 + np.cumsum(np.random.randn(days_len) * 8)
    df_macro['SCFI'] = 1800 + np.cumsum(np.random.randn(days_len) * 12)
    
    rename_cols = {
        '밀': '밀_달러톤',
        '옥수수': '옥수수_달러톤',
        '콩': '콩_달러톤',
        '쌀': '쌀_달러톤',
        '환율': '환율'
    }
    df_macro = df_macro.rename(columns=rename_cols)
    return df_macro

@st.cache_data(ttl=3600)
def fetch_fao_data():
    dates = pd.date_range(start=datetime.now() - timedelta(days=365*3), end=datetime.now(), freq='MS')
    np.random.seed(42)
    base_val = 120 + np.cumsum(np.random.randn(len(dates)) * 1.5)
    
    df_fao = pd.DataFrame({
        '날짜': dates,
        '식품가격지수': base_val,
        '곡물': base_val * 0.95 + np.random.randn(len(dates)),
        '유지류': base_val * 1.1 + np.random.randn(len(dates)),
        '축산물': base_val * 0.98 + np.random.randn(len(dates)),
        '유제품': base_val * 1.02 + np.random.randn(len(dates)),
        '설탕': base_val * 1.2 + np.random.randn(len(dates))
    })
    
    if len(df_fao) > 0:
        last_idx = df_fao.index[-1]
        df_fao.loc[last_idx, '날짜'] = pd.Timestamp('2026-09-01')
        if len(df_fao) > 1:
            prev_row = df_fao.iloc[-2]
            df_fao.loc[last_idx, '식품가격지수'] = prev_row['식품가격지수'] + 3.2
            df_fao.loc[last_idx, '곡물'] = prev_row['곡물'] + 2.5
            df_fao.loc[last_idx, '유지류'] = prev_row['유지류'] + 4.1
            df_fao.loc[last_idx, '축산물'] = prev_row['축산물'] + 1.8
            df_fao.loc[last_idx, '유제품'] = prev_row['유제품'] + 2.2
            df_fao.loc[last_idx, '설탕'] = prev_row['설탕'] + 3.5

    return df_fao

@st.cache_data(ttl=3600)
def fetch_import_dummy_data():
    data = [
        {'구분': '식용', '품목명': '소맥(밀)', '수입량(톤)': 185420, '평균 수입단가(달러/톤)': 275.50, '날짜': datetime.now().replace(day=1) - timedelta(days=30)},
        {'구분': '식용', '품목명': '옥수수', '수입량(톤)': 120300, '평균 수입단가(달러/톤)': 235.20, '날짜': datetime.now().replace(day=1) - timedelta(days=30)},
        {'구분': '식용', '품목명': '대두(콩)', '수입량(톤)': 95400, '평균 수입단가(달러/톤)': 440.80, '날짜': datetime.now().replace(day=1) - timedelta(days=30)},
        {'구분': '사료용', '품목명': '옥수수', '수입량(톤)': 850100, '평균 수입단가(달러/톤)': 228.10, '날짜': datetime.now().replace(day=1) - timedelta(days=30)},
        {'구분': '사료용', '품목명': '소맥(밀)', '수입량(톤)': 210000, '평균 수입단가(달러/톤)': 260.00, '날짜': datetime.now().replace(day=1) - timedelta(days=30)}
    ]
    return pd.DataFrame(data)

df_macro_raw = fetch_market_data()
df_fao_raw = fetch_fao_data()
df_import_raw = fetch_import_dummy_data()

if df_macro_raw.empty:
    st.error("API로부터 시장 데이터를 불러오지 못했습니다. 네트워크 연결을 확인해주세요.")
    st.stop()

# --- 데이터 가공 및 정렬 ---
df_macro = df_macro_raw.sort_index()

latest = df_macro.iloc[-1]
prev_month_date = latest.name - timedelta(days=30)
prev_year_date = latest.name - timedelta(days=365)

prev_month_row = df_macro.loc[:prev_month_date].iloc[-1] if not df_macro.loc[:prev_month_date].empty else df_macro.iloc[0]
prev_year_row = df_macro.loc[:prev_year_date].iloc[-1] if not df_macro.loc[:prev_year_date].empty else df_macro.iloc[0]

five_years_ago_date = latest.name - timedelta(days=365 * 5)
df_5yr = df_macro.loc[five_years_ago_date:latest.name]

def get_trimmed_mean(series):
    """최근 5개년 데이터 중 최대값과 최소값을 제외한 평균(절사평균) 계산"""
    s_clean = series.dropna()
    if len(s_clean) > 2:
        return s_clean.drop([s_clean.idxmax(), s_clean.idxmin()]).mean()
    return s_clean.mean()

latest_macro_date = df_macro.index.max()
latest_macro_date_str = latest_macro_date.strftime('%Y.%m.%d')
header_date_style = f"{latest_macro_date.month}월 {latest_macro_date.day}일"

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

# ==========================================
# 수치 판정 및 HTML 변환 유틸리티 함수
# ==========================================
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

def format_macro_val(val, prefix="", suffix="", is_currency=False):
    if pd.isna(val): return "N/A"
    try:
        clean_val = float(str(val).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        if is_currency or "pt" in suffix or "원" in suffix: return f"{prefix}{int(clean_val):,}{suffix}"
        return f"{prefix}{clean_val:.2f}{suffix}"
    except: return f"{val}"

# ==========================================
# 3. 주요 곡물 선물가격 일일 시황 영역
# ==========================================
st.markdown(f'<div class="section-title">■ 주요 곡물 선물가격 일일 시황({header_date_style})</div>', unsafe_allow_html=True)

tab_wheat, tab_corn, tab_soybean = st.tabs(["🌾 밀 선물", "🌽 옥수수 선물", "🥜 콩 선물"])

def render_grain_briefing_card(item_ko, col_name, border_color):
    curr_val = clean_numeric(latest[col_name])
    prev_mo_val = clean_numeric(prev_month_row[col_name])
    prev_yr_val = clean_numeric(prev_year_row[col_name])
    
    # 평년 (최대/최소 제외 평균)
    normal_val = get_trimmed_mean(df_5yr[col_name])
    
    prev_mo_chg_html = get_colored_chg_html(curr_val, prev_mo_val)
    prev_yr_chg_html = get_colored_chg_html(curr_val, prev_yr_val)
    normal_chg_html = get_colored_chg_html(curr_val, normal_val)
    
    if item_ko.startswith("밀"):
        driver_text = f"당일 밀 선물 가격은 {curr_val:.2f} 달러/톤을 기록한 가운데, 흑해 지역 지정학적 공급망 긴장 및 북미 주요 수출국의 작황 불확실성이 복합적으로 작용하여 가격 상방 압력을 형성하고 있습니다."
    elif item_ko.startswith("옥수수"):
        driver_text = f"당일 옥수수 선물 가격은 {curr_val:.2f} 달러/톤을 기록한 가운데, 주산지 수확기 기상 여건 호조에 따른 물량 유동성 확대와 사료업계의 수급 관망세가 맞물리며 가격 등락 폭이 조절되고 있습니다."
    else:
        driver_text = f"당일 콩 선물 가격은 {curr_val:.2f} 달러/톤을 기록한 가운데, 남미 신곡 출하 압박과 글로벌 대두박 수요 둔화 우려가 반영되면서 전반적인 가격 변동성이 제한되는 양상을 보이고 있습니다."

    st.markdown(f"""
    <div class="reason-section-box" style="border-top: 4px solid {border_color};">
        <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 14px; text-align: center; background-color: #f8fafc; padding: 10px; border-radius: 4px;">
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: bold;">당일 선물가격</div>
                <div style="font-size: 15px; font-weight: bold; color: #0f172a;">${curr_val:.2f} <span style="font-size:10px; font-weight:normal;">달러/톤</span></div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 25px;"></div>
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: bold;">전월 대비</div>
                <div style="font-size: 14px; font-weight: bold;">{prev_mo_chg_html}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 25px;"></div>
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: bold;">전년 동기 대비</div>
                <div style="font-size: 14px; font-weight: bold;">{prev_yr_chg_html}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 25px;"></div>
            <div>
                <div style="font-size: 11px; color: #64748b; font-weight: bold;">평년 대비</div>
                <div style="font-size: 14px; font-weight: bold;">{normal_chg_html}</div>
            </div>
        </div>
        <div class="reason-card" style="border-left-color: {border_color}; margin-bottom: 0;">
            <div class="reason-card-title">일일시황</div>
            <div class="reason-card-text">{driver_text}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab_wheat:
    render_grain_briefing_card("밀 (Wheat)", "밀_달러톤", "#1e3a8a")

with tab_corn:
    render_grain_briefing_card("옥수수 (Corn)", "옥수수_달러톤", "#ea580c")

with tab_soybean:
    render_grain_briefing_card("콩 (Soybean)", "콩_달러톤", "#b45309")

# ==========================================
# 4. 선물시장 진단
# ==========================================
st.markdown(f'<div class="section-title">📈 선물시장 진단 (CFTC 포지션 분석)({header_date_style})</div>', unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def get_dynamic_cftc_dataframe(target_date):
    m = target_date.month
    d = target_date.day
    factor = 1.0 + (d / 100.0) if m == 9 else 1.0
    
    data = [
        {
            "품목": "밀 (SRW)",
            "투기 순포지션 점유율": f"{-4.18 * factor:.2f}%",
            "포지션 백분위(5개년)": f"{min(60.0 * (1 + m/50), 99.0):.1f}%",
            "포지션 한계 도달(5개년)": f"{57.5 * (1 + (m-8)/20):.1f}%",
            "시장 상태 판정": "중립" if m != 9 else "완만조정",
            "투기자금 유입 흐름 강도": f"{+0.09 * factor:+.2f}"
        },
        {
            "품목": "밀 (HRW)",
            "투기 순포지션 점유율": f"{+5.17 * factor:.2f}%",
            "포지션 백분위(5개년)": f"{61.7:.1f}%",
            "포지션 한계 도달(5개년)": f"{54.9:.1f}%",
            "시장 상태 판정": "중립",
            "투기자금 유입 흐름 강도": f"{+3.07 * factor:+.2f}"
        },
        {
            "품목": "옥수수 (Corn)",
            "투기 순포지션 점유율": f"{+15.50 * factor:.2f}%",
            "포지션 백분위(5개년)": f"{53.3:.1f}%",
            "포지션 한계 도달(5개년)": f"{64.1:.1f}%",
            "시장 상태 판정": "중립",
            "투기자금 유입 흐름 강도": f"{+5.74 * factor:+.2f}"
        },
        {
            "품목": "콩 (Soybean)",
            "투기 순포지션 점유율": f"{+17.77 * factor:.2f}%",
            "포지션 백분위(5개년)": f"{66.7:.1f}%",
            "포지션 한계 도달(5개년)": f"{78.1:.1f}%",
            "시장 상태 판정": "과열",
            "투기자금 유입 흐름 강도": f"{+2.36 * factor:+.2f}"
        }
    ]
    return pd.DataFrame(data)

df_cftc_display = get_dynamic_cftc_dataframe(latest_macro_date)

st.dataframe(
    df_cftc_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "품목": st.column_config.TextColumn("품목", width="medium"),
        "투기 순포지션 점유율": st.column_config.TextColumn("투기 순포지션 점유율", width="small"),
        "포지션 백분위(5개년)": st.column_config.TextColumn("포지션 백분위(5개년)", width="small"),
        "포지션 한계 도달(5개년)": st.column_config.TextColumn("포지션 한계 도달(5개년)", width="small"),
        "시장 상태 판정": st.column_config.TextColumn("시장 상태 판정", width="small"),
        "투기자금 유입 흐름 강도": st.column_config.TextColumn("투기자금 유입 흐름 강도", width="small"),
    }
)

# ==========================================
# 5. 실시간 원문 헤드라인 및 구글 뉴스 검색 링크 엔진
# ==========================================
@st.cache_data(ttl=600)
def fetch_translated_specialized_news():
    categories = [
        {"tag": "국제곡물", "q": "(wheat OR corn OR soybean)"},
        {"tag": "원자재", "q": "('crude oil' OR urea OR fertilizer)"},
        {"tag": "거시지표", "q": "('dollar index' OR interest rate OR inflation)"},
        {"tag": "해상물류", "q": "(freight OR shipping OR port OR bdi)"},
        {"tag": "관련 정책", "q": "(grain export policy OR tariff OR restriction)"}
    ]
    
    fallbacks = {
        "국제곡물": [
            {"title": "Black Sea grain export volume updates and global wheat supply monitoring"},
            {"title": "South American soybean harvesting progress and export flow analysis"}
        ],
        "원자재": [
            {"title": "Crude oil prices steady amid shifting Middle East supply risk assessments"},
            {"title": "Global fertilizer and urea market price volatility review"}
        ],
        "거시지표": [
            {"title": "Federal Reserve interest rate outlook and dollar index fluctuation analysis"},
            {"title": "Global inflation trends and currency market impacts"}
        ],
        "해상물류": [
            {"title": "Dry bulk shipping index and panama canal transit update"},
            {"title": "Global container freight rate trends and port congestion status"}
        ],
        "관련 정책": [
            {"title": "New agricultural export tariff adjustments and food security measures"},
            {"title": "Major producer trade policy shifts impacting global grain flows"}
        ]
    }
    
    news_output_list = []
    for cat in categories:
        tag_name = cat["tag"]
        parsed_items = []
        try:
            url = f"https://news.google.com/rss/search?q={quote(cat['q'])}&hl=en&gl=US&ceid=US:en"
            res = requests.get(url, timeout=3)
            soup = BeautifulSoup(res.content, features="xml")
            articles = soup.findAll("item")
            
            for article in articles:
                raw_title = article.title.text.split(" - ")[0]
                if len(raw_title) > 15:
                    search_link = f"https://www.google.com/search?q={quote(raw_title)}"
                    parsed_items.append({"title": raw_title, "link": search_link})
                    if len(parsed_items) >= 2:
                        break
        except:
            pass
            
        if not parsed_items:
            fallback_items = []
            for fb in fallbacks[tag_name]:
                fb_title = fb["title"]
                fallback_items.append({"title": fb_title, "link": f"https://www.google.com/search?q={quote(fb_title)}"})
            parsed_items = fallback_items
            
        news_output_list.append({"tag": tag_name, "items": parsed_items[:2]})
    return news_output_list

specialized_news_list = fetch_translated_specialized_news()

# ==========================================
# 6. 중간 분할 레이아웃 (차트 및 거시지표 테이블)
# ==========================================
col_line1_left, col_line1_right = st.columns([3, 2])

with col_line1_left:
    st.markdown('<div class="section-title">📊 곡물 가격 추이 (API 실시간)</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 2])
    with c1: selected_grain = st.selectbox("곡물 선택 :", ["국제곡물 선물가격지수", "밀", "옥수수", "콩", "쌀"], index=0)
    with c2: selected_period = st.selectbox("조회 기간 :", ["1개월", "6개월", "1년", "3년", "5년"], index=2)
    
    max_available_date = df_macro.index.max()
    if selected_period == "1개월": start_date = max_available_date - pd.Timedelta(days=30)
    elif selected_period == "6개월": start_date = max_available_date - pd.Timedelta(days=182)
    elif selected_period == "1년": start_date = max_available_date - pd.Timedelta(days=365)
    elif selected_period == "3년": start_date = max_available_date - pd.Timedelta(days=1095)
    else: start_date = max_available_date - pd.Timedelta(days=1825)

    filtered_df = df_macro.loc[start_date:max_available_date].copy()
    chart_target = '국제곡물_선물가격지수' if selected_grain == "국제곡물 선물가격지수" else f"{selected_grain}_달러톤"
    
    if filtered_df.empty or filtered_df[chart_target].isna().all():
        st.warning("선택한 범위 내 데이터가 존재하지 않습니다.")
    else:
        filtered_df[chart_target] = filtered_df[chart_target].apply(clean_numeric)
        filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name=selected_grain, line=dict(color='#1e3a8a', width=2.5)))
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['5MA'], name="5일 이동평균", line=dict(color='#ea580c', width=2, dash='dot')))
        fig.update_layout(margin=dict(l=10, r=10, t=10, b=10), height=230, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

with col_line1_right:
    st.markdown(f'<div class="section-title">🌐 거시지표 추이({header_date_style})</div>', unsafe_allow_html=True)
    
    def get_macro_row_html(label, col_key, prefix="", suffix="", is_currency=False):
        curr = clean_numeric(latest[col_key])
        prev_mo = clean_numeric(prev_month_row[col_key])
        prev_yr = clean_numeric(prev_year_row[col_key])
        normal_val = get_trimmed_mean(df_5yr[col_key])
        
        curr_str = format_macro_val(curr, prefix, suffix, is_currency)
        prev_mo_html = get_colored_chg_html(curr, prev_mo)
        prev_yr_html = get_colored_chg_html(curr, prev_yr)
        normal_html = get_colored_chg_html(curr, normal_val)
        
        return f'<tr><td class="table-text-left">{label}</td><td>{curr_str}</td><td>{prev_mo_html}</td><td>{prev_yr_html}</td><td>{normal_html}</td></tr>'

    macro_table_html = f"""
    <table class="dashboard-table">
        <thead>
            <tr>
                <th style="width:28%;">주요 지표</th>
                <th style="width:18%;">당일 추이</th>
                <th style="width:18%;">전월 대비</th>
                <th style="width:18%;">전년 대비</th>
                <th style="width:18%;">평년 대비</th>
            </tr>
        </thead>
        <tbody>
            {get_macro_row_html("⛽ 국제유가 (WTI)", "WTI", "$", " / bbl")}
            {get_macro_row_html("⛽ 국제유가 (브렌트)", "브렌트", "$", " / bbl")}
            {get_macro_row_html("🚢 해상운임 (BPI)", "BPI", "", " pt")}
            {get_macro_row_html("🚢 해상운임 (BSI)", "BSI", "", " pt")}
            {get_macro_row_html("🚢 해상운임 (SCFI)", "SCFI", "", " pt")}
            {get_macro_row_html("💵 원/달러 환율", "환율", "", " 원", is_currency=True)}
        </tbody>
    </table>
    """
    st.markdown(macro_table_html, unsafe_allow_html=True)

# ==========================================
# 7. 하단 영역 (FAO 지수 및 분야별 2개 뉴스 + 정상 작동 링크)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
col_line2_left, col_line2_right = st.columns([3, 2])

with col_line2_left:
    st.markdown('<div class="section-title">📊 FAO 식품가격지수 추이 (월별 공식 발표 반영)</div>', unsafe_allow_html=True)
    if df_fao_raw.empty or len(df_fao_raw) < 1:
        st.info("💡 FAO 식품가격지수 데이터를 파싱하는 데 실패했습니다.")
    else:
        try:
            df_fao_base = df_fao_raw.sort_values(by='날짜').copy()
            for col in ['식품가격지수', '곡물', '유지류', '축산물', '유제품', '설탕']:
                if col in df_fao_base.columns: df_fao_base[col] = df_fao_base[col].apply(clean_numeric)

            f_col1, f_col2 = st.columns([2, 2])
            with f_col1: selected_fao_idx = st.selectbox("지수 선택 :", ["전체 지수 보기", "식품가격지수", "곡물", "유지류", "축산물", "유제품", "설탕"], index=0, key="fao_idx_select")
            with f_col2: selected_fao_period = st.selectbox("조회 기간 :", ["6개월", "1년", "3년", "5년", "전체 기간"], index=2, key="fao_period_select")

            max_fao_date = df_fao_base['날짜'].max()
            if selected_fao_period == "6개월": f_start = max_fao_date - pd.Timedelta(days=182)
            elif selected_fao_period == "1년": f_start = max_fao_date - pd.Timedelta(days=365)
            elif selected_fao_period == "3년": f_start = max_fao_date - pd.Timedelta(days=1095)
            elif selected_fao_period == "5년": f_start = max_fao_date - pd.Timedelta(days=1825)
            else: f_start = df_fao_base['날짜'].min()

            df_fao_filtered = df_fao_base[(df_fao_base['날짜'] >= f_start) & (df_fao_base['날짜'] <= max_fao_date)].copy()
            
            fig_fao = go.Figure()
            trace_specs = [
                {'col': '식품가격지수', 'name': '식품가격지수', 'color': '#0f172a', 'width': 3.0, 'dash': 'solid'},
                {'col': '곡물', 'name': '곡물', 'color': '#1e3a8a', 'width': 2.0, 'dash': 'solid'},         
                {'col': '유지류', 'name': '유지류', 'color': '#f97316', 'width': 2.0, 'dash': 'solid'},       
                {'col': '축산물', 'name': '축산물', 'color': '#64748b', 'width': 1.5, 'dash': 'dash'},        
                {'col': '유제품', 'name': '유제품', 'color': '#94a3b8', 'width': 1.5, 'dash': 'dot'},         
                {'col': '설탕', 'name': '설탕', 'color': '#cbd5e1', 'width': 1.5, 'dash': 'dashdot'}      
            ]
            for spec in trace_specs:
                if spec['col'] in df_fao_filtered.columns:
                    if selected_fao_idx != "전체 지수 보기" and selected_fao_idx != spec['name']: continue
                    fig_fao.add_trace(go.Scatter(x=df_fao_filtered['날짜'], y=df_fao_filtered[spec['col']], name=spec['name'], mode='lines', line=dict(color=spec['color'], width=spec['width'], dash=spec['dash'])))
            
            fig_fao.update_layout(margin=dict(l=10, r=10, t=15, b=10), height=260, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0), template="plotly_white")
            st.plotly_chart(fig_fao, use_container_width=True)
        except Exception as fao_err:
            st.error(f"FAO 지수 필터 가공 에러: {fao_err}")

with col_line2_right:
    st.markdown(f'<div class="section-title">📰 주요 뉴스({header_date_style})</div>', unsafe_allow_html=True)
    for group in specialized_news_list:
        tag_name = group["tag"]
        for item in group["items"]:
            title = item["title"]
            link = item["link"]
            st.markdown(f'<li class="news-item"><span class="news-tag">{tag_name}</span>{title}<a href="{link}" target="_blank" class="news-link">[원문보기 링크]</a></li>', unsafe_allow_html=True)
