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

# --- 详细活动列表 (使用 Tabs 切换视图) ---
tab1, tab2 = st.tabs([f"{USER_A_NAME} 的动态", f"{USER_B_NAME} 的动态"])

with tab1:
    if not df_a.empty:
        st.dataframe(df_a[['日期', '运动名称', '距离(km)', '配速', '平均心率']], width='stretch')

with tab2:
    if not df_b.empty:
        st.dataframe(df_b[['日期', '运动名称', '距离(km)', '配速', '平均心率']], width='stretch')