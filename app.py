import streamlit as st
import pandas as pd
import google.generativeai as genai
import io

# --- 1. 페이지 초기 설정 ---
st.set_page_config(
    page_title="데이버 - LMO팀 데이터 비서",
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
        <p class="title-font">데이버 (DaVer) 📊</p>
        <p class="subtitle-font">우리 팀을 위한 데이터 분석 비서</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- 2. API Key 및 모델 설정 ---
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

df = load_data(SHEET_URL)

if df is not None:
    # --- AI 분석 섹션 ---
    st.header("1. 🤖 AI에게 질문하기")
    question = st.text_area("데이터에 대해 궁금한 점을 자연스러운 문장으로 질문해주세요.", height=100, placeholder="예시: 구글시트에 몇 개의 샘플이 있지?")

    if st.button("🚀 분석 요청하기!"):
        if not question:
            st.warning("질문을 입력해주세요!")
        else:
            with st.spinner("🧠 데이버가 생각 중입니다..."):
                # --- [v3.3 핵심 수정!] AI가 오해하지 않도록 데이터 정보를 명확하게 전달 ---
                total_rows = len(df)
                
                buffer = io.StringIO()
                df.info(buf=buffer)
                df_info = buffer.getvalue()

                prompt = f"""
                당신은 Python Pandas와 Streamlit을 전문적으로 다루는 AI 데이터 분석가입니다.
                당신의 임무는 사용자의 질문을 분석하고, 주어진 DataFrame의 구조 정보를 바탕으로 질문에 답하는 **Pandas 코드**를 생성하는 것입니다.

                **규칙:**
                1. 절대로 최종 답변을 직접 텍스트로 말하지 마세요. 오직 Python 코드만 생성해야 합니다.
                2. 생성된 코드는 Streamlit을 사용하여 결과를 화면에 표시해야 합니다. (예: `st.write()`, `st.dataframe()`)
                3. 주어진 DataFrame의 변수명은 `df` 입니다. 이 변수명을 코드에서 사용하세요.
                4. 다른 설명 없이, 실행 가능한 Python 코드 블록만 반환하세요.
                5. '데이터 샘플'은 데이터의 일부일 뿐이므로, 전체 개수를 세는 데 사용하면 안 됩니다. 전체 개수는 '총 데이터 개수'를 참고하세요.

                **[DataFrame 구조 정보]**
                * **총 데이터 개수 (Total Rows):** {total_rows}
                * **컬럼 정보 및 데이터 타입:**
                ```
                {df_info}
                ```
                * **데이터 샘플 (상위 5개 행, 전체 개수가 아님):**
                ```
                {df.head().to_csv()}
                ```

                **[사용자 질문]**
                "{question}"

                **[생성할 Python 코드]**
                """
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    generated_code = response.text.replace("```python", "").replace("```", "").strip()
                    st.subheader("📊 분석 결과")
                    exec(generated_code, {'df': df, 'st': st, 'pd': pd})
                    with st.expander("🤖 AI가 실행한 분석 코드 보기 (검증용)"):
                        st.code(generated_code, language='python')
                except Exception as e:
                    st.error(f"코드를 실행하는 중 오류가 발생했습니다: {e}")

    st.write("---")
    
    # --- 데이터 검사기 섹션 ---
    st.header("2. 🕵️ 데이터 직접 검사하기 (AI 없음)")
    st.info("AI가 데이터를 잘못 인식하는 것 같다면, 여기서 직접 확인해보세요.")
    try:
        column_to_inspect = st.selectbox("검사할 컬럼을 선택하세요:", df.columns)
        if st.button("🔍 컬럼 내용 검사하기"):
            st.subheader(f"'{column_to_inspect}' 컬럼의 값 종류 및 개수")
            value_counts = df[column_to_inspect].value_counts().reset_index()
            value_counts.columns = [column_to_inspect, '개수']
            st.dataframe(value_counts)
            st.success("위 표는 AI를 거치지 않은 100% 정확한 원본 데이터의 통계입니다.")
    except Exception as e:
        st.error(f"검사 중 오류가 발생했습니다: {e}")
else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")
