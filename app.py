
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit.components.v1 as components
import json

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

# 가속도 시작

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
    '''가속도 사분면을 브라우저에서 직접 갱신한다.

    Streamlit 서버 재실행에 의존하지 않고 Plotly.js + native range input을 사용하므로
    두 날짜 핸들을 마우스로 잡고 이동하는 동안 input 이벤트마다 그래프가 즉시 갱신된다.
    범례 ON/OFF 상태도 브라우저 state로 유지한다.
    '''
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

    x_min, x_max = data[x_col].min(), data[x_col].max()
    y_min, y_max = data[accel_col].min(), data[accel_col].max()
    x_abs = max(abs(x_min), abs(x_max), 0.0001) * 1.18
    y_abs = max(abs(y_min), abs(y_max), 0.0001) * 1.18

    dates = sorted(data['날짜'].dropna().unique())
    date_strings = [pd.Timestamp(d).strftime('%Y-%m-%d') for d in dates]

    regions_payload = []
    for region in selected_regions:
        rdf = data[data['지역'] == region].sort_values('날짜').copy()
        if rdf.empty:
            continue
        points = []
        for _, row in rdf.iterrows():
            points.append({
                'date': pd.Timestamp(row['날짜']).strftime('%Y-%m-%d'),
                'x': float(row[x_col]),
                'y': float(row[accel_col]),
                'q': row['사분면']
            })
        regions_payload.append({
            'name': str(region),
            'color': region_color_map.get(region, '#333333'),
            'points': points
        })

    if not regions_payload or not dates:
        st.info(f'{title} 데이터가 없습니다.')
        return

    payload = {
        'title': title,
        'dates': date_strings,
        'regions': regions_payload,
        'xAbs': float(x_abs),
        'yAbs': float(y_abs),
        'quadrantColors': quadrant_colors
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))

    component_html = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
html,body {{ margin:0; padding:0; background:#fff; font-family:Arial,"Noto Sans KR",sans-serif; overflow:hidden; }}
#plot {{ width:100%; height:610px; }}
.controls {{ margin:4px 20px 0 55px; }}
.buttons {{ display:flex; gap:6px; margin-bottom:12px; }}
button {{ background:#fff; border:1px solid #b8c7dd; color:#607a9d; border-radius:3px; padding:7px 14px; font-size:13px; cursor:pointer; }}
button:hover {{ background:#f4f7fb; }}
.range-wrap {{ position:relative; height:46px; margin-top:2px; }}
.range-track {{ position:absolute; left:0; right:0; top:13px; height:4px; background:#d7e0ed; border-radius:3px; }}
.range-selected {{ position:absolute; top:13px; height:4px; background:#9eb6d8; border-radius:3px; }}
input[type=range] {{ position:absolute; left:0; top:0; width:100%; height:30px; margin:0; background:transparent; pointer-events:none; -webkit-appearance:none; appearance:none; }}
input[type=range]::-webkit-slider-runnable-track {{ height:4px; background:transparent; }}
input[type=range]::-moz-range-track {{ height:4px; background:transparent; }}
input[type=range]::-webkit-slider-thumb {{ -webkit-appearance:none; appearance:none; width:20px; height:20px; border-radius:50%; background:#fff; border:1px solid #9eb6d8; box-shadow:0 1px 2px rgba(0,0,0,.12); pointer-events:auto; cursor:pointer; margin-top:-8px; }}
input[type=range]::-moz-range-thumb {{ width:20px; height:20px; border-radius:50%; background:#fff; border:1px solid #9eb6d8; box-shadow:0 1px 2px rgba(0,0,0,.12); pointer-events:auto; cursor:pointer; }}
#startRange {{ z-index:5; }}
#endRange {{ z-index:4; }}
.range-labels {{ display:flex; justify-content:space-between; margin-top:2px; color:#607a9d; font-size:11px; }}
.current {{ text-align:center; color:#607a9d; font-size:12px; margin-bottom:5px; }}
.hint {{ color:#888; font-size:10px; text-align:center; margin-top:1px; }}
</style>
</head>
<body>
<div id="plot"></div>
<div class="controls">
  <div class="buttons">
    <button id="play" type="button">▶ 재생</button>
    <button id="pause" type="button">Ⅱ 일시정지</button>
  </div>
  <div class="current" id="currentDate"></div>
  <div class="range-wrap">
    <div class="range-track"></div>
    <div class="range-selected" id="selectedBar"></div>
    <input id="startRange" type="range" min="0" max="0" value="0" step="1" aria-label="분석 시작점">
    <input id="endRange" type="range" min="0" max="0" value="0" step="1" aria-label="분석 끝점">
  </div>
  <div class="range-labels"><span id="startLabel"></span><span id="endLabel"></span></div>
  <div class="hint">왼쪽 핸들 = 시작점 · 오른쪽 핸들 = 끝점 · 핸들을 잡고 이동하는 동안 그래프가 실시간 갱신됩니다.</div>
</div>
<script>
(function() {{
  const P = {payload_json};
  const dates = P.dates;
  const regions = P.regions;
  const qColors = P.quadrantColors;
  const plot = document.getElementById('plot');
  const startRange = document.getElementById('startRange');
  const endRange = document.getElementById('endRange');
  const currentDate = document.getElementById('currentDate');
  const startLabel = document.getElementById('startLabel');
  const endLabel = document.getElementById('endLabel');
  const selectedBar = document.getElementById('selectedBar');
  const playBtn = document.getElementById('play');
  const pauseBtn = document.getElementById('pause');

  let startIdx = 0;
  let endIdx = dates.length - 1;
  let playIdx = endIdx;
  let timer = null;
  let playing = false;
  // 서버 rerun과 무관한 브라우저 상태: 범례를 꺼 놓으면 핸들 이동에도 계속 꺼져 있다.
  const regionVisible = Object.fromEntries(regions.map(r => [r.name, true]));

  function pointsFor(region, lo, hi) {{
    const arr = region.points.filter(p => p.date >= dates[lo] && p.date <= dates[hi]);
    return arr.length ? arr : region.points.filter(p => p.date <= dates[hi]).slice(-1);
  }}

  function firstPoint(region, lo, hi) {{
    const arr = region.points.filter(p => p.date >= dates[lo] && p.date <= dates[hi]);
    return arr.length ? arr[0] : region.points.find(p => p.date >= dates[lo]) || region.points[0];
  }}

  function buildData(lo, hi, frameIdx) {{
    const traces = [];
    const currentIdx = Math.max(lo, Math.min(frameIdx, hi));
    regions.forEach((r) => {{
      const path = pointsFor(r, lo, currentIdx);
      const first = firstPoint(r, lo, hi);
      const last = path[path.length - 1];
      const markerColors = path.map(p => qColors[p.q]);
      const vis = regionVisible[r.name] ? true : 'legendonly';

      traces.push({{
        x:path.map(p=>p.x), y:path.map(p=>p.y), mode:'lines+markers',
        name:r.name, legendgroup:r.name, showlegend:true, visible:vis,
        line:{{color:r.color,width:2}}, marker:{{color:markerColors,size:6,opacity:.82}},
        customdata:path.map(p=>[r.name,p.date,p.x,p.y]),
        hovertemplate:'<b>%{{customdata[0]}}</b><br>날짜: %{{customdata[1]}}<br>증감률: %{{customdata[2]:.4f}}<br>가속도: %{{customdata[3]:.4f}}<extra></extra>'
      }});
      traces.push({{
        x:[first.x], y:[first.y], mode:'text', text:['START'], textposition:'bottom center',
        textfont:{{size:9,color:'#555'}}, legendgroup:r.name, showlegend:false, visible:vis, hoverinfo:'skip'
      }});
      traces.push({{
        x:[last.x], y:[last.y], mode:'markers+text', text:[r.name], textposition:'top center',
        textfont:{{size:10}}, marker:{{color:r.color,size:10}}, legendgroup:r.name,
        showlegend:false, visible:vis, hoverinfo:'skip'
      }});
    }});
    return traces;
  }}

  function makeLayout() {{
    const xa=P.xAbs, ya=P.yAbs;
    return {{
      title:{{text:P.title,x:0,xanchor:'left',y:.985,yanchor:'top',font:{{size:16}}}},
      xaxis:{{title:'주간 증감률 (지수)',range:[-xa,xa],zeroline:false}},
      yaxis:{{title:'가속도 (증감률 변화)',range:[-ya,ya],zeroline:false}},
      template:'plotly_white', height:610, margin:{{t:95,b:70,l:55,r:25}}, hovermode:'closest',
      legend:{{orientation:'h',yanchor:'bottom',y:1.02,xanchor:'left',x:0,title:'지역',groupclick:'togglegroup',traceorder:'normal',itemsizing:'constant'}},
      shapes:[
        {{type:'rect',x0:0,x1:xa,y0:0,y1:ya,fillcolor:'rgba(239,85,59,.10)',line_width:0,layer:'below'}},
        {{type:'rect',x0:-xa,x1:0,y0:0,y1:ya,fillcolor:'rgba(0,204,150,.10)',line_width:0,layer:'below'}},
        {{type:'rect',x0:-xa,x1:0,y0:-ya,y1:0,fillcolor:'rgba(99,110,250,.10)',line_width:0,layer:'below'}},
        {{type:'rect',x0:0,x1:xa,y0:-ya,y1:0,fillcolor:'rgba(255,161,90,.10)',line_width:0,layer:'below'}}
      ],
      annotations:[
        {{x:xa*.68,y:ya*.87,text:'<b>상승가속</b>',showarrow:false}},
        {{x:-xa*.68,y:ya*.87,text:'<b>하락반등</b>',showarrow:false}},
        {{x:-xa*.68,y:-ya*.87,text:'<b>하락가속</b>',showarrow:false}},
        {{x:xa*.68,y:-ya*.87,text:'<b>상승둔화</b>',showarrow:false}}
      ]
    }};
  }}

  async function render(lo, hi, frameIdx) {{
    frameIdx = Math.max(lo, Math.min(frameIdx, hi));
    playIdx = frameIdx;
    const newData = buildData(lo, hi, frameIdx);
    if (!plot.data) {{
      await Plotly.newPlot(plot, newData, makeLayout(), {{responsive:true,displaylogo:false}});
    }} else {{
      await Plotly.react(plot, newData, makeLayout(), {{responsive:true,displaylogo:false}});
    }}
    currentDate.textContent='날짜: '+dates[frameIdx];
    startLabel.textContent=dates[lo];
    endLabel.textContent=dates[hi];
    const max=Math.max(1,dates.length-1);
    selectedBar.style.left=(lo/max*100)+'%';
    selectedBar.style.width=((hi-lo)/max*100)+'%';
  }}

  function bindLegendHandler() {{
    if (plot.__legendBound) return;
    plot.__legendBound = true;
    plot.on('plotly_legendclick', function(e) {{
      const regionIndex=Math.floor(e.curveNumber/3);
      const r=regions[regionIndex];
      if (!r) return false;
      regionVisible[r.name]=!regionVisible[r.name];
      render(startIdx,endIdx,Math.min(playIdx,endIdx));
      return false;
    }});
  }}

  function updateFromInputs(source) {{
    let a=parseInt(startRange.value,10);
    let b=parseInt(endRange.value,10);
    if (a>=b) {{
      if (source==='start') a=Math.max(0,b-1);
      else b=Math.min(dates.length-1,a+1);
      startRange.value=String(a);
      endRange.value=String(b);
    }}
    startIdx=a; endIdx=b;
    stop();
    // input 이벤트는 pointer를 잡고 이동하는 동안 계속 발생하므로 서버 rerun 없이 실시간 갱신된다.
    render(startIdx,endIdx,endIdx);
  }}

  function stop() {{
    if (timer) {{ clearInterval(timer); timer=null; }}
    playing=false;
  }}

  function play() {{
    stop();
    playing=true;
    playIdx=startIdx;
    render(startIdx,endIdx,playIdx);
    timer=setInterval(function() {{
      if (!playing) return;
      playIdx++;
      render(startIdx,endIdx,playIdx);
      if (playIdx>=endIdx) stop();
    }},180);
  }}

  startRange.max=String(dates.length-1);
  endRange.max=String(dates.length-1);
  startRange.value='0';
  endRange.value=String(dates.length-1);
  startRange.addEventListener('input',()=>updateFromInputs('start'));
  endRange.addEventListener('input',()=>updateFromInputs('end'));
  playBtn.addEventListener('click',play);
  pauseBtn.addEventListener('click',stop);

  // 기본값은 전체 기간 + 애니메이션 완성 상태.
  render(0,dates.length-1,dates.length-1).then(bindLegendHandler);
}})();
</script>
</body>
</html>'''

    components.html(component_html, height=820, scrolling=False)


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

# 가속도 끝

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












