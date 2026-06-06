import streamlit as st
import requests
import pandas as pd
import datetime
import urllib3
import math

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# 1. 配置区 (把你们俩的 Token 填在这里)
# ==========================================
TOKEN_A = st.secrets["TOKEN_A"]
TOKEN_B = st.secrets["TOKEN_B"]

USER_A_NAME = "跑者 A"
USER_B_NAME = "跑者 B"

# ==========================================
# 2. 数据处理与换算函数
# ==========================================
# 使用 st.cache_data 缓存数据 10 分钟，避免每次刷新网页都去请求高驰 API
@st.cache_data(ttl=600) 
def fetch_coros_data(token):
    if not token:
        return pd.DataFrame() # 如果没有填 Token，返回空表格
        
    url = "https://teamcnapi.coros.com/activity/query"
    headers = {
        "accesstoken": token,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "origin": "https://t.coros.com",
    }
    params = {"size": 20, "pageNumber": 1, "modeList": ""}
    
    try:
        response = requests.get(url, headers=headers, params=params, verify=False, timeout=10)
        if response.status_code == 200:
            data_list = response.json().get('data', {}).get('dataList', [])
            return process_raw_data(data_list)
    except Exception as e:
        st.error(f"获取数据失败: {e}")
    return pd.DataFrame()

def process_raw_data(data_list):
    """将高驰的原始 JSON 列表转换为干净的 Pandas 数据表"""
    clean_data = []
    for item in data_list:
        # 换算距离
        dist_km = item.get('distance', 0) / 1000
        
        # 换算时间
        timestamp = item.get('startTime', 0)
        dt_obj = datetime.datetime.fromtimestamp(timestamp)
        date_str = dt_obj.strftime('%m-%d %H:%M')
        
        # 换算配速 (秒/公里 -> 分:秒)
        speed_sec = item.get('avgSpeed', 0)
        if speed_sec > 0:
            minutes = math.floor(speed_sec / 60)
            seconds = int(speed_sec % 60)
            pace_str = f"{minutes}'{seconds:02d}''"
        else:
            pace_str = "-'--''"
            
        clean_data.append({
            "日期": date_str,
            "原始时间": dt_obj,
            "运动名称": item.get('name', '未知运动'),
            "距离(km)": round(dist_km, 2),
            "配速": pace_str,
            "平均心率": item.get('avgHr', 0),
            "负荷": item.get('trainingLoad', 0)
        })
        
    return pd.DataFrame(clean_data)

# ==========================================
# 3. Streamlit 网页界面构建
# ==========================================
st.set_page_config(page_title="高驰双人看板", page_icon="🏃", layout="centered")
st.title("🏃 高驰双人训练看板")

# 拉取数据
df_a = fetch_coros_data(TOKEN_A)
df_b = fetch_coros_data(TOKEN_B)

# --- 核心指标对比看板 ---
st.subheader("🔥 近期数据 PK (最新 20 条记录)")
col1, col2 = st.columns(2)

with col1:
    st.success(f"👦 {USER_A_NAME}")
    if not df_a.empty:
        total_dist_a = df_a['距离(km)'].sum()
        avg_hr_a = int(df_a['平均心率'].mean())
        st.metric(label="累计跑量", value=f"{total_dist_a:.2f} km")
        st.metric(label="平均心率", value=f"{avg_hr_a} bpm")
    else:
        st.info("暂无数据")

with col2:
    st.info(f"👧 {USER_B_NAME}")
    if not df_b.empty:
        total_dist_b = df_b['距离(km)'].sum()
        avg_hr_b = int(df_b['平均心率'].mean())
        st.metric(label="累计跑量", value=f"{total_dist_b:.2f} km")
        st.metric(label="平均心率", value=f"{avg_hr_b} bpm")
    else:
        st.warning("请在代码中补全 B 的 Token")

st.divider()

# --- 详细活动列表 (移动端优化版：可点击展开) ---
st.subheader("📅 详细跑步记录")
tab1, tab2 = st.tabs([f"{USER_A_NAME} 的动态", f"{USER_B_NAME} 的动态"])

# 提取出一个专门用来画列表的函数，让代码更干净
def draw_activity_feed(df):
    if df.empty:
        st.info("暂无数据")
        return
        
    # 逐行遍历表格数据
    for index, row in df.iterrows():
        # 1. 列表封面：展示日期、距离和名称
        title = f"🏃 {row['距离(km)']} km | {row['日期']} | {row['运动名称']}"
        
        # 2. 点击展开后的内部视图
        with st.expander(label=title):
            # 将详情分成三列展示，类似手机上的数据卡片
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("平均配速", row['配速'])
            with c2:
                st.metric("平均心率", f"{row['平均心率']} bpm")
            with c3:
                st.metric("体能负荷", row['负荷'])
            
            # 进阶占位：你甚至可以在这里加个进度条来评估强度
            if row['平均心率'] > 150:
                st.warning("🔥 这次跑得有点猛哦！注意休息。")
            elif row['平均心率'] > 0:
                st.success("🍃 轻松有氧，状态不错。")

with tab1:
    draw_activity_feed(df_a)

with tab2:
    draw_activity_feed(df_b)
