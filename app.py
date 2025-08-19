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
    st.header("1. 🕵️ 데이터 직접 검색하기")
    st.info("아래 드롭다운 메뉴를 사용하여 원하는 데이터를 정확하게 찾아보세요.")

    try:
        filter_column = st.selectbox("필터링할 기준 컬럼을 선택하세요:", df_original.columns)
        unique_values = df_original[filter_column].unique()
        selected_value = st.selectbox(f"'{filter_column}' 컬럼에서 어떤 값을 찾을까요?", unique_values)

        if st.button("🔍 검색 실행", type="primary"):
            st.session_state.df_filtered = df_original[df_original[filter_column] == selected_value]
            st.session_state.selected_value = selected_value
            st.session_state.filter_column = filter_column

    except Exception as e:
        st.error(f"데이터를 검색하는 중 오류가 발생했습니다: {e}")
        
    if 'df_filtered' in st.session_state:
        df_filtered = st.session_state.df_filtered
        filter_column = st.session_state.filter_column
        selected_value = st.session_state.selected_value
        
        st.subheader(f"'{filter_column}' 컬럼에서 '{selected_value}'(으)로 검색된 결과 ({len(df_filtered)}건)")
        st.dataframe(df_filtered)
        
        if df_filtered.empty:
            st.warning("선택하신 조건에 맞는 데이터가 없습니다.")
        else:
            st.write("---")
            st.header("2. 🤖 위 검색 결과 한 줄 요약하기 (AI)")
            
            if st.button("✨ AI에게 요약 요청하기", type="secondary"):
                with st.spinner("🧠 DAVER가 검색된 데이터를 요약 중입니다..."):
                    try:
                        # --- [최종 핵심 수정!] AI에게 '계산'을 시키지 않고, '팩트'를 알려준 뒤 '글쓰기'만 요청 ---
                        
                        # 1. Python(Pandas)으로 100% 정확한 팩트를 미리 계산
                        total_count = len(df_filtered)
                        top_regions = df_filtered['주소'].value_counts().nlargest(3).to_dict()
                        top_regions_str = ", ".join([f"{region} ({count}건)" for region, count in top_regions.items()])

                        # 2. 계산된 팩트를 AI에게 명확하게 전달
                        prompt = f"""
                        당신은 데이터 요약 전문가입니다. 아래에 제공되는 [핵심 정보]를 바탕으로, 자연스러운 한글 문장으로 데이터 요약 보고서를 작성해주세요.

                        **[핵심 정보]**
                        - 분석 대상: '{selected_value}'
                        - 총 데이터 건수: {total_count}건
                        - 상위 3개 발견 주소: {top_regions_str}
                        
                        **[작성 지침]**
                        - 위의 [핵심 정보]에 있는 숫자와 내용을 **그대로 사용하여** 요약문을 작성하세요.
                        - 절대로 숫자를 임의로 바꾸거나 없는 말을 만들지 마세요.
                        - 한두 문단의 간결한 보고서 형식으로 작성해주세요.
                        - "핵심 정보에 따르면" 과 같은 말은 빼고, 자연스럽게 분석한 것처럼 작성해주세요.
                        """
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        
                        st.subheader("📝 AI 요약 결과")
                        st.success(response.text)

                    except Exception as e:
                        st.error(f"AI 요약 중 오류가 발생했습니다: {e}")

else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")
