import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="부동산 지수 4분면 분석",
    page_icon="",
    layout="wide"
)

@st.cache_data
def load_data(file_path):
    try:
        sale = pd.read_excel(file_path, sheet_name="3.매매지수", skiprows=[0, 2, 3])
        rent = pd.read_excel(file_path, sheet_name="4.전세지수", skiprows=[0, 2, 3])
    except Exception as e:
        st.error(f"오류 발생: {e}")
        st.stop()

    sale = sale.dropna(subset=['구분'])
    sale[:] = sale[:].fillna(0).infer_objects(copy=False)
    rent[:] = rent[:].fillna(0).infer_objects(copy=False)

    sale.rename(columns={'구분': '날짜'}, inplace=True)
    rent.rename(columns={'구분': '날짜'}, inplace=True)

    sale_melt = sale.melt(id_vars=['날짜'], var_name='지역', value_name='매매지수')
    rent_melt = rent.melt(id_vars=['날짜'], var_name='지역', value_name='전세지수')

    df = pd.merge(sale_melt, rent_melt, on=['날짜', '지역'])
    df['날짜'] = pd.to_datetime(df['날짜'])
    return df
    
@st.cache_data
def load_change_data(file_path):
    try:
        # 증감 시트는 보통 '매매증감', '전세증감'으로 명명됨 (시트명 확인 필요)
        sale_chg = pd.read_excel(file_path, sheet_name="1.매매증감", skiprows=[0, 2, 3])
        rent_chg = pd.read_excel(file_path, sheet_name="2.전세증감", skiprows=[0, 2, 3])
    except Exception as e:
        st.error(f"증감 데이터 로드 오류: {e}")
        return None

    sale_chg = sale_chg.dropna(subset=['구분']).fillna(0).infer_objects(copy=False)
    rent_chg = rent_chg.dropna(subset=['구분']).fillna(0).infer_objects(copy=False)

    sale_chg.rename(columns={'구분': '날짜'}, inplace=True)
    rent_chg.rename(columns={'구분': '날짜'}, inplace=True)

    s_melt = sale_chg.melt(id_vars=['날짜'], var_name='지역', value_name='매매증감')
    r_melt = rent_chg.melt(id_vars=['날짜'], var_name='지역', value_name='전세증감')

    df_chg = pd.merge(s_melt, r_melt, on=['날짜', '지역'])
    df_chg['날짜'] = pd.to_datetime(df_chg['날짜'])
    return df_chg

file_path = "주간시계열.xlsx"
logo_image_path = "jak_logo.png"
df = load_data(file_path)

df_chg = load_change_data(file_path)

# --- 사이드바 ---
st.sidebar.header("🗓️ 필터")
selected_dates = st.sidebar.date_input(
    "날짜 범위",
    value=(df["날짜"].min(), df["날짜"].max()),
    min_value=df["날짜"].min(),
    max_value=df["날짜"].max(),
)

if len(selected_dates) != 2:
    st.sidebar.error("날짜 범위를 선택하세요.")
    st.stop()
start_date, end_date = selected_dates

all_regions = df["지역"].unique()
selected_regions = st.sidebar.multiselect("지역 선택", options=all_regions, default=all_regions[:3])

st.sidebar.header("🎨 색상")
color_map = {reg: st.sidebar.color_picker(f"{reg}", px.colors.qualitative.Plotly[i%10]) 
             for i, reg in enumerate(selected_regions)}

# --- 메인 화면 ---
col1, col2 = st.columns([1, 8]) 

with col1:
    try:
        st.image(logo_image_path, use_container_width=True) 
    except Exception as e:
        st.write("🖼️ LOGO")

with col2:
    st.title("작부동산 매전지수 4분면")

# --- 데이터 필터링 ---
mask = (df["날짜"] >= pd.to_datetime(start_date)) & \
       (df["날짜"] <= pd.to_datetime(end_date)) & \
       (df["지역"].isin(selected_regions))
df_sel = df[mask].sort_values(['지역', '날짜'])

if df_sel.empty:
    st.warning("데이터가 없습니다.")
else:
    fig = go.Figure()

    for region in selected_regions:
        rdf = df_sel[df_sel['지역'] == region]
        if rdf.empty: continue
        
        reg_color = color_map.get(region, "black")

        # 1. 경로 선 추가
        fig.add_trace(go.Scatter(
            x=rdf['매매지수'], y=rdf['전세지수'],
            mode='lines+markers',
            name=region,
            line=dict(color=reg_color, width=2),
            marker=dict(size=4, opacity=0.5),
            hoverinfo='text',
            text=[f"{region}<br>{d.strftime('%Y-%m-%d')}<br>매매:{s}<br>전세:{r}" 
                  for d, s, r in zip(rdf['날짜'], rdf['매매지수'], rdf['전세지수'])]
        ))
        
        # 3. 최신 지점(현재) 강조 레이블
        last = rdf.iloc[-1]
        fig.add_annotation(
            x=last['매매지수'], y=last['전세지수'],
            text=f"<b>{region} (최근)</b>",
            showarrow=False, yshift=15,
            font=dict(color="white", size=11),
            bgcolor=reg_color, borderpad=4, opacity=1
        )

        # 5. 종료 지점(가장 최근 날짜) 표시
        last = rdf.iloc[-1]
        fig.add_trace(go.Scatter(
            x=[last['매매지수']], y=[last['전세지수']],
            mode='markers+text',
            text=["recent"], 
            textposition="top center", 
            marker=dict(color=reg_color, size=10, symbol="circle"), 
            showlegend=False
        ))

        first = rdf.iloc[0]
        fig.add_trace(go.Scatter(
            x=[first['매매지수']], y=[first['전세지수']],
            mode='markers+text',
            text=["START"], textposition="bottom center",
            marker=dict(color="grey", size=8, symbol="circle"),
            showlegend=False
        ))

    
    fig.update_layout(
        title=f"부동산 지수 경로 분석 ({start_date} ~ {end_date})",
        xaxis_title="매매지수", yaxis_title="전세지수",
        template="plotly_white",
        height=700,
        hovermode="closest"
    )

    st.plotly_chart(fig, use_container_width=True)
st.divider() 

mask_chg = (df_chg["날짜"] >= pd.to_datetime(start_date)) & \
           (df_chg["날짜"] <= pd.to_datetime(end_date)) & \
           (df_chg["지역"].isin(selected_regions))
df_chg_sel = df_chg[mask_chg].sort_values(['지역', '날짜'])

if df_chg_sel.empty:
    st.warning("증감 데이터가 없습니다.")
else:
    fig2 = go.Figure()

    for region in selected_regions:
        rdf = df_chg_sel[df_chg_sel['지역'] == region]
        if rdf.empty: continue
        
        reg_color = color_map.get(region, "black")

        # 경로 선
        fig2.add_trace(go.Scatter(
            x=rdf['매매증감'], y=rdf['전세증감'],
            mode='lines+markers',
            name=region,
            line=dict(color=reg_color, width=2),
            marker=dict(size=8, opacity=1),
            hoverinfo='text',
            text=[f"{region}<br>{d.strftime('%Y-%m-%d')}<br>매매증감:{s}%<br>전세증감:{r}%" 
                  for d, s, r in zip(rdf['날짜'], rdf['매매증감'], rdf['전세증감'])]
        ))

        # 최신 지점 강조 (사각형 레이블)
        last = rdf.iloc[-1]
        fig2.add_annotation(
            x=last['매매증감'], y=last['전세증감'],
            text=f"<b>{region} (최근)</b>",
            showarrow=False, yshift=15,
            font=dict(color="white", size=11),
            bgcolor=reg_color, borderpad=4
        )

    # 증감률 그래프 특화 레이아웃 (0점 기준 십자선 추가)
    fig2.update_layout(
        title=f"매매/전세 증감률 경로 ({start_date} ~ {end_date})",
        xaxis_title="매매증감률 (%)", yaxis_title="전세증감률 (%)",
        template="plotly_white",
        height=700,
        hovermode="closest"
    )
    
    fig2.add_vline(x=0, line_width=1, line_dash="dash", line_color="gray")
    fig2.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")

    st.plotly_chart(fig2, use_container_width=True)


