import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- [찐막 핵심 1] 타임스탬프를 읽어오는 새로운 함수 ---
@st.cache_data(ttl=60) # 타임스탬프는 1분마다 새로고침
def load_timestamp(url):
    try:
        # MetaData 시트를 읽기 위한 URL 생성
        # [사용자 수정 필요!] 아래 YOUR_METADATA_SHEET_GID 부분을 실제 GID 숫자로 바꿔주세요.
        gid = "        gid = "1373493684" 
        csv_url = url.replace("/edit?usp=sharing", f"/export?format=csv&gid={gid}")
        timestamp_df = pd.read_csv(csv_url, header=None)
        return timestamp_df.iloc[0, 0] # 첫 번째 행, 첫 번째 열의 값을 반환
    except Exception:
        return "업데이트 시간 확인 불가"

# --- 비밀번호 확인 기능 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    with st.form("password_form"):
        password = st.text_input("비밀번호를 입력하세요", type="password")
        submitted = st.form_submit_button("확인")

        if submitted:
            if password == st.secrets["password"]:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
    return False

# 비밀번호가 맞지 않으면, 아래의 앱 본체는 실행되지 않음
if not check_password():
    st.stop()

# --- 1. 페이지 초기 설정 (비밀번호 통과 후 실행) ---
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
    # --- [찐막 핵심 2] 타임스탬프 화면에 표시하기 ---
    last_updated = load_timestamp(SHEET_URL)
    st.info(f"**데이터베이스 상태:** {last_updated}")

    st.header("1. 🕵️ 데이터 직접 검색하기 (3중 필터링)")
    st.info("세 가지 필터 조건을 조합하여 원하는 데이터를 정확하게 찾아보세요.")

    # --- 4. 3중 필터링 인터페이스 ---
    try:
        cols = st.columns(3)

        with cols[0]:
            st.subheader("필터 1: 권역")
            if '권역' in df_original.columns:
                unique_regions = ['--전체--'] + sorted(list(df_original['권역'].unique()))
                selected_region = st.selectbox("권역을 선택하세요:", unique_regions, key="region")
            else:
                st.warning("'권역' 컬럼을 찾을 수 없습니다. 구글 시트를 확인해주세요.")
                selected_region = '--전체--'

        with cols[1]:
            st.subheader("필터 2: 작물")
            if '작물' in df_original.columns:
                unique_crops = ['--전체--'] + sorted(list(df_original['작물'].unique()))
                selected_crop = st.selectbox("작물을 선택하세요:", unique_crops, key="crop")
            else:
                st.warning("'작물' 컬럼을 찾을 수 없습니다.")
                selected_crop = '--전체--'
        
        with cols[2]:
            st.subheader("필터 3: Strip결과")
            if 'Strip결과' in df_original.columns:
                unique_results = ['--전체--'] + sorted(list(df_original['Strip결과'].unique()))
                selected_result = st.selectbox("Strip결과를 선택하세요:", unique_results, key="result")
            else:
                st.warning("'Strip결과' 컬럼을 찾을 수 없습니다.")
                selected_result = '--전체--'

        df_filtered = df_original.copy()
        filter_summary = []

        if selected_region != '--전체--' and '권역' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['권역'] == selected_region]
            filter_summary.append(f"권역='{selected_region}'")
            
        if selected_crop != '--전체--' and '작물' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['작물'] == selected_crop]
            filter_summary.append(f"작물='{selected_crop}'")

        if selected_result != '--전체--' and 'Strip결과' in df_filtered.columns:
            df_filtered = df_filtered[df_filtered['Strip결과'] == selected_result]
            filter_summary.append(f"Strip결과='{selected_result}'")
        
        st.write("---")
        if filter_summary:
            st.subheader(f"🔍 검색 결과 ({' & '.join(filter_summary)})")
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
                        - 분석 조건: {' & '.join(filter_summary) if filter_summary else "전체 데이터"}
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
