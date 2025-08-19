import streamlit as st
import pandas as pd
import google.generativeai as genai
import json

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
    .success-box { 
        background-color: #d4edda; border: 1px solid #c3e6cb; 
        border-radius: 5px; padding: 15px; margin: 10px 0;
    }
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

def create_smart_filtering_prompt(question, df_original):
    """스마트 필터링을 위한 프롬프트 생성"""
    
    # 데이터 구조 정보
    columns_info = []
    for col in df_original.columns:
        unique_values = df_original[col].unique()
        if len(unique_values) <= 20:  # 값이 많지 않으면 전체 표시
            columns_info.append(f"{col}: {list(unique_values)}")
        else:  # 값이 많으면 일부만 표시
            sample_values = list(unique_values[:10])
            columns_info.append(f"{col}: {sample_values} ... (총 {len(unique_values)}개 고유값)")
    
    columns_text = "\n".join(columns_info)
    
    prompt = f"""
당신은 데이터 분석 전문가입니다. 사용자의 자연어 질문을 분석해서 pandas 필터링 코드를 생성해주세요.

**[전체 데이터 정보]**
총 행수: {len(df_original)}
컬럼 및 가능한 값들:
{columns_text}

**[데이터 샘플]**
{df_original.head(3).to_string()}

**[사용자 질문]**
"{question}"

**[분석 과정]**
위 질문을 분석해서 다음을 수행하세요:

1. **질문 이해**: 어떤 조건으로 데이터를 필터링해야 하는지 파악
2. **필터링 코드 생성**: pandas 조건문 작성
3. **결과 분석**: 필터링된 데이터의 특징 분석

**[답변 형식]**
## 질문 분석
(질문에서 찾아낸 필터링 조건들을 설명)

## 필터링 및 분석 코드
```python
# 단계별 필터링 수행
filtered_df = df.copy()

# 필터링 조건들 (예시)
# filtered_df = filtered_df[filtered_df['작물'] == '면화']
# filtered_df = filtered_df[filtered_df['주소'].str.contains('충청남도')]

# 결과 출력
st.write(f"🔍 검색 결과: {{len(filtered_df)}}건 발견")
st.write("---")

# 주요 통계
st.metric("총 건수", len(filtered_df))

# 데이터 테이블 표시  
if len(filtered_df) > 0:
    st.subheader("📋 해당 데이터 목록")
    st.dataframe(filtered_df)
    
    # 추가 분석 (필요시)
    # 예: 지역별 분포, 날짜별 분포 등
else:
    st.warning("조건에 맞는 데이터가 없습니다.")
```

**중요사항:**
- df 변수에는 전체 원본 데이터가 들어있습니다
- 반드시 실제 존재하는 컬럼명과 값만 사용하세요
- 문자열 검색시 .str.contains() 활용하세요
- 결과를 streamlit으로 보기 좋게 표시하세요
"""
    
    return prompt

# 세션 상태 초기화
if 'filtered_data' not in st.session_state:
    st.session_state.filtered_data = None
if 'filter_question' not in st.session_state:
    st.session_state.filter_question = ""

df_original = load_data(SHEET_URL)
if df_original is not None:
    # --- 전체 데이터 미리보기 ---
    with st.expander("📋 전체 데이터 미리보기"):
        st.dataframe(df_original.head(10))
        st.info(f"전체 데이터: {len(df_original)}행 × {len(df_original.columns)}열")
    
    # --- 1단계: AI 스마트 검색 ---
    st.header("1. 🤖 AI에게 자연어로 데이터 요청하기")
    st.info("💡 예시: '충남 지역 면화 데이터는 몇 개야?', '경기도 벼 재배 현황 보여줘', '2025년 7월 데이터만 찾아줘'")
    
    question = st.text_area(
        "구글시트 전체 데이터에서 찾고 싶은 것을 자연어로 질문해주세요:", 
        height=100,
        placeholder="예시: 충남 지역 면화가 몇 개인지 알려줘"
    )
    
    if st.button("🔍 AI에게 데이터 검색 요청!", type="primary"):
        if not question:
            st.warning("질문을 입력해주세요!")
        else:
            with st.spinner("🧠 AI가 질문을 분석하고 데이터를 검색 중입니다..."):
                try:
                    # AI 프롬프트 생성 및 호출
                    prompt = create_smart_filtering_prompt(question, df_original)
                    
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    response = model.generate_content(prompt)
                    response_text = response.text
                    
                    # 응답 파싱
                    analysis_text = ""
                    generated_code = ""
                    
                    if "## 필터링 및 분석 코드" in response_text:
                        parts = response_text.split("## 필터링 및 분석 코드")
                        analysis_text = parts[0].replace("## 질문 분석", "").strip()
                        code_part = parts[1]
                        
                        # 코드 추출
                        if "```python" in code_part:
                            code_start = code_part.find("```python") + 9
                            code_end = code_part.find("```", code_start)
                            generated_code = code_part[code_start:code_end].strip()
                        else:
                            generated_code = code_part.strip()
                    
                    # 코드 실행
                    st.subheader("📊 AI 검색 결과")
                    
                    # 안전한 실행 환경
                    safe_globals = {
                        'df': df_original,  # 전체 데이터 제공
                        'st': st,
                        'pd': pd,
                        'len': len,
                        'filtered_df': None,  # 결과 저장용
                        '__builtins__': {'len': len, 'str': str, 'int': int, 'float': float, 'round': round, 'list': list}
                    }
                    
                    # 실행 후 결과 추출을 위한 코드 수정
                    execution_code = generated_code + """

# 필터링된 결과를 세션에 저장
if 'filtered_df' in locals():
    import streamlit as st
    st.session_state.filtered_data = filtered_df
    st.session_state.filter_question = question
"""
                    
                    exec(execution_code, safe_globals)
                    
                    # AI 분석 과정 표시
                    with st.expander("🤖 AI의 질문 분석 과정 및 코드"):
                        if analysis_text:
                            st.subheader("🤔 AI의 질문 분석")
                            st.markdown(analysis_text)
                        
                        st.subheader("💻 실행된 검색 코드")
                        st.code(generated_code, language='python')
                
                except Exception as e:
                    st.error(f"❌ 검색 중 오류가 발생했습니다: {str(e)}")
                    with st.expander("🔍 오류 정보"):
                        st.error(f"오류 상세: {e}")
                        if 'generated_code' in locals():
                            st.code(generated_code, language='python')
    
    st.write("---")
    
    # --- 2단계: 필터링된 데이터 상세 분석 ---
    st.header("2. 📊 검색된 데이터 상세 분석하기")
    
    if st.session_state.filtered_data is not None and len(st.session_state.filtered_data) > 0:
        filtered_df = st.session_state.filtered_data
        
        st.success(f"✅ 이전 검색 결과: '{st.session_state.filter_question}'로 찾은 {len(filtered_df)}건의 데이터")
        
        # 검색된 데이터 요약
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("총 데이터 수", len(filtered_df))
        with col2:
            st.metric("컬럼 수", len(filtered_df.columns))
        with col3:
            if len(filtered_df) > 0:
                st.metric("데이터 기간", f"{len(pd.to_datetime(filtered_df.iloc[:,1], errors='coerce').dt.date.unique())}일" if len(filtered_df.columns) > 1 else "N/A")
        
        # 상세 분석 질문
        detail_question = st.text_area(
            "위 검색된 데이터에 대해 더 자세히 알고 싶은 것을 질문해주세요:",
            height=100,
            placeholder="예시: 이 데이터의 지역별 분포는? 월별 트렌드는? 평균값은?"
        )
        
        if st.button("📈 상세 분석 시작!", type="secondary"):
            if not detail_question:
                st.warning("상세 분석 질문을 입력해주세요!")
            else:
                with st.spinner("🔬 상세 분석 중입니다..."):
                    try:
                        # 상세 분석용 프롬프트
                        detail_prompt = f"""
당신은 데이터 분석 전문가입니다. 이미 필터링된 데이터에 대해 상세 분석을 수행해주세요.

**[필터링된 데이터 정보]**
- 총 행수: {len(filtered_df)}
- 컬럼: {list(filtered_df.columns)}
- 이전 검색 조건: "{st.session_state.filter_question}"

**[필터링된 데이터 샘플]**
{filtered_df.head(5).to_string()}

**[사용자 상세 질문]**
"{detail_question}"

**[분석 지침]**
위 필터링된 데이터(df)만을 사용해서 상세 분석을 수행하세요.

**[답변 형식]**
## 분석 계획
(어떤 분석을 할지 계획)

## 상세 분석 코드
```python
# 필터링된 데이터 확인
st.write("🔍 분석 대상 데이터:")
st.write(f"총 {len(df)}건의 데이터")

# 상세 분석 수행
# 예: 그룹별 집계, 통계 분석, 시각화 등

# 결과를 명확하게 표시
st.subheader("📊 분석 결과")
# 분석 결과 출력 코드
```

**주의사항:**
- df에는 이미 필터링된 데이터만 들어있습니다
- 시각화가 필요하면 st.bar_chart, st.line_chart 등을 활용하세요
- 결과를 보기 좋게 정리해서 표시하세요
"""
                        
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(detail_prompt)
                        response_text = response.text
                        
                        # 코드 추출 및 실행
                        if "```python" in response_text:
                            code_start = response_text.find("```python") + 9
                            code_end = response_text.find("```", code_start)
                            analysis_code = response_text[code_start:code_end].strip()
                        else:
                            analysis_code = response_text.strip()
                        
                        st.subheader("🔬 상세 분석 결과")
                        
                        # 안전한 실행 환경
                        safe_globals = {
                            'df': filtered_df,  # 필터링된 데이터만 제공
                            'st': st,
                            'pd': pd,
                            'len': len,
                            '__builtins__': {'len': len, 'str': str, 'int': int, 'float': float, 'round': round, 'list': list}
                        }
                        
                        exec(analysis_code, safe_globals)
                        
                        # 분석 과정 표시
                        with st.expander("🤖 상세 분석 과정"):
                            st.code(analysis_code, language='python')
                    
                    except Exception as e:
                        st.error(f"❌ 상세 분석 중 오류: {str(e)}")
        
        # 검색된 원본 데이터 표시
        with st.expander("📋 검색된 원본 데이터 전체보기"):
            st.dataframe(filtered_df)
    
    else:
        st.info("⬆️ 먼저 1단계에서 AI에게 데이터 검색을 요청해주세요.")

else:
    st.warning("❌ 데이터를 불러올 수 없습니다.")
