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

# --- [수정됨] 제목 변경 및 초록창 스타일 추가 ---
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
        <p class="title-font">DAVER (Data Analyzer & Visualizer for Everyone) 📊</p>
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
# [수정됨] 사용자님의 구글 시트 URL 적용
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
    question = st.text_area("데이터에 대해 궁금한 점을 자연스러운 문장으로 질문해주세요.", height=100, placeholder="예시: 면화 작물의 개수는 총 몇 개인가요?")

    if st.button("🚀 분석 요청하기!"):
        if not question:
            st.warning("질문을 입력해주세요!")
        else:
            with st.spinner("🧠 DAVER가 계획을 세우고 분석 중입니다..."):
                # --- [v3.4 핵심!] '판단' 단계를 강제하는 Chain of Thought 프롬프트 ---
                total_rows = len(df)

                buffer = io.StringIO()
                df.info(buf=buffer)
                df_info = buffer.getvalue()

                prompt = f"""
                당신은 Python Pandas와 Streamlit을 전문적으로 다루는 AI 데이터 분석가입니다.
                당신의 임무는 사용자의 질문을 분석하고, **먼저 '생각의 과정'을 통해 분석 계획을 세운 뒤**, 그 계획에 따라 최종 코드를 생성하는 것입니다.

                **지켜야 할 흐름:**
                1.  **생각의 과정 (Chain of Thought):** 사용자의 질문을 어떻게 해결할지 단계별로 계획을 세웁니다. 이 계획은 **간결하고 명확한 한국어**로 작성합니다.
                2.  **최종 실행 코드:** 위 계획에 따라, Streamlit으로 결과를 시각화하거나 텍스트로 출력하는 **실행 가능한 Python Pandas 코드 블록**만 생성합니다.

                **규칙:**
                * 주어진 DataFrame의 변수명은 `df` 입니다.
                * '총 데이터 개수'는 {total_rows}개 입니다. 샘플 데이터와 혼동하지 마세요.
                * 결과물은 아래 '출력 형식 예시'를 반드시, 글자 하나 틀리지 않고 똑같이 따라야 합니다.

                **제공된 데이터 정보:**
                * **총 데이터 개수:** {total_rows}
                * **컬럼 정보 및 데이터 타입:**
                {df_info}

                **사용자 질문:**
                "{question}"

                **출력 형식 예시:**
                ## 생각의 과정
                1.  질문에서 요구하는 특정 컬럼을 찾는다. (예: '작물')
                2.  해당 컬럼에서 특정 값(예: '면화')과 정확히 일치하는 데이터를 필터링한다.
                3.  필터링된 데이터의 총 개수를 계산한다.
                4.  결과를 사용자에게 명확하게 보여주는 Streamlit 코드를 작성한다.

                ## 최종 실행 코드
                \`\`\`python
                # 예시: '작물' 컬럼에서 '면화'를 찾아 개수 세기
                target_crop = '면화'
                filtered_df = df['작물'][df['작물'] == target_crop]
                count = len(filtered_df)
                st.write(f"'{target_crop}'의 총 개수는 {count}개입니다.")
                \`\`\`
                """
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)

                    # AI의 답변에서 '생각의 과정'과 '코드'를 분리
                    response_text = response.text
                    thought_process = ""
                    generated_code = ""

                    if "## 최종 실행 코드" in response_text:
                        parts = response_text.split("## 최종 실행 코드")
                        thought_process = parts[:parts.index("## 최종 실행 코드")].replace("## 생각의 과정", "").strip()
                        generated_code = parts[-1].replace("\`\`\`python", "").replace("\`\`\`", "").strip()
                    else:
                        generated_code = response_text.replace("\`\`\`python", "").replace("\`\`\`", "").strip()

                    st.subheader("📊 분석 결과")
                    exec(generated_code, {'df': df, 'st': st, 'pd': pd})

                    with st.expander("🤖 AI의 '판단' 과정 및 실행 코드 보기 (검증용)"):
                        st.subheader("🤔 생각의 과정 (AI의 계획서)")
                        st.markdown(thought_process)
                        st.subheader("💻 최종 실행 코드")
                        st.code(generated_code, language='python')

                except Exception as e:
                    st.error(f"코드를 실행하는 중 오류가 발생했습니다: {e}")
else:
    st.warning("데이터를 불러올 수 없습니다. `app.py` 파일의 `SHEET_URL` 변수를 확인해주세요.")

    st.write("---")

    # --- 데이터 검사기 섹션 ---
    st.header("2. 🕵️ 데이터 직접 검사하기 (AI 없음)")
    st.info("AI가 데이터를 잘못 인식하는 것 같다면, 여기서 직접 확인해보세요.")
    try:
        column_to_inspect = st.selectbox("검사할 컬럼을 선택하세요:", df.columns)
        if st.button("🔍 컬럼 내용 검사하기"):
            st.subheader(f"'{column_to_inspect}' 컬럼의 값 종류 및 개수")
            value_counts = df.iloc[:, df.columns.get_loc(column_to_inspect)].value_counts().reset_index()
            value_counts.columns = [column_to_inspect, '개수']
            st.dataframe(value_counts)
            st.success("위 표는 AI를 거치지 않은 100% 정확한 원본 데이터의 통계입니다.")
    except Exception as e:
        st.error(f"검사 중 오류가 발생했습니다: {e}")
