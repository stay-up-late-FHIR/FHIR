import streamlit as st
import requests
import json
import pandas as pd
import time

# --- 1. 匯入你的兩個核心模組 ---
# 確保 fhir_gateway.py 和 ai_engine.py 都在同一個資料夾內
from fhir_gateway import create_raw_data_bundle
from ai_engine import analyze_and_create_report

# --- 2. 系統設定 ---
st.set_page_config(layout="wide", page_title="h1 智慧醫療物聯網系統")
FHIR_SERVER_URL = "http://hapi.fhir.org/baseR4"

# 初始化 Session State (這是模擬手錶與雲端溝通的記憶體)
if 'watch_alert' not in st.session_state:
    st.session_state['watch_alert'] = None  # 用來存 "警報訊息"
if 'has_data' not in st.session_state:
    st.session_state['has_data'] = False    # 用來存 "是否已上傳"

# --- 3. 輔助函式 ---
def send_bundle(bundle):
    """通用的上傳函式 (POST)"""
    headers = {"Content-Type": "application/fhir+json"}
    try:
        return requests.post(FHIR_SERVER_URL, json=bundle, headers=headers)
    except Exception as e:
        return str(e)

# ==========================================
#  UI 介面開始
# ==========================================
st.title("🏥 h1 智慧醫療物聯網系統 (完整閉鎖迴路展示)")
st.caption("Architecture: Streamlit Edge (Watch) ↔ Python Gateway ↔ HAPI FHIR Server ↔ AI Engine")

# 建立兩個主要頁面：手錶端 (患者) vs 醫院端 (醫生)
tab1, tab2 = st.tabs(["⌚ 患者穿戴裝置 (Client)", "👨‍⚕️ 醫院戰情室 (Server)"])

# ==========================================
#  TAB 1: 手錶端 (負責採集 + 接收警報)
# ==========================================
with tab1:
    col_watch_ui, col_watch_input = st.columns([1, 1])

    # --- 左半邊：手錶螢幕 (接收 AI 的動作) ---
    with col_watch_ui:
        st.subheader("📱 手錶即時畫面")
        
        # 檢查 Session State 有沒有 AI 傳回來的警報
        alert_msg = st.session_state['watch_alert']
        
        if alert_msg:
            # 🚨 狀況 A: 收到 AI 的 High Risk 指令 -> 觸發手錶反應
            st.error(f"🚨 【緊急通知】 {alert_msg}")
            
            # CSS 動畫：讓整個網頁震動 (模擬手錶震動)
            st.markdown("""
                <style>
                .stApp { animation: shake 0.5s; animation-iteration-count: infinite; }
                @keyframes shake {
                  0% { transform: translate(1px, 1px) rotate(0deg); }
                  10% { transform: translate(-1px, -2px) rotate(-1deg); }
                  20% { transform: translate(-3px, 0px) rotate(1deg); }
                  30% { transform: translate(3px, 2px) rotate(0deg); }
                  40% { transform: translate(1px, -1px) rotate(1deg); }
                  50% { transform: translate(-1px, 2px) rotate(-1deg); }
                  60% { transform: translate(-3px, 1px) rotate(0deg); }
                  70% { transform: translate(3px, 1px) rotate(-1deg); }
                  80% { transform: translate(-1px, -1px) rotate(1deg); }
                  90% { transform: translate(1px, 2px) rotate(0deg); }
                  100% { transform: translate(1px, -2px) rotate(-1deg); }
                }
                </style>
                ⚠️ **檢測到異常！手錶震動中... 請立即停止活動！**
                """, unsafe_allow_html=True)
            
            if st.button("🔕 我已平安 (解除警報)"):
                st.session_state['watch_alert'] = None
                st.rerun()
        else:
            # 🟢 狀況 B: 平安無事
            st.success("✅ 系統連線正常 | 監測中...")
            current_hr = st.session_state.get('hr', '--')
            st.metric(label="即時心率", value=f"{current_hr} BPM")

    # --- 右半邊：數據輸入 (模擬感測器) ---
    with col_watch_input:
        st.subheader("⚙️ 感測器模擬")
        st.info("請在此輸入模擬數據並上傳")
        
        hr_input = st.slider("模擬心率 (Heart Rate)", 40, 200, 75)
        name_input = st.text_input("患者姓名", "Wang Xiao-Ming")
        
        if st.button("📡 上傳數據至雲端 (Upload Raw Data)", type="primary"):
            # 1. 呼叫 Gateway 進行 FHIR 轉換
            raw_bundle, pid, oid = create_raw_data_bundle(hr_input, 25.033, 121.565, name_input)
            
            # 2. 上傳到 HAPI FHIR Server
            with st.spinner("正在與 FHIR Server 通訊..."):
                res = send_bundle(raw_bundle)
            
            # 3. 處理結果
            if hasattr(res, 'status_code') and res.status_code == 200:
                st.toast("上傳成功！等待 AI 分析...", icon="☁️")
                
                # 將關鍵 ID 存入 Session State (傳遞給 Tab 2 用)
                st.session_state['pid'] = pid
                st.session_state['oid'] = oid
                st.session_state['hr'] = hr_input
                st.session_state['has_data'] = True
                st.session_state['watch_alert'] = None # 上傳新數據時，先清除舊警報
            else:
                st.error("上傳失敗，請檢查網路或是 FHIR Server 狀態")

# ==========================================
#  TAB 2: 醫院端 (AI 分析 + 歷史調閱)
# ==========================================
with tab2:
    st.header("Step 2: 醫院戰情室")
    
    # 分成兩個子功能
    sub_tab_ai, sub_tab_history = st.tabs(["⚡ 即時 AI 診斷 (Real-time)", "📈 歷史病歷調閱 (History)"])

    # --- 功能 A: AI 觸發與決策 ---
    with sub_tab_ai:
        if st.session_state['has_data']:
            st.info(f"收到最新數據：Patient ID: {st.session_state['pid']} | Heart Rate: {st.session_state['hr']}")
            
            if st.button("🤖 啟動 AI 引擎分析"):
                # 1. 呼叫 AI Engine
                ai_bundle, risk_level = analyze_and_create_report(
                    st.session_state['hr'], 
                    st.session_state['pid'], 
                    st.session_state['oid']
                )
                
                # 2. 上傳分析報告
                send_bundle(ai_bundle)
                
                # 3. 【關鍵】判斷是否要反向控制手錶
                if risk_level == "high":
                    st.error("⚠️ AI 判定：高風險 (High Risk)！已發出急救請求。")
                    # 設定警報，這會傳回 Tab 1
                    st.session_state['watch_alert'] = "偵測到心跳過快！有猝死風險！"
                    st.toast("警報已發送至手錶！", icon="🚨")
                else:
                    st.success("🟢 AI 判定：數據正常。")
                    st.session_state['watch_alert'] = None
                
                with st.expander("查看 AI 產出的 FHIR Bundle"):
                    st.json(ai_bundle)
        else:
            st.warning("尚無新數據，請先至「患者端」上傳資料。")

    # --- 功能 B: 歷史資料調閱 (GET Request) ---
    with sub_tab_history:
        st.markdown("#### 📂 調閱雲端電子病歷")
        search_name = st.text_input("輸入查詢姓名", "Wang Xiao-Ming", key="search_name")
        
        if st.button("🔄 從 FHIR Server 下載病歷"):
            with st.spinner("正在從 HAPI FHIR Server 抓取資料..."):
                # 1. 組裝 FHIR Search API
                # 邏輯：搜尋 Observation，代碼=8867-4(心率)，病人名字包含輸入值，按時間倒序
                api_url = f"{FHIR_SERVER_URL}/Observation?code=8867-4&subject.name={search_name}&_sort=-date&_count=50"
                
                try:
                    resp = requests.get(api_url).json()
                    
                    if 'entry' in resp:
                        # 2. 解析 JSON 並轉成表格
                        records = []
                        for entry in resp['entry']:
                            try:
                                r = entry['resource']
                                val = r['valueQuantity']['value']
                                time_str = r['effectiveDateTime']
                                records.append({"Time": time_str, "Heart Rate (BPM)": val})
                            except:
                                continue
                        
                        if records:
                            df = pd.DataFrame(records)
                            # 把時間字串轉成 datetime 物件，畫圖比較準
                            df['Time'] = pd.to_datetime(df['Time'])
                            
                            st.success(f"成功調閱 {len(df)} 筆歷史紀錄！")
                            
                            # 畫圖
                            st.line_chart(df.set_index('Time')['Heart Rate (BPM)'])
                            # 秀表格
                            st.dataframe(df)
                        else:
                            st.warning("有找到資料結構，但內容無法解析。")
                    else:
                        st.warning(f"查無 '{search_name}' 的相關數據。")
                        
                except Exception as e:
                    st.error(f"連線錯誤: {e}")
