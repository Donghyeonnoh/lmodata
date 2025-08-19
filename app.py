import streamlit as st
import pandas as pd
import google.generativeai as genai
import io
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

def get_data_summary(df):
    """데이터 요약 정보를 생성하는 함수"""
    summary = {
        "총_행수": int(len(df)),
        "총_컬럼수": int(len(df.columns)),
        "컬럼정보": {}
    }
    
    for col in df.columns:
        col_info = {
            "데이터타입": str(df[col].dtype),
            "null값개수": int(df[col].isnull().sum()),
            "고유값개수": int(df[col].nunique())
        }
        
        # 숫자형 컬럼의 경우 통계 정보 추가
        if df[col].dtype in ['int64', 'float64']:
            col_info.update({
                "최솟값": float(df[col].min()) if pd.notna(df[col].min()) else None,
                "최댓값": float(df[col].max()) if pd.notna(df[col].max()) else None,
                "평균값": round(float(df[col].mean()), 2) if pd.notna(df[col].mean()) else None,
                "중앙값": float(df[col].median()) if pd.notna(df[col].median()) else None
            })
        # 문자형 컬럼의 경우 상위 값들 추가
        else:
            top_values = df[col].value_counts().head(3)
            # int64 인덱스를 일반 Python int로 변환
            col_info["상위값들"] = {str(k): int(v) for k, v in top_values.items()}
            
        summary["컬럼정보"][col] = col_info
    
    return summary

def create_enhanced_prompt(question, df_filtered, data_summary):
    """향상된 프롬프트 생성"""
    
    # 실제 데이터를 더 많이 포함
    sample_data = df_filtered.head(10).to_string(index=False) if len(df_filtered) <= 10 else df_filtered.sample(10).to_string(index=False)
    
    prompt = f"""
**중요: 당신은 제공된 실제 데이터만을 사용하여 분석해야 합니다. 외부 지식이나 가상의 데이터를 사용하지 마세요.**

당신은 Python Pandas와 Streamlit 전문 데이터 분석가입니다.
아래 제공된 **실제 데이터**를 기반으로 사용자 질문에 답해주세요.

**[실제 데이터 정보]**
총 행수: {data_summary['총_행수']}행
총 컬럼수: {data_summary['총_컬럼수']}개

**[각 컬럼별 상세 정보]**
{self._format_data_summary_for_prompt(data_summary)}

**[실제 데이터 샘플]**
```
{sample_data}
```

**[분석 지침]**
1. **데이터 확인**: 위에 제공된 실제 데이터만 사용하세요
2. **생각의 과정**: 분석 계획을 단계별로 수립하세요
3. **코드 작성**: 실제 데이터(df)를 사용하는 Python 코드만 작성하세요
4. **결과 출력**: 반드시 st.write(), st.dataframe(), st.metric() 등으로 결과를 화면에 표시하세요

**[사용자 질문]**
"{question}"

**[답변 형식]**
## 생각의 과정
(실제 데이터를 어떻게 분석할지 단계별 계획)

## 최종 실행 코드
```python
# 실제 제공된 데이터(df)만 사용하는 코드
```

**주의사항:**
- df 변수에는 위에 제시된 실제 데이터가 들어있습니다
- 외부 데이터나 가상의 데이터를 사용하지 마세요
- 코드 실행 결과를 반드시 streamlit으로 화면에 출력하세요
"""
    
    return prompt

df_original = load_data(SHEET_URL)
if df_original is not None:
    # --- 데이터 미리보기 추가 ---
    with st.expander("📋 전체 데이터 미리보기 (상위 10개 행)"):
        st.dataframe(df_original.head(10))
        st.info(f"전체 데이터: {len(df_original)}행 × {len(df_original.columns)}열")
    
    # --- 1. 데이터 검색 ---
    st.header("1. 🕵️ 데이터 직접 검색하기")
    st.info("분석하고 싶은 데이터를 필터링해서 정확하게 찾아보세요.")
    
    col1, col2 = st.columns(2)
    with col1:
        filter_column = st.selectbox("필터링할 기준 컬럼을 선택하세요:", df_original.columns)
    
    with col2:
        unique_values = df_original[filter_column].unique()
        selected_value = st.selectbox(f"'{filter_column}' 컬럼에서 어떤 값을 찾을까요?", unique_values)
    
    df_filtered = df_original[df_original[filter_column] == selected_value]
    
    st.subheader(f"🔍 검색 결과: '{filter_column}' = '{selected_value}' ({len(df_filtered)}건)")
    
    if len(df_filtered) > 0:
        st.dataframe(df_filtered)
        
        # 검색된 데이터의 요약 정보 표시
        with st.expander("📊 검색된 데이터 요약 정보"):
            data_summary = get_data_summary(df_filtered)
            try:
                st.json(data_summary)
            except Exception as e:
                st.write("📊 검색된 데이터 정보:")
                st.write(f"- 총 행수: {len(df_filtered)}개")
                st.write(f"- 컬럼: {', '.join(df_filtered.columns)}")
                if len(df_filtered) > 0:
                    st.write("- 데이터 타입:")
                    for col in df_filtered.columns:
                        st.write(f"  • {col}: {df_filtered[col].dtype}")
    else:
        st.warning("검색 결과가 없습니다.")
    
    st.write("---")
    
    # --- 2. AI 분석 ---
    st.header("2. 🤖 검색된 데이터에 대해 AI 질문하기")
    
    if not df_filtered.empty:
        # 질문 예시 제공
        st.info("💡 질문 예시: '평균값은?', '최댓값을 찾아줘', '데이터를 요약해줘', '컬럼별 분포를 보여줘'")
        
        question = st.text_area(
            "검색된 데이터에 대해 궁금한 점을 질문해주세요:", 
            height=100, 
            placeholder="예시: 이 데이터의 평균값과 분포를 분석해줘"
        )
        
        if st.button("🚀 분석 요청하기!", type="primary"):
            if not question:
                st.warning("질문을 입력해주세요!")
            else:
                with st.spinner("🧠 DAVER가 실제 데이터를 분석 중입니다..."):
                    try:
                        # 데이터 요약 정보 생성
                        data_summary = get_data_summary(df_filtered)
                        
                        # 향상된 프롬프트 생성
                        prompt = create_enhanced_prompt(question, df_filtered, data_summary)
                        
                        # AI 모델 호출
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        response = model.generate_content(prompt)
                        response_text = response.text
                        
                        # 응답 파싱
                        thought_process = ""
                        generated_code = ""
                        
                        if "## 최종 실행 코드" in response_text:
                            parts = response_text.split("## 최종 실행 코드")
                            thought_process = parts[0].replace("## 생각의 과정", "").strip()
                            code_part = parts[1]
                            # 코드 블록에서 실제 코드만 추출
                            if "```python" in code_part:
                                code_start = code_part.find("```python") + 9
                                code_end = code_part.find("```", code_start)
                                generated_code = code_part[code_start:code_end].strip()
                            else:
                                generated_code = code_part.strip()
                        else:
                            generated_code = response_text.replace("```python", "").replace("```", "").strip()
                        
                        # 코드 실행
                        st.subheader("📊 분석 결과")
                        
                        # 안전한 실행 환경 구성
                        safe_globals = {
                            'df': df_filtered,
                            'st': st,
                            'pd': pd,
                            '__builtins__': {'len': len, 'str': str, 'int': int, 'float': float, 'round': round}
                        }
                        
                        exec(generated_code, safe_globals)
                        
                        # AI의 분석 과정 표시
                        with st.expander("🤖 AI의 분석 과정 및 코드 보기"):
                            if thought_process:
                                st.subheader("🤔 생각의 과정")
                                st.markdown(thought_process)
                            
                            st.subheader("💻 실행된 코드")
                            st.code(generated_code, language='python')
                            
                            st.subheader("📋 사용된 데이터 정보")
                            try:
                                st.json({
                                    "데이터_행수": int(len(df_filtered)),
                                    "데이터_컬럼": list(df_filtered.columns),
                                    "필터_조건": f"{filter_column} = {selected_value}"
                                })
                            except:
                                st.write({
                                    "데이터_행수": len(df_filtered),
                                    "데이터_컬럼": list(df_filtered.columns),
                                    "필터_조건": f"{filter_column} = {selected_value}"
                                })
                    
                    except Exception as e:
                        st.error(f"❌ 분석 중 오류가 발생했습니다: {str(e)}")
                        
                        with st.expander("🔍 오류 디버깅 정보"):
                            st.error(f"오류 상세: {e}")
                            if 'generated_code' in locals() and generated_code:
                                st.subheader("문제가 된 코드:")
                                st.code(generated_code, language='python')
                            
                            st.subheader("사용 가능한 데이터:")
                            st.dataframe(df_filtered.head())
    else:
        st.info("⬆️ 위에서 데이터를 먼저 검색해주세요.")

else:
    st.warning("❌ 데이터를 불러올 수 없습니다. `SHEET_URL` 변수를 확인해주세요.")
