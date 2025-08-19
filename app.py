import streamlit as st
import pandas as pd

# --- 1. 페이지 초기 설정 ---
st.set_page_config(
    page_title="DAVER - 우리 팀 데이터 비서",
    page_icon="📊",
    layout="wide",
)

# --- 제목 및 스타일 ---
st.markdown(
    """
    <style>
    .title-container {
        background-color: #03C75A; padding: 20px 20px 10px 20px; border-radius: 10px;
        color: white; text-align: center; margin-bottom: 20px;
    }
    .title-font { font-size: 36px; font-weight: bold; }
    .subtitle-font { font-size: 16px; }
    </style>
    <div class="title-container">
        <p class="title-font">DAVER (Data Analyzer & Visualizer for Everyone) 📊</p>
        <p class="subtitle-font">우리 팀을 위한 데이터 분석 비서</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- 2. 데이터 로딩 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-0gW_EY8VOTF46pQJ0pB85mskdyyq_-1WKf0xlqHPrM/edit?usp=sharing"

@st.cache_data(ttl=600) # 10분마다 데이터를 새로고침합니다.
def load_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        df = pd.read_csv(csv_url)
        # 데이터를 불러올 때 모든 텍스트 컬럼의 양쪽 공백을 자동으로 제거합니다.
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는 데 실패했습니다: {e}")
        return None

df_original = load_data(SHEET_URL)

# 데이터가 성공적으로 로드되었을 때만 아래 내용을 표시합니다.
if df_original is not None:
    st.header("🕵️ 데이터 직접 검색하기")
    st.info("아래 드롭다운 메뉴를 사용하여 원하는 데이터를 정확하게 찾아보세요.")

    # --- 3. 데이터 직접 검색 (수동 필터) ---
    try:
        # 필터링할 컬럼을 사용자가 선택
        filter_column = st.selectbox("필터링할 기준 컬럼을 선택하세요:", df_original.columns)
        
        # 선택된 컬럼의 고유한 값들을 가져와서 선택지로 제공
        unique_values = df_original[filter_column].unique()
        selected_value = st.selectbox(f"'{filter_column}' 컬럼에서 어떤 값을 찾을까요?", unique_values)

        # '검색' 버튼을 추가하여 사용자가 원할 때 필터링 실행
        if st.button("🔍 검색 실행", type="primary"):
            # 선택된 값으로 데이터 필터링 (AI 없음, 100% 정확)
            df_filtered = df_original[df_original[filter_column] == selected_value]

            st.subheader(f"'{filter_column}' 컬럼에서 '{selected_value}'(으)로 검색된 결과 ({len(df_filtered)}건)")
            st.dataframe(df_filtered)
            
            # 검색된 데이터가 없을 경우 메시지 표시
            if df_filtered.empty:
                st.warning("선택하신 조건에 맞는 데이터가 없습니다.")

    except Exception as e:
        st.error(f"데이터를 검색하는 중 오류가 발생했습니다: {e}")

else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")
