import streamlit as st
import pandas as pd
import google.generativeai as genai

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

# --- 2. API Key 설정 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("앗! Gemini API Key를 설정하지 않으셨군요. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# --- 3. 데이터 로딩 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-0gW_EY8VOTF46pQJ0pB85mskdyyq_-1WKf0xlqHPrM/edit?usp=sharing"

@st.cache_data(ttl=600)
def load_data(url):
    try:
        csv_url = url.replace("/edit?usp=sharing", "/export?format=csv")
        df = pd.read_csv(csv_url)
        df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는 데 실패했습니다: {e}")
        return None

df_original = load_data(SHEET_URL)

if df_original is not None:
    st.header("1. 🕵️ 데이터 직접 검색하기 (다중 필터링)")
    st.info("여러 필터 조건을 적용하여 원하는 데이터를 정확하게 찾아보세요.")

    # --- 4. [찐 최종 핵심!] 다중 필터링 인터페이스 ---
    try:
        cols = st.columns(2) # 2개의 컬럼으로 화면을 나눔

        # 필터 조건 1
        with cols[0]:
            st.subheader("필터 조건 1")
            filter_col1 = st.selectbox("기준 컬럼 1:", df_original.columns, key="col1")
            unique_values1 = ['--전체--'] + list(df_original[filter_col1].unique())
            selected_val1 = st.selectbox(f"'{filter_col1}'에서 찾을 값:", unique_values1, key="val1")

        # 필터 조건 2
        with cols[1]:
            st.subheader("필터 조건 2")
            filter_col2 = st.selectbox("기준 컬럼 2:", df_original.columns, index=1, key="col2") # 기본으로 두번째 컬럼 선택
            unique_values2 = ['--전체--'] + list(df_original[filter_col2].unique())
            selected_val2 = st.selectbox(f"'{filter_col2}'에서 찾을 값:", unique_values2, key="val2")

        # 필터링 로직
        df_filtered = df_original.copy() # 원본 데이터 복사로 시작
        
        filter_summary = [] # 적용된 필터 요약을 위한 리스트

        if selected_val1 != '--전체--':
            df_filtered = df_filtered[df_filtered[filter_col1] == selected_val1]
            filter_summary.append(f"'{filter_col1}'이(가) '{selected_val1}'인 조건")
            
        if selected_val2 != '--전체--':
            df_filtered = df_filtered[df_filtered[filter_col2] == selected_val2]
            filter_summary.append(f"'{filter_col2}'이(가) '{selected_val2}'인 조건")
        
        # 검색 결과 표시
        st.write("---")
        if filter_summary:
            st.subheader(f"🔍 검색 결과 ({' 그리고 '.join(filter_summary)})")
        else:
            st.subheader("🔍 전체 데이터")

        st.dataframe(df_filtered)
        st.success(f"총 {len(df_filtered)}건의 데이터가 검색되었습니다.")

        # --- 5. AI 요약 기능 ---
        if not df_filtered.empty:
            st.write("---")
            st.header("2. 🤖 위 검색 결과 한 줄 요약하기 (AI)")
            
            if st.button("✨ AI에게 요약 요청하기", type="primary"):
                with st.spinner("🧠 DAVER가 검색된 데이터를 요약 중입니다..."):
                    try:
                        total_count = len(df_filtered)
                        top_regions = df_filtered['주소'].value_counts().nlargest(3).to_dict() if '주소' in df_filtered.columns else {}
                        top_regions_str = ", ".join([f"{region} ({count}건)" for region, count in top_regions.items()])

                        prompt = f"""
                        당신은 데이터 요약 전문가입니다. 아래에 제공되는 [핵심 정보]를 바탕으로, 자연스러운 한글 문장으로 데이터 요약 보고서를 작성해주세요.

                        [핵심 정보]
                        - 분석 조건: {' 그리고 '.join(filter_summary) if filter_summary else "전체 데이터"}
                        - 총 데이터 건수: {total_count}건
                        - 상위 3개 발견 주소: {top_regions_str if top_regions_str else "정보 없음"}
                        
                        [작성 지침]
                        - 위의 [핵심 정보]에 있는 숫자와 내용을 **그대로 사용하여** 요약문을 작성하세요.
                        - "핵심 정보에 따르면" 과 같은 말은 빼고, 자연스럽게 분석한 것처럼 작성해주세요.
                        """
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        
                        st.subheader("📝 AI 요약 결과")
                        st.success(response.text)

                    except Exception as e:
                        st.error(f"AI 요약 중 오류가 발생했습니다: {e}")

    except Exception as e:
        st.error(f"데이터를 처리하는 중 오류가 발생했습니다: {e}")

else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")
