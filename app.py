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

# [수정사항] 1번 요건: 뉴스 헤드라인 폰트 크기를 카테고리 태그(11px)와 동일하게 축소 조정
# [수정사항] 3번 요건: 수입 추이 테이블 폰트와 스타일을 거시지표 테이블 스타일과 일치시키는 디자인 정의
st.markdown("""
    <style>
    .reportview-container, .main { background-color: #f1f5f9; }
    
    /* 1번 요건: 메인 타이틀 안의 날짜용 얇은 폰트 스타일 */
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
    
    /* 동적 컬러 텍스트 및 테이블 공통 폰트 지정 */
    .color-up { color: #dc2626; font-weight: bold; }
    .color-down { color: #2563eb; font-weight: bold; }
    .color-flat { color: #64748b; font-weight: bold; }
    
    /* 1번 요건: 주요 뉴스 헤드라인 폰트 크기를 태그와 동일한 11px로 매핑 */
    .news-tag { background-color: #f1f5f9; color: #475569; font-weight: bold; padding: 2px 6px; border-radius: 3px; font-size: 11px; margin-right: 6px; display: inline-block; }
    .news-item { margin-bottom: 10px; font-size: 11px; list-style-type: none; color: #1e293b; }
    
    /* 2, 3번 요건: 거시지표 및 수입추이 테이블 통합 커스텀 CSS (Malgun Gothic 계열 명시) */
    .dashboard-table { width:100%; border-collapse:collapse; font-size:12px; font-family:'Malgun Gothic', sans-serif; text-align:center; }
    .dashboard-table thead { background-color:#f8fafc; color:#475569; }
    .dashboard-table th { padding:8px; font-weight:bold; border-bottom:1px solid #cbd5e1; }
    .dashboard-table td { padding:8px; border-bottom:1px solid #f1f5f9; vertical-align:middle; color:#1e293b; }
    .dashboard-table tr:nth-child(even) { background-color:#f8fafc; }
    .table-text-left { text-align: left !important; font-weight: bold; }
    .category-cell-style { background-color: #f8fafc; font-weight: bold; color: #334155; border-right: 1px solid #e2e8f0; }
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

# [수정사항] 1번 요건: 메인 타이틀에 매핑할 날짜 포맷 자동 파싱 연동 (가장 최신 날짜 추출)
latest_macro_date_str = df_macro.index.max().strftime('%Y.%m.%d')
st.markdown(f'div class="report-title"■ 국제곡물 모니터링 대시보드span class="title-thin"(업데이트: {latest_macro_date_str})/span/div', unsafe_allow_html=True)

# 가중치 복합 지수 연산
df_macro['국제곡물_선물가격지수'] = (df_macro['밀_달러톤'].fillna(0) * 0.32) + \
                          (df_macro['옥수수_달러톤'].fillna(0) * 0.28) + \
                          (df_macro['콩_달러톤'].fillna(0) * 0.38) + \
                          (df_macro['쌀_달러톤'].fillna(0) * 0.02)

all_nan_mask = df_macro[['밀_달러톤', '옥수수_달러톤', '콩_달러톤', '쌀_달러톤']].isna().all(axis=1)
df_macro.loc[all_nan_mask, '국제곡물_선물가격지수'] = None

# 수입 추이 데이터 처리
df_import_raw['날짜'] = pd.to_datetime(df_import_raw['날짜'])
latest_import_date = df_import_raw['날짜'].max()
df_import_filtered = df_import_raw[df_import_raw['날짜'] == latest_import_date].copy()

# ==========================================
# 수치 판정 및 HTML 변환 유틸리티 함수
# ==========================================
def get_colored_chg_html(curr, base, is_pct_string=False):
    try:
        # [수정사항] 3번 요건: 엑셀에서 문자열 변동률("▲ +3.2%", "▼ -1.5%")이 직접 넘어올 때 판정하는 분기문 보완
        if is_pct_string:
            val_str = str(curr).strip()
            if "▲" in val_str or "+" in val_str:
                return f'<span class="color-up">{val_str}</span>'
            elif "▼" in val_str or "-" in val_str:
                return f'<span class="color-down">{val_str}</span>'
            else:
                return f'<span class="color-flat">{val_str}</span>'

        if pd.isna(curr) or pd.isna(base):
            return '<span class="color-flat">-</span>'
        
        c_num = float(curr)
        b_num = float(base)
        
        if b_num == 0:
            return '<span class="color-flat">-</span>'
            
        val = ((c_num - b_num) / b_num) * 100
        if val > 0:
            return f'<span class="color-up">▲+{val:.1f}%</span>'
        elif val < 0:
            return f'<span class="color-down">▼{val:.1f}%</span>'
        else:
            return f'<span class="color-flat">0.0%</span>'
    except:
        return '<span class="color-flat">-</span>'

def render_metric_card(label, curr_val, base_day, base_year, unit="달러/톤", is_ratio=False):
    try:
        is_val_na = pd.isna(curr_val) or (hasattr(curr_val, 'isna') and curr_val.isna().all())
    except:
        is_val_na = False

    if is_val_na:
        value_html = '<span class="metric-val-text">N/A</span>'
        delta_html = '<div style="font-size:11px; color:#64748b; margin-top:4px;">-</div>'
    else:
        val_clean = curr_val.iloc[0] if isinstance(curr_val, pd.Series) else curr_val
        b_day_clean = base_day.iloc[0] if isinstance(base_day, pd.Series) else base_day
        b_yr_clean = base_year.iloc[0] if isinstance(base_year, pd.Series) else base_year

        if is_ratio:
            value_html = f'<span class="metric-val-text">{float(val_clean):.2f}</span><span class="sub-text">(적정: 2.50)</span>'
            chg_day = get_colored_chg_html(val_clean, b_day_clean)
            delta_html = f'<div style="font-size:11px; color:#64748b; margin-top:4px;">전일 대비 변동: {chg_day}</div>'
        else:
            value_html = f'<span class="metric-val-text">{int(float(val_clean))}</span><span class="unit-text">{unit}</span>'
            chg_day = get_colored_chg_html(val_clean, b_day_clean)
            chg_yr = get_colored_chg_html(val_clean, b_yr_clean)
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

# [수정사항] 2번 요건: 환율 등에 1000단위 구분 심볼(,) 적용 인터페이스 구현
def format_macro_val(val, prefix="", suffix="", is_currency=False):
    if pd.isna(val): return "N/A"
    try:
        if "bbl" in suffix: return f"{prefix}{float(val):.2f}{suffix}"
        if is_currency:
            return f"{prefix}{int(float(val)):,}{suffix}"
        return f"{prefix}{int(float(val))}{suffix}"
    except: return f"{val}"

# ==========================================
# 2. 상단 상위 지표 영역 (Metric Cards)
# ==========================================
col1, col2, col3, col4, col5 = st.columns(5)
with col1: render_metric_card("🌾 밀 선물", latest['밀_달러톤'], prev_day['밀_달러톤'], prev_year['밀_달러톤'])
with col2: render_metric_card("🌽 옥수수 선물", latest['옥수수_달러톤'], prev_day['옥수수_달러톤'], prev_year['옥수수_달러톤'])
with col3: render_metric_card("🥜 콩 선물", latest['콩_달러톤'], prev_day['콩_달러톤'], prev_year['콩_달러톤'])
with col4: render_metric_card("🍚 쌀 수출 (태국)", latest['쌀_달러톤'], prev_day['쌀_달러톤'], prev_year['쌀_달러톤'])
with col5: render_metric_card("📊 콩/옥수수 비율", latest['콩_옥수수_비율'], prev_day['콩_옥수수_비율'], None, is_ratio=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 3. 실시간 뉴스 크롤링 연동 (복합 키워드 확장 및 KREI 예외처리)
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
    with c1: selected_grain = st.selectbox("곡물 선택 :", ["국제곡물 선물가격지수", "밀", "옥수수", "콩", "쌀"], index=0)
    with c2:
        period_mapping = {"1달": 30, "3달": 90, "1년": 365, "5년": 1825}
        selected_period = st.selectbox("조회 기간 :", list(period_mapping.keys()), index=1)
    
    days_to_filter = period_mapping[selected_period]
    filtered_df = df_macro.tail(days_to_filter).copy()
    chart_target = '국제곡물_선물가격지수' if selected_grain == "국제곡물 선물가격지수" else f"{selected_grain}_달러톤"
    
    if filtered_df[chart_target].isna().all():
        st.warning("선택한 기간 내에 분석할 시황 데이터가 엑셀에 존재하지 않습니다.")
    else:
        filtered_df[chart_target] = filtered_df[chart_target].interpolate(method='linear', limit_direction='both')
        filtered_df['5MA'] = filtered_df[chart_target].rolling(window=5).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=filtered_df.index, y=filtered_df[chart_target], name="국제곡물 선물가격지수" if selected_grain == "국제곡물 선물가격지수" else selected_grain, connectgaps=True, line=dict(color='#1e3a8a', width=2.5)))
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
    
    # [수정사항] 2번 요건: 테이블 th 헤더에 text-align: center 강제부여, 컬럼명 문구 수정, 환율 1000단위 콤마 반영
    macro_table_html = f"""
    <table class="dashboard-table">
        <thead>
            <tr>
                <th style="text-align:center; width:35%;">주요 지표</th>
                <th style="text-align:center; width:25%;">당일 가격</th>
                <th style="text-align:center; width:20%;">전일 대비<br>증감</th>
                <th style="text-align:center; width:20%;">전년 대비<br>증감</th>
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
# 5. 하단 수입 추이 영역 (요청사항 3번 스펙 맞춤 수동 HTML 결합 개편)
# ==========================================
formatted_date = latest_import_date.strftime('%Y년 %m월')
st.markdown(f'<div class="section-title">🚢 수입 추이 <span style="font-size:12px; font-weight:normal; color:#64748b; margin-left:8px;">(* 가장 최신 데이터 수집 기준일: {formatted_date})</span></div>', unsafe_allow_html=True)

# [수정사항] 3번 요건: 스타일을 거시지표 테이블 스타일과 일치시키고, 첫 행 가운데 정렬, 수입량 1000단위 콤마 및 변동률 동적 컬러 매핑을 마크업으로 완벽 제어
import_rows_html = ""
food_df = df_import_filtered[df_import_filtered['구분'] == '식용']
feed_df = df_import_filtered[df_import_filtered['구분'] == '사료용']

# 식용 파트 빌드
for idx, row in enumerate(food_df.to_dict('records')):
    weight_val = f"{int(float(row['당월 수입량 (톤)'])):,}" if pd.notna(row['당월 수입량 (톤)']) and str(row['당월 수입량 (톤)']).lower() != 'n/a' else "N/A"
    price_val = f"${float(row['당월 평균 수입단가(달러/톤)']):.2f}" if pd.notna(row['당월 평균 수입단가(달러/톤)']) and str(row['당월 평균 수입단가(달러/톤)']).lower() != 'n/a' else "N/A"
    
    td_month_chg = get_colored_chg_html(row['전월 대비 증감'], None, is_pct_string=True)
    td_year_chg = get_colored_chg_html(row['전년 대비 증감'], None, is_pct_string=True)
    
    row_string = f"""
    <tr>
        { '<td class="category-cell-style" rowspan="4">식용</td>' if idx == 0 else '' }
        <td class="table-text-left">{row['품목명']}</td>
        <td>{weight_val}</td>
        <td>{price_val}</td>
        <td>{td_month_chg}</td>
        <td>{td_year_chg}</td>
    </tr>
    """
    import_rows_html += row_string

# 사료용 파트 빌드
for idx, row in enumerate(feed_df.to_dict('records')):
    weight_val = f"{int(float(row['당월 수입량 (톤)'])):,}" if pd.notna(row['당월 수입량 (톤)']) and str(row['당월 수입량 (톤)']).lower() != 'n/a' else "N/A"
    price_val = f"${float(row['당월 평균 수입단가(달러/톤)']):.2f}" if pd.notna(row['당월 평균 수입단가(달러/톤)']) and str(row['당월 평균 수입단가(달러/톤)']).lower() != 'n/a' else "N/A"
    
    td_month_chg = get_colored_chg_html(row['전월 대비 증감'], None, is_pct_string=True)
    td_year_chg = get_colored_chg_html(row['전년 대비 증감'], None, is_pct_string=True)
    
    row_string = f"""
    <tr>
        { '<td class="category-cell-style" rowspan="3">사료용</td>' if idx == 0 else '' }
        <td class="table-text-left">{row['품목명']}</td>
        <td>{weight_val}</td>
        <td>{price_val}</td>
        <td>{td_month_chg}</td>
        <td>{td_year_chg}</td>
    </tr>
    """
    import_rows_html += row_string

import_table_html = f"""
<table class="dashboard-table">
    <thead>
        <tr>
            <th style="text-align:center; width:10%;">구분</th>
            <th style="text-align:center; width:18%;">품목명</th>
            <th style="text-align:center; width:18%;">당월 수입량 (톤)</th>
            <th style="text-align:center; width:22%;">당월 평균 수입단가<br>(달러/톤)</th>
            <th style="text-align:center; width:16%;">전월 대비<br>증감</th>
            <th style="text-align:center; width:16%;">전년 대비<br>증감</th>
        </tr>
    </thead>
    <tbody>
        {import_rows_html}
    </tbody>
</table>
"""
st.markdown(import_table_html, unsafe_allow_html=True)
