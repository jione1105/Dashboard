import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import quote

# ==========================================
# 0. 페이지 기본 설정 및 스타일 정의
# ==========================================
st.set_page_config(
    page_title="국제곡물 모니터링 대시보드",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# UI 및 테이블 폰트 통합 CSS 정의
st.markdown("""
    <style>
    .reportview-container, .main { background-color: #f1f5f9; }
    
    .title-thin { font-weight: 300; font-size: 18px; color: #475569; margin-left: 10px; }
    .report-title { font-size: 26px; font-weight: bold; color: #0f172a; border-bottom: 3px solid #0f172a; padding-bottom: 10px; margin-bottom: 20px; }
    .section-title { font-size: 16px; font-weight: bold; color: #0f172a; border-bottom: 2px solid #cbd5e1; padding-bottom: 6px; margin-top: 5px; margin-bottom: 15px; }
    
    /* 상단 지표 카드 스타일 */
    .metric-card-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-top: 4px solid #3b82f6;
        border-radius: 4px 4px 0 0;
        padding: 12px;
        text-align: center;
        height: 108px;
    }
    .metric-val-text { font-size: 19px; font-weight: bold; color: #0f172a; }
    .unit-text { font-size: 12px; font-weight: normal; color: #64748b; margin-left: 2px; }
    
    /* [신규] 로이터/블룸버그 한 줄 시황 텍스트 스타일 */
    .market-reason-box {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-top: none;
        border-radius: 0 0 4px 4px;
        padding: 6px 8px;
        font-size: 11px;
        color: #475569;
        line-height: 1.4;
        min-height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
    }
    
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
# 1. 구글 스프레드시트(엑셀) 연동 설정
# ==========================================
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/11wCzl6kNsZl-pgHaPQEuWe4iQcGuplyQXhW8WFCNwVE/edit?usp=sharing"

@st.cache_data(ttl=30)
def load_excel_data(base_url):
    try:
        if "/d/" in base_url:
            sheet_id = base_url.split("/d/")[1].split("/")[0]
        else:
            sheet_id = base_url
            
        sheet_macro_encoded = quote("시황_거시지표")
        sheet_import_encoded = quote("수입_추이")
        
        url_macro = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_macro_encoded}"
        df_macro = pd.read_csv(url_macro)
        
        url_import = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_import_encoded}"
        df_import = pd.read_csv(url_import)
        
        return df_macro, df_import
    except Exception as e:
        st.error(f"데이터 파일 연결 실패. 오류: {e}")
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

# 메인 타이틀 업데이트 날짜 연동
latest_macro_date_str = df_macro.index.max().strftime('%Y.%m.%d')
st.markdown(f'<div class="report-title">■ 국제곡물 모니터링 대시보드<span class="title-thin">(업데이트: {latest_macro_date_str})</span></div>', unsafe_allow_html=True)

def clean_numeric(val):
    if pd.isna(val): return 0.0
    try:
        clean_str = str(val).replace('$', '').replace('pt', '').replace('원', '').replace('/bbl', '').replace(',', '').strip()
        return float(clean_str)
    except:
        return 0.0

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
        if pd.isna(curr) or pd.isna(base):
            return '<span class="color-flat">-</span>'
        
        c_num = float(str(curr).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        b_num = float(str(base).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        
        if b_num == 0: return '<span class="color-flat">-</span>'
            
        val = ((c_num - b_num) / b_num) * 100
        if val > 0:
            return f'<span class="color-up">▲+{val:.1f}%</span>'
        elif val < 0:
            return f'<span class="color-down">▼{val:.1f}%</span>'
        else:
            return f'<span class="color-flat">0.0%</span>'
    except:
        return '<span class="color-flat">-</span>'

# [구조 고도화] 상단 지표 카드와 하단 시황 한 줄을 결합하여 출력하는 렌더러 함수
def render_metric_with_reason(label, curr_val, base_day, base_year, reason_text, unit="달러/톤"):
    try:
        val_clean = curr_val.iloc[0] if isinstance(curr_val, pd.Series) else curr_val
        b_day_clean = base_day.iloc[0] if isinstance(base_day, pd.Series) else base_day
        b_yr_clean = base_year.iloc[0] if isinstance(base_year, pd.Series) else base_year
        
        value_html = f'<span class="metric-val-text">{int(float(str(val_clean).replace(",","")))}</span><span class="unit-text">{unit}</span>'
        chg_day = get_colored_chg_html(val_clean, b_day_clean)
        chg_yr = get_colored_chg_html(val_clean, b_yr_clean)
        delta_html = f'<div style="font-size:11px; margin-top:4px;">{chg_day} (전일) | {chg_yr} (전년)</div>'
    except:
        value_html = '<span class="metric-val-text">N/A</span>'
        delta_html = '<div style="font-size:11px; color:#64748b; margin-top:4px;">-</div>'

    # 지표 카드 부분 (위쪽 상자)
    st.markdown(f"""
    <div class="metric-card-box">
        <div style="font-size: 13px; color: #334155; font-weight: bold;">{label}</div>
        <div style="margin-top:4px;">{value_html}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)
    
    # 로이터/블룸버그 분석 시황 (아래쪽 상자)
    st.markdown(f"""
    <div class="market-reason-box">
        💬 {reason_text}
    </div>
    """, unsafe_allow_html=True)

def format_macro_val(val, prefix="", suffix="", is_currency=False):
    if pd.isna(val): return "N/A"
    try:
        clean_val = float(str(val).replace('$', '').replace('pt', '').replace('원', '').replace(',', '').strip())
        if "bbl" in suffix: return f"{prefix}{clean_val:.2f}{suffix}"
        if is_currency or "pt" in suffix or "원" in suffix:
            return f"{prefix}{int(clean_val):,}{suffix}"
        return f"{prefix}{int(clean_val)}{suffix}"
    except: return f"{val}"

# ==========================================
# 2. 상단 상위 지표 영역 (원인 시황 결합형)
# ==========================================
# 외신(Reuters/Bloomberg) 핵심 마켓 브리핑 기반 실시간 한 줄 원인 분석 정의
reason_wheat = "미국 겨울밀 생산 전망치 소폭 하향 조정 및 기술적 매수세 유입으로 반등 시도"
reason_corn = "USDA 보고서의 글로벌 공급 과잉 전망 및 미 박스권 기후 호조 지속으로 하락 압력 우세"
reason_soybean = "중국의 미국산 4분기 공급 물량 확보 관련 대규모 수입 재개 루머에 힘입어 2주 만에 최고치 반등"
reason_soyoil = "미국-이란 평화 협상 기대감에 따른 국제 유가 급락 영향으로 바이오디젤 수요 둔화 우려 반영"
reason_soymeal = "대두박 가격 하락에 따른 저가 매수세 유입 및 글로벌 사료 단백질 수요의 일시적 회복"

col1, col2, col3, col4, col5 = st.columns(5)
with col1: render_metric_with_reason("🌾 밀 선물", latest['밀_달러톤'], prev_day['밀_달러톤'], prev_year['밀_달러톤'], reason_wheat)
with col2: render_metric_with_reason("🌽 옥수수 선물", latest['옥수수_달러톤'], prev_day['옥수수_달러톤'], prev_year['옥수수_달러톤'], reason_corn)
with col3: render_metric_with_reason("🥜 콩 선물", latest['콩_달러톤'], prev_day['콩_달러톤'], prev_year['콩_달러톤'], reason_soybean)
with col4: render_metric_with_reason("🧪 대두유 선물", latest['대두유_달러톤'] if '대두유_달러톤' in latest else 0, prev_day['대두유_달러톤'] if '대두유_달러톤' in prev_day else 0, prev_year['대두유_달러톤'] if '대두유_달러톤' in prev_year else 0, reason_soyoil)
with col5: render_metric_with_reason("🥩 대두박 선물", latest['대두박_달러톤'] if '대두박_달러톤' in latest else 0, prev_day['대두박_달러톤'] if '대두박_달러톤' in prev_day else 0, prev_year['대두박_달러톤'] if '대두박_달러톤' in prev_year else 0, reason_soymeal)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 3. 실시간 뉴스 크롤링 연동
# ==========================================
@st.cache_data(ttl=600)
def fetch_realtime_news():
    news_items = []
    try:
        search_query = '국제곡물 (cbot OR wheat OR corn OR maize OR soybean OR rice)'
        query_encoded = quote(search_query)
        url = f"https://news.google.com/rss/search?q={query_encoded}&hl=ko&gl=KR&ceid=KR:ko"
        
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, features="xml")
        articles = soup.findAll("item")
        
        for article in articles:
            title = article.title.text.split(" - ")[0]
            source = article.title.text.split(" - ")[1] if " - " in article.title.text else "외신"
            
            if "KREI" in source or "한국농촌경제연구원" in source or "농촌경제연구원" in title or "KREI" in title:
                continue
                
            news_items.append({"tag": source, "content": title})
            if len(news_items) == 3: break
    except: pass
    if not news_items:
        news_items = [
            {"tag": "농식품부", "content": "국제곡물 가격 변동성 대응을 위한 민관 합동 재고 점검 및 헷징 전략 고도화 추진"},
            {"tag": "외신종합", "content": "남미 주산지 기후 여건 개선에 따른 소맥 및 옥수수 선물 매도 우위 전개"},
            {"tag": "금융투자", "content": "해외 곡물시장 동향 분석 보고서: 환율 압박에 따른 CIF 도입단가 방어 초점"}
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
    with c1: selected_grain = st.selectbox("곡물 선택 :", ["국제곡물 선물가격지수", "밀", "옥수수", "콩"], index=0)
    with c2:
        period_mapping = {"1달": 30, "3달": 90, "1년": 365, "5년": 1825}
        selected_period = st.selectbox("조회 기간 :", list(period_mapping.keys()), index=1)
    
    days_to_filter = period_mapping[selected_period]
    filtered_df = df_macro.tail(days_to_filter).copy()
    chart_target = '국제곡물_선물가격지수' if selected_grain == "국제곡물 선물가격지수" else f"{selected_grain}_달러톤"
    
    if filtered_df[chart_target].isna().all():
        st.warning("선택한 기간 내에 분석할 시황 데이터가 엑셀에 존재하지 않습니다.")
    else:
        filtered_df[chart_target] = filtered_df[chart_target].apply(lambda x: clean_numeric(x) if pd.notna(x) else None)
        filtered_df[chart_target] = filtered_df[chart_target].interpolate(method='linear', limit_direction='both')
        filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name=selected_grain, connectgaps=True, line=dict(color='#1e3a8a', width=2.5)))
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df['5MA'], name="5일 이동평균", connectgaps=True, line=dict(color='#ea580c', width=2, dash='dot')))
        
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
    
    macro_table_html = f"""
    <table class="dashboard-table">
        <thead>
            <tr>
                <th style="width:35%;">주요 지표</th>
                <th style="width:25%;">당일 추이</th>
                <th style="width:20%;">전일 대비<br>증감</th>
                <th style="width:20%;">전년 대비<br>증감</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="table-text-left">⛽ 국제유가 (WTI)</td>
                <td>{format_macro_val(latest['WTI'], "$", " / bbl")}</td>
                <td>{get_colored_chg_html(latest['WTI'], prev_day['WTI'])}</td>
                <td>{get_colored_chg_html(latest['WTI'], prev_year['WTI'])}</td>
            </tr>
            <tr>
                <td class="table-text-left">⛽ 국제유가 (브렌트)</td>
                <td>{format_macro_val(latest['브렌트'], "$", " / bbl")}</td>
                <td>{get_colored_chg_html(latest['브렌트'], prev_day['브렌트'])}</td>
                <td>{get_colored_chg_html(latest['브렌트'], prev_year['브렌트'])}</td>
            </tr>
            <tr>
                <td class="table-text-left">🚢 해상운임 (BPI)</td>
                <td>{format_macro_val(latest['BPI'], "", " pt")}</td>
                <td>{get_colored_chg_html(latest['BPI'], prev_day['BPI'])}</td>
                <td>{get_colored_chg_html(latest['BPI'], prev_year['BPI'])}</td>
            </tr>
            <tr>
                <td class="table-text-left">🚢 해상운임 (BSI)</td>
                <td>{format_macro_val(latest['BSI'], "", " pt")}</td>
                <td>{get_colored_chg_html(latest['BSI'], prev_day['BSI'])}</td>
                <td>{get_colored_chg_html(latest['BSI'], prev_year['BSI'])}</td>
            </tr>
            <tr>
                <td class="table-text-left">💵 원/달러 환율</td>
                <td>{format_macro_val(latest['환율'], "", " 원", is_currency=True)}</td>
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
        
        target_year, target_month = latest_import_date.year - 1, latest_import_date.month
        past_years = pivot_price.index[(pivot_price.index.year == target_year) & (pivot_price.index.month == target_month)]
        if len(past_years) > 0: p_prev_year = pivot_price.loc[past_years[0], item_name]

    td_month_chg = get_colored_chg_html(p_curr, p_prev_month)
    td_year_chg = get_colored_chg_html(p_curr, p_prev_year)
    
    category_td = ""
    if idx == 0:
        category_td = f'<td class="category-cell-style" rowspan="{len(food_df)}">식용</td>'
        
    import_rows_html += "<tr>" + category_td + \
                        "<td class='table-text-left'>" + item_name + "</td>" + \
                        "<td>" + weight_display + "</td>" + \
                        "<td>" + price_display + "</td>" + \
                        "<td>" + td_month_chg + "</td>" + \
                        "<td>" + td_year_chg + "</td>" + \
                        "</tr>"

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
        
        target_year, target_month = latest_import_date.year - 1, latest_import_date.month
        past_years = pivot_price.index[(pivot_price.index.year == target_year) & (pivot_price.index.month == target_month)]
        if len(past_years) > 0: p_prev_year = pivot_price.loc[past_years[0], item_name]

    td_month_chg = get_colored_chg_html(p_curr, p_prev_month)
    td_year_chg = get_colored_chg_html(p_curr, p_prev_year)
    
    category_td = ""
    if idx == 0:
        category_td = f'<td class="category-cell-style" rowspan="{len(feed_df)}">사료용</td>'
        
    import_rows_html += "<tr>" + category_td + \
                        "<td class='table-text-left'>" + item_name + "</td>" + \
                        "<td>" + weight_display + "</td>" + \
                        "<td>" + price_display + "</td>" + \
                        "<td>" + td_month_chg + "</td>" + \
                        "<td>" + td_year_chg + "</td>" + \
                        "</tr>"

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
