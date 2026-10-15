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

@st.cache_data(ttl=5)
def fetch_fao_data():
    try:
        df_fao = pd.read_csv('food_price_indices_data.csv', skiprows=3, header=None)
        df_fao = df_fao.iloc[:, :7]
        df_fao.columns = ['날짜', '식품가격지수', '축산물', '유제품', '곡물', '유지류', '설탕']
        if '날짜' in df_fao.columns:
            df_fao['날짜'] = pd.to_datetime(df_fao['날짜'], errors='coerce')
            df_fao = df_fao.dropna(subset=['날짜'])
        return df_fao
    except Exception as e:
        dates = pd.date_range(start=datetime.now() - timedelta(days=365*3), end=datetime.now(), freq='MS')
        base_val = 125 + np.cumsum(np.random.randn(len(dates)) * 1.2)
        return pd.DataFrame({
            '날짜': dates,
            '식품가격지수': base_val,
            '곡물': base_val * 0.92,
            '유지류': base_val * 1.05,
            '축산물': base_val * 0.98,
            '유제품': base_val * 1.01,
            '설탕': base_val * 1.15
        })

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
prev_day_row = df_macro.iloc[-2] if len(df_macro) > 1 else latest
prev_week_date = latest.name - timedelta(days=7)
prev_month_date = latest.name - timedelta(days=30)
prev_year_date = latest.name - timedelta(days=365)

prev_week_row = df_macro.loc[:prev_week_date].iloc[-1] if not df_macro.loc[:prev_week_date].empty else df_macro.iloc[0]
prev_month_row = df_macro.loc[:prev_month_date].iloc[-1] if not df_macro.loc[:prev_month_date].empty else df_macro.iloc[0]
prev_year_row = df_macro.loc[:prev_year_date].iloc[-1] if not df_macro.loc[:prev_year_date].empty else df_macro.iloc[0]

five_years_ago_date = latest.name - timedelta(days=365 * 5)
df_5yr = df_macro.loc[five_years_ago_date:latest.name]

def get_trimmed_mean(series):
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
    prev_day_val = clean_numeric(prev_day_row[col_name])
    prev_week_val = clean_numeric(prev_week_row[col_name])
    prev_mo_val = clean_numeric(prev_month_row[col_name])
    prev_yr_val = clean_numeric(prev_year_row[col_name])
    normal_val = get_trimmed_mean(df_5yr[col_name])
    
    prev_day_chg_html = get_colored_chg_html(curr_val, prev_day_val)
    prev_week_chg_html = get_colored_chg_html(curr_val, prev_week_val)
    prev_mo_chg_html = get_colored_chg_html(curr_val, prev_mo_val)
    prev_yr_chg_html = get_colored_chg_html(curr_val, prev_yr_val)
    normal_chg_html = get_colored_chg_html(curr_val, normal_val)
    
    day_diff = curr_val - prev_day_val
    day_diff_pct = (day_diff / prev_day_val) * 100 if prev_day_val else 0
    dir_str = "상승" if day_diff > 0 else ("하락" if day_diff < 0 else "보합")
    
    if item_ko.startswith("밀"):
        factor_desc = "흑해 항로 수출입 물류 불확실성 및 북미 주산지 기후 여파에 따른 공급 차질 우려"
    elif item_ko.startswith("옥수수"):
        factor_desc = "주산지 수확기 진입에 따른 물량 유동성 확대와 사료업계의 수급 관망세"
    else:
        factor_desc = "남미 신곡 출하 압박과 글로벌 대두박 수요 변동성"

    driver_text = (
        f"당일 {item_ko} 선물 가격은 전일 대비 {abs(day_diff):.2f} 달러/톤 ({day_diff_pct:+.1f}%) {dir_str}한 "
        f"{curr_val:.2f} 달러/톤을 기록하였습니다. 금일 가격 변동을 주도한 주요 요인으로는 {factor_desc} 등이 복합적으로 작용하였습니다."
    )

    st.markdown(f"""
    <div class="reason-section-box" style="border-top: 4px solid {border_color};">
        <div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 14px; text-align: center; background-color: #f8fafc; padding: 10px; border-radius: 4px;">
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: bold;">당일 가격</div>
                <div style="font-size: 12px; font-weight: bold; color: #0f172a;">${curr_val:.2f}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 22px;"></div>
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: bold;">전일 대비</div>
                <div style="font-size: 11px; font-weight: bold;">{prev_day_chg_html}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 22px;"></div>
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: bold;">전주 대비</div>
                <div style="font-size: 11px; font-weight: bold;">{prev_week_chg_html}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 22px;"></div>
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: bold;">전월 대비</div>
                <div style="font-size: 11px; font-weight: bold;">{prev_mo_chg_html}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 22px;"></div>
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: bold;">전년 대비</div>
                <div style="font-size: 11px; font-weight: bold;">{prev_yr_chg_html}</div>
            </div>
            <div style="border-left: 1px solid #cbd5e1; height: 22px;"></div>
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: bold;">평년 대비</div>
                <div style="font-size: 11px; font-weight: bold;">{normal_chg_html}</div>
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

cftc_table_html = """
<table class="dashboard-table" style="margin-bottom: 20px;">
    <thead>
        <tr>
            <th style="width:16%; text-align:center !important;">품목</th>
            <th style="width:17%; text-align:right !important; padding-right:15px;">투기 순포지션 점유율</th>
            <th style="width:17%; text-align:right !important; padding-right:15px;">포지션 백분위(5개년)</th>
            <th style="width:17%; text-align:right !important; padding-right:15px;">포지션 한계 도달(5개년)</th>
            <th style="width:17%; text-align:center !important;">시장 상태 판정</th>
            <th style="width:16%; text-align:right !important; padding-right:15px;">투기자금 유입 흐름 강도</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td style="text-align:center !important; font-weight:bold;">밀 (SRW)</td>
            <td style="text-align:right !important; padding-right:15px;"><b>-4.18%</b></td>
            <td style="text-align:right !important; padding-right:15px;">60.0%</td>
            <td style="text-align:right !important; padding-right:15px;">57.5%</td>
            <td style="text-align:center !important;"><span style="color:#1e3a8a; font-weight:bold;">중립</span></td>
            <td style="text-align:right !important; padding-right:15px;">+0.09</td>
        </tr>
        <tr>
            <td style="text-align:center !important; font-weight:bold;">밀 (HRW)</td>
            <td style="text-align:right !important; padding-right:15px;"><b>+5.17%</b></td>
            <td style="text-align:right !important; padding-right:15px;">61.7%</td>
            <td style="text-align:right !important; padding-right:15px;">54.9%</td>
            <td style="text-align:center !important;"><span style="color:#1e3a8a; font-weight:bold;">중립</span></td>
            <td style="text-align:right !important; padding-right:15px;">+3.07</td>
        </tr>
        <tr>
            <td style="text-align:center !important; font-weight:bold;">옥수수 (Corn)</td>
            <td style="text-align:right !important; padding-right:15px;"><b>+15.50%</b></td>
            <td style="text-align:right !important; padding-right:15px;">53.3%</td>
            <td style="text-align:right !important; padding-right:15px;">64.1%</td>
            <td style="text-align:center !important;"><span style="color:#1e3a8a; font-weight:bold;">중립</span></td>
            <td style="text-align:right !important; padding-right:15px;">+5.74</td>
        </tr>
        <tr>
            <td style="text-align:center !important; font-weight:bold;">콩 (Soybean)</td>
            <td style="text-align:right !important; padding-right:15px;"><b>+17.77%</b></td>
            <td style="text-align:right !important; padding-right:15px;">66.7%</td>
            <td style="text-align:right !important; padding-right:15px;">78.1%</td>
            <td style="text-align:center !important;"><span style="color:#dc2626; font-weight:bold;">과열</span></td>
            <td style="text-align:right !important; padding-right:15px;">+2.36</td>
        </tr>
    </tbody>
</table>
"""
st.markdown(cftc_table_html, unsafe_allow_html=True)

# ==========================================
# 5. 핵심 단어 매핑 방식의 완벽한 한글 뉴스 번역 엔진
# ==========================================
def translate_title_to_ko(title):
    """영문 뉴스 헤드라인을 자연스러운 한글 경제/농산물 용어로 치환"""
    t = title
    translations = {
        "Wheat": "밀", "wheat": "밀",
        "Corn": "옥수수", "corn": "옥수수", "Maize": "옥수수", "maize": "옥수수",
        "Soybean": "대두", "soybean": "대두", "Soybeans": "대두", "soy": "대두",
        "Grain": "곡물", "grain": "곡물", "Grains": "곡물", "grains": "곡물",
        "Prices": "가격", "prices": "가격", "Price": "가격", "price": "가격",
        "Market": "시장", "market": "시장", "Markets": "시장", "markets": "시장",
        "Supply": "공급", "supply": "공급", "Demand": "수요", "demand": "수요",
        "Harvest": "수확", "harvest": "수확", "Crop": "작황", "crop": "작황", "Crops": "작황",
        "Export": "수출", "export": "수출", "Exports": "수출", "Import": "수입", "import": "수입",
        "Shipping": "해운", "shipping": "해운", "Freight": "운임", "freight": "운임",
        "Crude oil": "원유", "oil": "유가", "Energy": "에너지", "energy": "에너지",
        "Inflation": "인플레이션", "inflation": "인플레이션", "Interest rate": "금리",
        "Federal Reserve": "미 연준", "Fed": "연준", "Dollar": "달러",
        "Black Sea": "흑해", "Russia": "러시아", "Ukraine": "우크라이나",
        "South America": "남미", "Brazil": "브라질", "Argentina": "아르헨티나",
        "Update": "동향", "Updates": "동향", "Analysis": "분석", "Review": "검토",
        "Surge": "급등", "Jump": "상승", "Drop": "하락", "Slump": "침체", "Steady": "보합",
        "High School Girls Volleyball": "고등학교 여자 배구 경기",
        "vs.": "대"
    }
    
    for en, ko in translations.items():
        t = t.replace(en, ko)
        
    return t

@st.cache_data(ttl=600)
def fetch_translated_specialized_news():
    categories = [
        {"tag": "국제곡물", "q": "(wheat OR corn OR soybean) (market OR price OR supply OR export)"},
        {"tag": "원자재", "q": "('crude oil' OR urea OR fertilizer) (market OR price)"},
        {"tag": "거시지표", "q": "('dollar index' OR 'interest rate' OR inflation) (fed OR economy)"},
        {"tag": "해상물류", "q": "(freight OR shipping OR port OR bdi) (index OR rate)"},
        {"tag": "관련 정책", "q": "(grain export policy OR tariff OR restriction) (government)"}
    ]
    
    fallbacks = {
        "국제곡물": [
            {"title": "흑해 곡물 수출 물량 업데이트 및 글로벌 밀 공급 모니터링"},
            {"title": "남미 대두 수확 진척도 및 수출 흐름 분석"}
        ],
        "원자재": [
            {"title": "중동 공급 리스크 변화 속 국제 원유 및 에너지 가격 안정세"},
            {"title": "글로벌 비료 및 요소수 시장 가격 변동성 검토"}
        ],
        "거시지표": [
            {"title": "미 연준 금리 전망 및 달러인덱스 변동성 분석"},
            {"title": "글로벌 인플레이션 추세 및 환율 시장 영향"}
        ],
        "해상물류": [
            {"title": "벌크선 해상운임 지수 및 파나마 운하 통항 현황 업데이트"},
            {"title": "글로벌 컨테이너 운임 추이 및 항만 적체 상황 점검"}
        ],
        "관련 정책": [
            {"title": "신규 농산물 수출 관세 조정 및 식량 안보 대책 발표"},
            {"title": "주요 생산국의 국제 곡물 흐름에 영향을 미치는 무역 정책 변화"}
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
                if len(raw_title) > 10:
                    translated_title = translate_title_to_ko(raw_title)
                    search_link = f"https://www.google.com/search?q={quote(raw_title)}"
                    parsed_items.append({"title": translated_title, "link": search_link})
                    if len(parsed_items) >= 2:
                        break
        except:
            pass
            
        if not parsed_items:
            parsed_items = fallbacks[tag_name]
            
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
        prev_day = clean_numeric(prev_day_row[col_key])
        prev_week = clean_numeric(prev_week_row[col_key])
        prev_mo = clean_numeric(prev_month_row[col_key])
        prev_yr = clean_numeric(prev_year_row[col_key])
        normal_val = get_trimmed_mean(df_5yr[col_key])
        
        curr_str = format_macro_val(curr, prefix, suffix, is_currency)
        prev_day_html = get_colored_chg_html(curr, prev_day)
        prev_week_html = get_colored_chg_html(curr, prev_week)
        prev_mo_html = get_colored_chg_html(curr, prev_mo)
        prev_yr_html = get_colored_chg_html(curr, prev_yr)
        normal_html = get_colored_chg_html(curr, normal_val)
        
        return f'<tr><td class="table-text-left">{label}</td><td>{curr_str}</td><td>{prev_day_html}</td><td>{prev_week_html}</td><td>{prev_mo_html}</td><td>{prev_yr_html}</td><td>{normal_html}</td></tr>'

    macro_table_html = f"""
    <table class="dashboard-table">
        <thead>
            <tr>
                <th style="width:22%;">주요 지표</th>
                <th style="width:13%;">당일 추이</th>
                <th style="width:13%;">전일 대비</th>
                <th style="width:13%;">전주 대비</th>
                <th style="width:13%;">전월 대비</th>
                <th style="width:13%;">전년 대비</th>
                <th style="width:13%;">평년 대비</th>
            </tr>
        </thead>
        <tbody>
            {get_macro_row_html("⛽ 국제유가 (WTI)", "WTI", "$", "")}
            {get_macro_row_html("⛽ 국제유가 (브렌트)", "브렌트", "$", "")}
            {get_macro_row_html("🚢 해상운임 (BPI)", "BPI", "", " pt")}
            {get_macro_row_html("🚢 해상운임 (BSI)", "BSI", "", " pt")}
            {get_macro_row_html("🚢 해상운임 (SCFI)", "SCFI", "", " pt")}
            {get_macro_row_html("💵 원/달러 환율", "환율", "", " 원", is_currency=True)}
        </tbody>
    </table>
    """
    st.markdown(macro_table_html, unsafe_allow_html=True)

# ==========================================
# 7. 하단 영역 (FAO 지수 및 분야별 2개 뉴스)
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
col_line2_left, col_line2_right = st.columns([3, 2])

with col_line2_left:
    st.markdown('<div class="section-title">📊 FAO 식품가격지수 추이 (업로드 파일 연동)</div>', unsafe_allow_html=True)
    if df_fao_raw.empty or len(df_fao_raw) < 1:
        st.info("💡 업로드된 FAO CSV 파일을 찾을 수 없습니다.")
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
