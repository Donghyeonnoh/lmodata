import streamlit as st
import pandas as pd
import google.generativeai as genai
import io

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
    # --- [v4.0] 데이터 검색 (AI 없음) ---
    st.header("1. 🕵️ 데이터 직접 검색하기 (AI 없음)")
    st.info("먼저 분석하고 싶은 데이터를 필터링해서 정확하게 찾아보세요.")

    filter_column = st.selectbox("필터링할 기준 컬럼을 선택하세요:", df_original.columns)
    
    unique_values = df_original[filter_column].unique()
    selected_value = st.selectbox(f"'{filter_column}' 컬럼에서 어떤 값을 찾을까요?", unique_values)

    df_filtered = df_original[df_original[filter_column] == selected_value]

    st.subheader(f"🔍 '{filter_column}' 컬럼에서 '{selected_value}'(으)로 검색된 결과 ({len(df_filtered)}건)")
    st.dataframe(df_filtered)

    st.write("---")

    # --- [v4.0] 검색된 데이터 기반 AI 분석 ---
    st.header("2. 🤖 위 검색 결과에 대해 AI에게 질문하기")
    
    if not df_filtered.empty:
        question = st.text_area("위 표의 데이터에 대해 궁금한 점을 질문해주세요.", height=100, placeholder=f"예시: 이 데이터의 평균 가격은 얼마인가요?")

        if st.button("🚀 분석 요청하기!"):
            if not question:
                st.warning("질문을 입력해주세요!")
            else:
                with st.spinner("🧠 DAVER가 스스로 생각하고 분석 중입니다..."):
                    # --- [v4.1 핵심 수정!] 특정 예시를 제거하고, 스스로 생각하도록 규칙 강화 ---
                    total_rows = len(df_filtered)
                    
                    prompt = f"""
                    당신은 Python Pandas와 Streamlit을 전문적으로 다루는 AI 데이터 분석가입니다.
                    당신의 임무는 [사용자 질문]을 분석하고, [분석할 데이터]의 구조를 참고하여 아래 [작업 흐름]에 따라 답변을 생성하는 것입니다.

                    **[작업 흐름]**
                    1.  **생각의 과정 (Chain of Thought):** [사용자 질문]을 해결하기 위한 계획을 한글로 1, 2, 3... 단계별로 세웁니다. 이 계획은 매우 구체적이어야 합니다. 어떤 컬럼을 사용할 것인지, 어떤 Pandas 함수를 적용할 것인지 명시해야 합니다.
                    2.  **최종 실행 코드:** 위 '생각의 과정'에서 세운 계획을 그대로 실행하는 Python 코드 블록만 생성합니다. 결과는 반드시 Streamlit(st)을 사용해 화면에 출력해야 합니다.

                    **[규칙]**
                    * 코드에서 사용할 DataFrame의 변수명은 `df` 입니다.
                    * [분석할 데이터]에 없는 내용은 절대로 상상해서 답변하면 안 됩니다.
                    * 답변은 '생각의 과정'과 '최종 실행 코드' 두 부분으로만 구성되어야 합니다. 다른 말은 덧붙이지 마세요.

                    **[분석할 데이터]**
                    * **총 데이터 개수:** {total_rows}
                    * **컬럼 목록:** {', '.join(df_filtered.columns)}
                    * **데이터 샘플 (상위 5개):**
                    {df_filtered.head().to_csv()}

                    **[사용자 질문]**
                    "{question}"
                    """
                    
                    generated_code = ""
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        
                        response_text = response.text
                        thought_process = ""

                        if "## 최종 실행 코드" in response_text:
                            parts = response_text.split("## 최종 실행 코드")
                            thought_process = parts[0].replace("## 생각의 과정", "").strip()
                            generated_code = parts[1].replace("```python", "").replace("```", "").strip()
                        else:
                            generated_code = response_text.replace("```python", "").replace("```", "").strip()

                        st.subheader("📊 분석 결과")
                        exec(generated_code, {'df': df_filtered, 'st': st, 'pd': pd})

                        with st.expander("🤖 AI의 '판단' 과정 및 실행 코드 보기 (검증용)"):
                            st.subheader("🤔 생각의 과정 (AI의 계획서)")
                            st.markdown(thought_process)
                            st.subheader("💻 최종 실행 코드")
                            st.code(generated_code, language='python')
                            
                    except Exception as e:
                        st.error(f"코드를 실행하는 중 오류가 발생했습니다: {e}")
                        if generated_code:
                            st.error("AI가 생성한 아래 코드에서 문제가 발생했을 수 있습니다:")
                            st.code(generated_code, language='python')
    else:
        st.info("위에 검색된 데이터가 없어서 AI에게 질문할 수 없습니다.")
else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")
