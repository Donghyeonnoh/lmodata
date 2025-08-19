import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 페이지 초기 설정 (가장 먼저 실행되어야 함) ---
st.set_page_config(
    page_title="DAVER",
    page_icon="💻",
    layout="centered",
)

# --- 타임스탬프 로딩 함수 ---
@st.cache_data(ttl=60)
def load_timestamp(url):
    try:
        gid = "1373493684"
        csv_url = url.replace("/edit?usp=sharing", f"/export?format=csv&gid={gid}")
        timestamp_df = pd.read_csv(csv_url, header=None)
        return timestamp_df.iloc[0, 0]
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

if not check_password():
    st.stop()

# --- 제목 및 스타일 ---
st.markdown(
    """
    <style>
    .title-container {
        background-color: #03C75A; padding: 20px 20px 10px 20px; border-radius: 10px;
        color: white; text-align: center; margin-bottom: 20px;
    }
    .title-font { font-size: 32px; font-weight: bold; }
    .subtitle-font { font-size: 16px; }
    
    @media (max-width: 600px) {
        .title-font {
            font-size: 24px;
        }
    }
    </style>
    <div class="title-container">
        <p class="title-font">DAVER 💻</p>
        <p class="subtitle-font">LMO팀 데이터 분석 비서</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- API Key 설정 & 데이터 로딩 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("앗! Gemini API Key를 설정하지 않으셨군요.")
    st.stop()

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

# --- 데이터가 있을 경우 앱 본문 표시 ---
if df_original is not None:
    # --- 사이드바 필터 ---
    with st.sidebar:
        st.title("🕵️ 데이터 검색 필터")
        st.info("아래 필터로 데이터를 검색하세요.")
        if '권역' in df_original.columns:
            unique_regions = ['--전체--'] + sorted(list(df_original['권역'].unique()))
            selected_region = st.selectbox("권역:", unique_regions, key="region")
        else:
            selected_region = '--전체--'
        if '작물' in df_original.columns:
            unique_crops = ['--전체--'] + sorted(list(df_original['작물'].unique()))
            selected_crop = st.selectbox("작물:", unique_crops, key="crop")
        else:
            selected_crop = '--전체--'
        if 'Strip결과' in df_original.columns:
            unique_results = ['--전체--'] + sorted(list(df_original['Strip결과'].unique()))
            selected_result = st.selectbox("Strip결과:", unique_results, key="result")
        else:
            selected_result = '--전체--'
        st.markdown("---")
        last_updated = load_timestamp(SHEET_URL)
        st.success(f"**데이터 상태**\n\n{last_updated}")

    # --- 데이터 필터링 로직 ---
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

    # --- 메인 화면 ---
    if filter_summary:
        st.subheader(f"🔍 검색 결과 ({' & '.join(filter_summary)})")
    else:
        st.subheader("🔍 전체 데이터")
    st.dataframe(df_filtered)
    st.success(f"총 {len(df_filtered)}건의 데이터가 검색되었습니다.")

    # --- AI 요약 기능 ---
    if not df_filtered.empty:
        st.write("---")
        st.header("🤖 위 검색 결과 한 줄 요약 (AI)")
        if st.button("✨ AI에게 요약 요청하기", type="primary"):
            ### ★★★ 여기를 다시 원래 코드로 복구했어요! ★★★ ###
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
else:
    st.warning("데이터를 불러올 수 없습니다.")
