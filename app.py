import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="부동산 지수 사분면 분석",
    page_icon="asdfasdfasf",
    layout="wide"
)

@st.cache_data
def load_data(file_path):
    try:
        # 엑셀 로드
        sale = pd.read_excel(file_path, sheet_name="3.매매지수", skiprows=[0, 2, 3])
        rent = pd.read_excel(file_path, sheet_name="4.전세지수", skiprows=[0, 2, 3])
    except Exception as e:
        st.error(f"오류 발생: {e}")
        st.stop()

    # '구분' 열(날짜)이 비어있는 행 제거
    sale = sale.dropna(subset=['구분'])
    rent = rent.dropna(subset=['구분'])

    # 날짜를 제외한 나머지 수치 데이터의 결측치만 0으로 채움
    sale.iloc[:, 1:] = sale.iloc[:, 1:].fillna(0)
    rent.iloc[:, 1:] = rent.iloc[:, 1:].fillna(0)

    # 이름 변경
    sale.rename(columns={'구분': '날짜'}, inplace=True)
    rent.rename(columns={'구분': '날짜'}, inplace=True)

    # Wide to Long 변환
    sale_melt = sale.melt(id_vars=['날짜'], var_name='지역', value_name='매매지수')
    rent_melt = rent.melt(id_vars=['날짜'], var_name='지역', value_name='전세지수')

    # 병합 및 날짜 형식 강제 변환 (에러 방지용 errors='coerce')
    df = pd.merge(sale_melt, rent_melt, on=['날짜', '지역'])
    df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
    df = df.dropna(subset=['날짜']) # 변환 실패한 행 제거
    
    return df
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
@st.cache_data
def load_change_data(file_path):
    try:
        sale_chg = pd.read_excel(file_path, sheet_name="1.매매증감", skiprows=[0, 2, 3])
        rent_chg = pd.read_excel(file_path, sheet_name="2.전세증감", skiprows=[0, 2, 3])
    except Exception as e:
        st.error(f"증감 데이터 로드 오류: {e}")
        return None

    sale_chg = sale_chg.dropna(subset=['구분'])
    rent_chg = rent_chg.dropna(subset=['구분'])

    # 수치 데이터만 0으로 채우기
    sale_chg.iloc[:, 1:] = sale_chg.iloc[:, 1:].fillna(0)
    rent_chg.iloc[:, 1:] = rent_chg.iloc[:, 1:].fillna(0)

    sale_chg.rename(columns={'구분': '날짜'}, inplace=True)
    rent_chg.rename(columns={'구분': '날짜'}, inplace=True)

    s_melt = sale_chg.melt(id_vars=['날짜'], var_name='지역', value_name='매매증감')
    r_melt = rent_chg.melt(id_vars=['날짜'], var_name='지역', value_name='전세증감')

    df_chg = pd.merge(s_melt, r_melt, on=['날짜', '지역'])
    df_chg['날짜'] = pd.to_datetime(df_chg['날짜'], errors='coerce')
    df_chg = df_chg.dropna(subset=['날짜'])
    
    return df_chg
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

file_path = "kb.xlsx"
logo_image_path = "jak_logo.png"
df = load_data(file_path)

# 데이터 로드 실행++++++++++++++++++++++++++++++++++++++++  
df_chg = load_change_data(file_path)
#++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

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

col1, col2 = st.columns([1, 8]) 

with col1:
    try:
        st.image(logo_image_path, use_container_width=True) 
    except Exception as e:
        st.write("🖼️ LOGO")

with col2:
    st.title("작부동산 매전지수 사분면")

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
        
        last = rdf.iloc[-1]
        fig.add_annotation(
            x=last['매매지수'], y=last['전세지수'],
            text=f"<b>{region} (최근)</b>",
            showarrow=False, yshift=15,
            font=dict(color="white", size=11),
            bgcolor=reg_color, borderpad=4, opacity=1
        )

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
        title=f"jak 작부동산 지수 경로 분석 ({start_date} ~ {end_date})",
        xaxis_title="매매지수", yaxis_title="전세지수",
        template="plotly_white",
        height=700,
        hovermode="closest"
    )

    st.plotly_chart(fig, use_container_width=True)

# ======가속도 추가부분 시작=======


# ================================================================
# 매매/전세 증감률 가속도 사분면 분석
#   X축 : 해당 주의 증감률
#   Y축 : 가속도 = 해당 주 증감률 - 직전 주 증감률
#   1사분면 : 상승가속
#   2사분면 : 하락반등
#   3사분면 : 하락가속
#   4사분면 : 상승둔화
# ================================================================

def make_acceleration_data(df_index, value_col, accel_col):
    """
    지수 Raw Data(3.매매지수/4.전세지수)에서
    주간 증감률과 가속도(증감률의 전주 대비 변화)를 계산한다.

    주간 변동 = 현주 지수 - 전주 지수
    가속도 = 현주 변동 - 전주 변동
    """
    data = df_index.copy().sort_values(['지역', '날짜']).copy()

    prev_index = data.groupby('지역')[value_col].shift(1)
    prev_change = (data[value_col] - prev_index)

    data['증감률계산'] = prev_change
    data[accel_col] = prev_change - prev_change.groupby(data['지역']).shift(1)

    # 첫 주는 전주 지수가 없고, 두 번째 주는 가속도 계산에 전전주가 없으므로 제외
    data = data.dropna(subset=['증감률계산', accel_col]).copy()
    data[value_col + '_변동'] = data['증감률계산']
    return data


def add_quadrant_columns(data, value_col, accel_col):
    data = data.copy()

    def classify(row):
        x = row[value_col]
        y = row[accel_col]

        if x >= 0 and y >= 0:
            return '상승가속'
        elif x < 0 and y >= 0:
            return '하락반등'
        elif x < 0 and y < 0:
            return '하락가속'
        else:
            return '상승둔화'

    data['사분면'] = data.apply(classify, axis=1)
    return data


def draw_acceleration_quadrant(data, value_col, accel_col, title, region_color_map):
    """가속도 사분면을 그리고 Plotly 애니메이션으로 시간 흐름을 재생한다."""
    data = data[
        (data['날짜'] >= pd.to_datetime(start_date)) &
        (data['날짜'] <= pd.to_datetime(end_date)) &
        (data['지역'].isin(selected_regions))
    ].copy()

    if data.empty:
        st.info(f'{title} 데이터가 없습니다.')
        return

    x_col = '증감률계산'
    data = add_quadrant_columns(data, x_col, accel_col)
    data = data.sort_values(['날짜', '지역'])

    quadrant_colors = {
        '상승가속': '#EF553B',
        '상승둔화': '#FFA15A',
        '하락반등': '#00CC96',
        '하락가속': '#636EFA'
    }

    # 전체 축 범위는 애니메이션 중에도 고정한다.
    x_min, x_max = data[x_col].min(), data[x_col].max()
    y_min, y_max = data[accel_col].min(), data[accel_col].max()
    x_abs = max(abs(x_min), abs(x_max), 0.0001) * 1.18
    y_abs = max(abs(y_min), abs(y_max), 0.0001) * 1.18

    dates = sorted(data['날짜'].dropna().unique())

    # 가속도 그래프 내부에서 별도로 움직일 수 있는 시작/끝 구간.
    # 실제 컨트롤은 그래프 아래에 표시하고, 값은 session_state로 유지한다.
    range_key = f'acc_range_v2_{value_col}'
    default_range = (pd.Timestamp(dates[0]).date(), pd.Timestamp(dates[-1]).date())
    saved_range = st.session_state.get(range_key, default_range)
    try:
        saved_range = (pd.Timestamp(saved_range[0]).date(), pd.Timestamp(saved_range[1]).date())
    except Exception:
        saved_range = default_range
    # 상위 날짜 필터가 바뀌면 기존 두 핸들을 새 범위 안으로 보정한다.
    saved_range = (
        max(saved_range[0], default_range[0]),
        min(saved_range[1], default_range[1])
    )
    if saved_range[0] > saved_range[1]:
        saved_range = default_range
    st.session_state[range_key] = saved_range

    acc_start = pd.to_datetime(saved_range[0])
    acc_end = pd.to_datetime(saved_range[1])

    # 선택된 구간에 맞춰 애니메이션 프레임도 시작~끝으로 제한한다.
    dates = [d for d in dates if pd.Timestamp(d) >= acc_start and pd.Timestamp(d) <= acc_end]
    if not dates:
        st.info(f'{title} 선택 구간에 데이터가 없습니다.')
        return

    # 지역별 데이터 준비
    region_data = {}
    for region in selected_regions:
        rdf = data[(data['지역'] == region) &
                   (data['날짜'] >= acc_start) &
                   (data['날짜'] <= acc_end)].sort_values('날짜').copy()
        if not rdf.empty:
            region_data[region] = rdf

    if not region_data:
        st.info(f'{title} 데이터가 없습니다.')
        return

    fig_acc = go.Figure()

    # ------------------------------------------------------------------
    # 기본 프레임: 시작일의 상태
    # 각 지역당
    #   1) 경로 + 점 (지역 범례 담당)
    #   2) START
    #   3) 현재 끝점 + 지역명
    # 의 3개 trace를 만든다.
    # ------------------------------------------------------------------
    for region in selected_regions:
        rdf = region_data.get(region)
        if rdf is None:
            continue

        reg_color = region_color_map.get(region, '#333333')
        initial = rdf[rdf['날짜'] <= dates[0]].copy()
        if initial.empty:
            initial = rdf.iloc[[0]].copy()

        marker_colors = [quadrant_colors[q] for q in initial['사분면']]

        # 지역 경로 + 점: 지역 범례에서 이 trace를 켜고 끄면
        # 같은 legendgroup의 START/끝점도 함께 표시/숨김된다.
        fig_acc.add_trace(go.Scatter(
            x=initial[x_col],
            y=initial[accel_col],
            mode='lines+markers',
            name=region,
            legendgroup=region,
            line=dict(color=reg_color, width=2),
            marker=dict(color=marker_colors, size=6, opacity=0.82),
            customdata=initial[['지역', '날짜', x_col, accel_col]].to_numpy(),
            hovertemplate=(
                '<b>%{customdata[0]}</b><br>'
                '날짜: %{customdata[1]}<br>'
                '증감률: %{customdata[2]:.4f}<br>'
                '가속도: %{customdata[3]:.4f}<extra></extra>'
            ),
            showlegend=True
        ))

        first = rdf.iloc[0]
        fig_acc.add_trace(go.Scatter(
            x=[first[x_col]],
            y=[first[accel_col]],
            mode='text',
            text=['START'],
            textposition='bottom center',
            textfont=dict(size=9, color='#555555'),
            legendgroup=region,
            showlegend=False,
            hoverinfo='skip'
        ))

        last = initial.iloc[-1]
        fig_acc.add_trace(go.Scatter(
            x=[last[x_col]],
            y=[last[accel_col]],
            mode='markers+text',
            text=[region],
            textposition='top center',
            textfont=dict(size=10),
            marker=dict(color=reg_color, size=10),
            legendgroup=region,
            showlegend=False,
            hovertemplate=(
                f'<b>{region}</b><br>'
                '날짜: %{x}<br>'
                '증감률: %{y:.4f}<extra></extra>'
            )
        ))

    # ------------------------------------------------------------------
    # 사분면 배경
    # ------------------------------------------------------------------
    rects = [
        (0, x_abs, 0, y_abs, 'rgba(239,85,59,0.10)'),
        (-x_abs, 0, 0, y_abs, 'rgba(0,204,150,0.10)'),
        (-x_abs, 0, -y_abs, 0, 'rgba(99,110,250,0.10)'),
        (0, x_abs, -y_abs, 0, 'rgba(255,161,90,0.10)')
    ]
    for x0, x1, y0, y1, fill in rects:
        fig_acc.add_shape(
            type='rect', x0=x0, x1=x1, y0=y0, y1=y1,
            fillcolor=fill, line_width=0, layer='below'
        )

    fig_acc.add_hline(y=0, line_width=1, line_color='#999999')
    fig_acc.add_vline(x=0, line_width=1, line_color='#999999')

    # 사분면 명칭
    fig_acc.add_annotation(x=x_abs * 0.68, y=y_abs * 0.87,
                           text='<b>상승가속</b>', showarrow=False)
    fig_acc.add_annotation(x=-x_abs * 0.68, y=y_abs * 0.87,
                           text='<b>하락반등</b>', showarrow=False)
    fig_acc.add_annotation(x=-x_abs * 0.68, y=-y_abs * 0.87,
                           text='<b>하락가속</b>', showarrow=False)
    fig_acc.add_annotation(x=x_abs * 0.68, y=-y_abs * 0.87,
                           text='<b>상승둔화</b>', showarrow=False)

    # ------------------------------------------------------------------
    # 애니메이션 프레임
    # 날짜별로 START는 고정하고, 경로와 현재 끝점을 해당 날짜까지 이동시킨다.
    # ------------------------------------------------------------------
    frames = []
    for frame_date in dates:
        frame_traces = []

        for region in selected_regions:
            rdf = region_data.get(region)
            if rdf is None:
                continue

            visible = rdf[rdf['날짜'] <= frame_date].copy()
            if visible.empty:
                visible = rdf.iloc[[0]].copy()

            marker_colors = [quadrant_colors[q] for q in visible['사분면']]
            reg_color = region_color_map.get(region, '#333333')

            # 1. 현재까지의 경로
            frame_traces.append(go.Scatter(
                x=visible[x_col].tolist(),
                y=visible[accel_col].tolist(),
                marker=dict(color=marker_colors),
                customdata=visible[['지역', '날짜', x_col, accel_col]].to_numpy()
            ))

            # 2. START는 고정
            first = rdf.iloc[0]
            frame_traces.append(go.Scatter(
                x=[first[x_col]], y=[first[accel_col]],
                text=['START']
            ))

            # 3. 현재 끝점 + 지역명
            last = visible.iloc[-1]
            frame_traces.append(go.Scatter(
                x=[last[x_col]], y=[last[accel_col]],
                text=[region],
                marker=dict(color=reg_color)
            ))

        frames.append(go.Frame(
            name=pd.Timestamp(frame_date).strftime('%Y-%m-%d'),
            data=frame_traces
        ))

    fig_acc.frames = frames

    # 기본 화면은 "애니메이션이 모두 완료된 상태"로 표시한다.
    # 즉, 선택된 시작일~끝일까지의 전체 경로와 끝점을 처음부터 보여준다.
    # 재생 버튼을 누르면 첫 프레임(START)부터 끝 프레임까지 다시 재생한다.
    if frames:
        final_frame = frames[-1]
        for trace, frame_trace in zip(fig_acc.data, final_frame.data):
            if hasattr(frame_trace, 'x') and frame_trace.x is not None:
                trace.x = frame_trace.x
            if hasattr(frame_trace, 'y') and frame_trace.y is not None:
                trace.y = frame_trace.y
            if hasattr(frame_trace, 'text') and frame_trace.text is not None:
                trace.text = frame_trace.text
            if getattr(frame_trace, 'marker', None) is not None:
                trace.marker.color = frame_trace.marker.color

    # ▶ 기본 화면은 완료 상태이며, 재생 버튼은 선택한 시작~끝 구간을 처음부터 재생한다.
    fig_acc.update_layout(
        uirevision=f'acceleration-{value_col}',
        title=dict(
            text=title,
            x=0.0,
            xanchor='left',
            y=0.985,
            yanchor='top'
        ),
        xaxis_title='주간 증감률 (지수)',
        yaxis_title='가속도 (증감률 변화)',
        xaxis=dict(range=[-x_abs, x_abs], zeroline=False),
        yaxis=dict(range=[-y_abs, y_abs], zeroline=False),
        template='plotly_white',
        height=820,
        # x축 제목/눈금을 가리지 않도록 플레이 버튼을 그래프 아래에 배치한다.
        margin=dict(t=220, b=95, l=55, r=25),
        hovermode='closest',
        legend=dict(
            orientation='h',
            yanchor='bottom', y=1.015,
            xanchor='left', x=0,
            title='지역',
            groupclick='togglegroup',
            traceorder='normal',
            itemsizing='constant'
        ),
        updatemenus=[dict(
            type='buttons',
            direction='left',
            x=0.0, y=-0.18,
            xanchor='left', yanchor='top',
            showactive=False,
            buttons=[
                dict(
                    label='▶ 재생',
                    method='animate',
                    args=[None, {
                        'frame': {'duration': 180, 'redraw': True},
                        'transition': {'duration': 0},
                        'fromcurrent': False,
                        'mode': 'immediate'
                    }]
                ),
                dict(
                    label='⏸ 일시정지',
                    method='animate',
                    args=[[None], {
                        'frame': {'duration': 0, 'redraw': False},
                        'transition': {'duration': 0},
                        'mode': 'immediate'
                    }]
                )
            ]
        )]
    )

    st.plotly_chart(fig_acc, use_container_width=True, key=f'acc_{value_col}')

    # 그래프 아래에 두 개의 핸들이 있는 구간 슬라이더를 표시한다.
    # 왼쪽 핸들 = 시작점, 오른쪽 핸들 = 끝점.
    # Streamlit slider의 key 자체를 범위 상태로 사용한다.
    # 사용자가 어느 핸들이든 놓는 즉시 해당 구간으로 앱이 다시 실행되고,
    # Plotly는 동일한 uirevision을 유지하므로 사용자가 꺼 둔 범례 상태도 유지한다.
    st.slider(
        '분석 구간: 시작점 ↔ 끝점 (두 핸들을 각각 이동)',
        min_value=default_range[0],
        max_value=default_range[1],
        value=saved_range,
        format='YYYY-MM-DD',
        key=range_key,
        on_change=lambda: None,
    )
    new_range = st.session_state[range_key]
    if new_range != saved_range:
        # 범위가 바뀐 경우 다음 실행에서 새 범위를 즉시 반영한다.
        st.rerun()
    st.caption(
        f'시작점: {acc_start.strftime("%Y-%m-%d")}   |   끝점: {acc_end.strftime("%Y-%m-%d")}  '
        '— 기본값은 전체 기간이며, 두 핸들을 각각 움직이면 선택 구간의 전체 경로가 즉시 다시 그려집니다. 재생은 선택한 시작점부터 끝점까지 진행됩니다.'
    )


# 가속도 데이터 계산
df_sale_acc = make_acceleration_data(df, '매매지수', '매매가속도')
df_rent_acc = make_acceleration_data(df, '전세지수', '전세가속도')

# 두 그래프를 나란히 배치
acc_col1, acc_col2 = st.columns(2)

with acc_col1:
    draw_acceleration_quadrant(
        df_sale_acc,
        '매매증감',
        '매매가속도',
        f'매매증감 가속도 사분면 ({start_date} ~ {end_date})',
        color_map
    )

with acc_col2:
    draw_acceleration_quadrant(
        df_rent_acc,
        '전세증감',
        '전세가속도',
        f'전세증감 가속도 사분면 ({start_date} ~ {end_date})',
        color_map
    )


# =======가속도 추가부분 끝========


st.divider() 
mask_chg = (df_chg["날짜"] >= pd.to_datetime(start_date)) & \
           (df_chg["날짜"] <= pd.to_datetime(end_date)) & \
           (df_chg["지역"].isin(selected_regions))
df_chg_sel = df_chg[mask_chg].sort_values(['날짜', '지역'])


if df_chg_sel.empty:
    st.warning("선택한 범위에 증감 데이터가 없습니다.")
else:
    df_bar = df_chg_sel.melt(
        id_vars=['날짜', '지역'], 
        value_vars=['매매증감', '전세증감'],
        var_name='구분', 
        value_name='증감률'
    )

    df_bar['날짜_표시'] = df_bar['날짜'].dt.strftime('%Y-%m-%d')

    st.write(f"######  jak 작부동산 지역별 매매/전세 증감률 ({start_date} ~ {end_date})")

    for region in selected_regions:
        region_df = df_bar[df_bar['지역'] == region]
        
        if region_df.empty:
            continue
            
        fig_each = px.bar(
            region_df,
            x='날짜_표시',
            y='증감률',
            color='구분',
            barmode='group',
            title=f"{region}", 
            color_discrete_map={'매매증감': '#EF553B', '전세증감': '#636EFA'},
            labels={'증감률': '증감률 (%)', '날짜_표시': ''},
            height=350, 
            template="plotly_white"
        )

        fig_each.update_layout(
            margin=dict(t=40, b=10, l=10, r=10),
            showlegend=(region == selected_regions[0]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified"
        )

        fig_each.update_xaxes(type='category', tickangle=35)
        fig_each.add_hline(y=0, line_width=1, line_color="black")

        st.plotly_chart(fig_each, use_container_width=True)












