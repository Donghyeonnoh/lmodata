import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- 페이지 초기 설정 (가장 먼저 실행되어야 함) ---
### 변경점 1: layout을 'centered'로 변경하여 모바일 가독성 확보 ###
st.set_page_config(
    page_title="DAVER",
    page_icon="💻",
    layout="centered", # wide -> centered
)

# --- [찐막 핵심 1] 타임스탬프를 읽어오는 새로운 함수 ---
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

# --- 제목 및 스타일 (비밀번호 통과 후 실행) ---
### 변경점 2: 모바일 화면(폭 600px 이하)에서 제목 폰트 크기 조정 ###
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
        <p class="title-font">DAVER 📊</p>
        <p class="subtitle-font">우리 팀을 위한 데이터 분석 비서</p>
    </div>
    """,
    unsafe_allow_html=True
)

# --- API Key 설정 & 데이터 로딩 (기존과 동일) ---
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
    ### 변경점 3: 3단 필터를 사이드바로 이동 ###
    with st.sidebar:
        st.title("🕵️ 데이터 검색 필터")
        st.info("아래 필터로 데이터를 검색하세요.")

        # 필터 1: 권역
        if '권역' in df_original.columns:
            unique_regions = ['--전체--'] + sorted(list(df_original['권역'].unique()))
            selected_region = st.selectbox("권역:", unique_regions, key="region")
        else:
            st.warning("'권역' 컬럼 없음")
            selected_region = '--전체--'

        # 필터 2: 작물
        if '작물' in df_original.columns:
            unique_crops = ['--전체--'] + sorted(list(df_original['작물'].unique()))
            selected_crop = st.selectbox("작물:", unique_crops, key="crop")
        else:
            st.warning("'작물' 컬럼 없음")
            selected_crop = '--전체--'
        
        # 필터 3: Strip결과
        if 'Strip결과' in df_original.columns:
            unique_results = ['--전체--'] + sorted(list(df_original['Strip결과'].unique()))
            selected_result = st.selectbox("Strip결과:", unique_results, key="result")
        else:
            st.warning("'Strip결과' 컬럼 없음")
            selected_result = '--전체--'
        
        st.markdown("---")
        last_updated = load_timestamp(SHEET_URL)
        st.success(f"**데이터 상태**\n\n{last_updated}")


    # --- 메인 화면 구성 ---
    df_filtered = df_original.copy()
    filter_summary = []

    if selected_region != '--전체--':
        df_filtered = df_filtered[df_filtered['권역'] == selected_region]
        filter_summary.append(f"권역='{selected_region}'")
        
    if selected_crop != '--전체--':
        df_filtered = df_filtered[df_filtered['작물'] == selected_crop]
        filter_summary.append(f"작물='{selected_crop}'")

    if selected_result != '--전체--':
        df_filtered = df_filtered[df_filtered['Strip결과'] == selected_result]
        filter_summary.append(f"Strip결과='{selected_result}'")
    
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
            # (AI 요약 기능 코드는 기존과 동일하여 생략)
            pass
else:
    st.warning("데이터를 불러올 수 없습니다.")
