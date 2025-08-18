import streamlit as st
import pandas as pd
import google.generativeai as genai
import io

# --- 1. 페이지 초기 설정 ---
st.set_page_config(
    page_title="데이버 - 우리 팀 데이터 비서",
    page_icon="📊",
    layout="wide",
)

# --- [수정 1] 제목 변경 및 초록창 스타일 추가 ---
# 네이버 스타일의 초록색 배경을 가진 검색창 헤더를 만듭니다.
st.markdown(
    """
    <style>
    .title-container {
        background-color: #03C75A;
        padding: 20px 20px 10px 20px;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
    }
    .title-font {
        font-size: 36px;
        font-weight: bold;
    }
    .subtitle-font {
        font-size: 16px;
    }
    </style>
    <div class="title-container">
        <p class="title-font">데이버 (Datavor) 📊</p>
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
        return df
    except Exception as e:
        st.error(f"데이터를 불러오는 데 실패했습니다. 구글 시트 링크와 공유 설정을 확인해주세요: {e}")
        return None

df = load_data(SHEET_URL)

if df is not None:
    # --- [수정 2] 데이터베이스 미리보기 부분 삭제 ---
    # st.subheader("✅ 데이터베이스 미리보기 (최신 5개)")
    # st.dataframe(df.head())
    # st.write("---")

    # --- 4. 사용자 질문 입력 ---
    question = st.text_area("데이터에 대해 궁금한 점을 자연스러운 문장으로 질문해주세요.", height=100, placeholder="예시: 24개의 면화 작물 데이터를 모두 찾아줘")

    if st.button("🚀 분석 요청하기!"):
        if not question:
            st.warning("질문을 입력해주세요!")
        else:
            with st.spinner("🧠 데이버가 생각 중입니다... 잠시만 기다려주세요."):
                # --- 5. AI에게 데이터 요약 정보 전달 ---
                buffer = io.StringIO()
                df.info(buf=buffer)
                df_info = buffer.getvalue()
                
                prompt = f"""
                당신은 Python Pandas와 Streamlit을 전문적으로 다루는 AI 데이터 분석가입니다.
                당신의 임무는 사용자의 질문을 분석하고, 주어진 DataFrame의 구조 정보를 바탕으로 질문에 답하는 **Pandas 코드**를 생성하는 것입니다.

                **규칙:**
                1. 절대로, 절대로 최종 답변을 계산하거나 결과를 직접 텍스트로 말하지 마세요. 오직 Python 코드만 생성해야 합니다.
                2. 생성된 코드는 Streamlit을 사용하여 결과를 화면에 표시해야 합니다 (예: `st.write()`, `st.dataframe()`, `st.bar_chart()`).
                3. 주어진 DataFrame의 변수명은 `df` 입니다. 이 변수명을 코드에서 사용하세요.
                4. 다른 설명이나 주석 없이, 실행 가능한 Python 코드 블록만 반환하세요.

                **[DataFrame 구조 정보]**
                * **컬럼 정보 및 데이터 타입:**
                ```
                {df_info}
                ```
                * **데이터 샘플 (상위 5개 행):**
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
                    
                    # --- 6. AI가 만든 코드를 받아서 '우리 앱'이 직접 실행 ---
                    exec(generated_code, {'df': df, 'st': st, 'pd': pd})

                    with st.expander("🤖 AI가 실행한 분석 코드 보기 (검증용)"):
                        st.code(generated_code, language='python')
                        
                except Exception as e:
                    st.error(f"코드를 실행하는 중 오류가 발생했습니다: {e}")

else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")
