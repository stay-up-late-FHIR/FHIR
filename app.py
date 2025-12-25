import streamlit as st
import requests
import uuid
import time
from datetime import datetime, timezone

try:
    from fhir_gateway import create_raw_data_bundle
    from ai_engine import analyze_and_create_report
except ImportError:
    st.error("找不到必要的模組 (fhir_gateway.py 或 ai_engine.py)。請確認檔案位置。")
    st.stop()

st.set_page_config(layout="wide", page_title="h1 雙軌醫療系統 (FHIR 標準版)")
FHIR_SERVER_URL = "https://server.fire.ly" 

# --- 初始化 Session State ---
if 'watch_screen' not in st.session_state: st.session_state['watch_screen'] = "normal"
if 'watch_message' not in st.session_state: st.session_state['watch_message'] = None 
if 'has_data' not in st.session_state: st.session_state['has_data'] = False
if 'vitals' not in st.session_state: st.session_state['vitals'] = {}
if 'pid' not in st.session_state: st.session_state['pid'] = None
if 'ai_status' not in st.session_state: st.session_state['ai_status'] = "unknown"

# --- Helper Functions ---

def send_bundle(bundle):
    headers = {"Content-Type": "application/fhir+json"}
    try:
        # 設定 timeout 避免卡死
        response = requests.post(FHIR_SERVER_URL, json=bundle, headers=headers, timeout=10)
        response.raise_for_status() # 檢查 HTTP 錯誤
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"連線錯誤: {e}")
        return None

def send_service_request(patient_id, risk_id):
    """發送醫療處置請求 (Start CPR)"""
    req_id = str(uuid.uuid4())
    # 若 risk_id 為空，給予預設值以防報錯
    safe_risk_id = risk_id if risk_id else "unknown-risk"
    
    sr = {
        "resourceType": "ServiceRequest",
        "id": req_id,
        "status": "active",
        "intent": "order",
        "priority": "stat",
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "40617009", "display": "Start CPR"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "reasonReference": [{"reference": f"RiskAssessment/{safe_risk_id}"}]
    }
    res = send_bundle(sr)
    return req_id, sr, res

def send_communication_request(patient_id, message_text, priority="routine"):
    """發送溝通請求 (Doctor Instruction)"""
    req_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()
    
    comm_req = {
        "resourceType": "CommunicationRequest",
        "id": req_id,
        "status": "active",
        "priority": priority,
        "subject": {"reference": f"Patient/{patient_id}"},
        "payload": [{"contentString": message_text}],
        "authoredOn": timestamp,
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/communication-category", "code": "instruction"}]}]
    }
    
    res = send_bundle(comm_req)
    return req_id, comm_req, res

# --- UI 開始 ---
st.title("🏥 h1 智慧醫療系統：CommunicationRequest 實作")
st.caption("流程 A: 預防監測 | 流程 B: 急救回應 | 醫生溝通: CommunicationRequest")

tab1, tab2 = st.tabs(["⌚ 穿戴裝置 (User)", "👨‍⚕️ 醫療中心 (Doctor)"])

# ==========================================
#  TAB 1: 手錶端
# ==========================================
with tab1:
    col_watch, col_sensor = st.columns([1, 1.5])

    with col_watch:
        st.subheader("📱 手錶畫面")
        state = st.session_state['watch_screen']
        msg = st.session_state['watch_message']

        # [修正 1] 優先級調整：緊急狀況 (CPR) 必須最先判斷
        if state == "cpr":
            st.error("🆘 EMERGENCY - ServiceRequest Received")
            st.markdown("""
            <div style="background-color: #d32f2f; color: white; padding: 20px; border-radius: 10px; text-align: center; animation: pulse 1s infinite;">
                <h1>START CPR</h1>
                <p>🚑 Ambulance Dispatched</p>
            </div>
            <style>@keyframes pulse { 0% {transform: scale(1);} 50% {transform: scale(1.05);} 100% {transform: scale(1);} }</style>
            """, unsafe_allow_html=True)
            if st.button("🔕 解除急救"):
                st.session_state['watch_screen'] = "normal"
                st.rerun()

        # [修正 1] 其次是文字訊息
        elif msg:
            st.info("📩 收到新訊息 (CommunicationRequest)")
            st.markdown(f"""
            <div style="background-color: #e3f2fd; color: #0d47a1; padding: 15px; border-radius: 10px; border-left: 5px solid #2196f3;">
                <strong>👨‍⚕️ Dr. AI:</strong><br>
                <span style="font-size: 1.2em;">{msg}</span>
            </div>
            """, unsafe_allow_html=True)
            if st.button("知道了 (Dismiss Msg)"):
                st.session_state['watch_message'] = None
                st.rerun()

        # [修正 1] 再來是預防性警報
        elif state == "rest":
            st.warning("⚠️ 疲勞預警")
            st.write("檢測到高壓力，請休息。")
            if st.button("✅ 解除提醒"):
                st.session_state['watch_screen'] = "normal"
                st.rerun()

        else:
            st.success("✅ 監測中...")
            if st.session_state['has_data']:
                v = st.session_state['vitals']
                st.metric("Heart Rate", f"{v.get('hr')} bpm")

    with col_sensor:
        st.subheader("⚙️ 生理感測")
        c1, c2 = st.columns(2)
        user_name = c1.text_input("姓名", "Wang Xiao-Mei")
        user_id = c2.text_input("ID", "A223456789")
        
        hr = st.slider("❤️ 心率", 40, 200, 75)
        spo2 = st.slider("💧 血氧", 70, 100, 98)
        hrv = st.slider("📈 HRV", 10, 100, 60)
        stress = st.slider("🤯 壓力", 0, 100, 20)
        
        # [修正 2] 定義固定參數變數，避免數值不一致
        sys_bp = 110
        dia_bp = 70
        resp_rate = 16
        sleep_hours = 7

        if st.button("📡 上傳數據"):
            with st.spinner("上傳中..."):
                # 1. 產生 FHIR 數據包 (使用變數傳遞)
                raw_bundle, pid, oid = create_raw_data_bundle(
                    user_id, user_name, hr, spo2, sys_bp, dia_bp, resp_rate, hrv, stress, sleep_hours, 25.033, 121.565
                )
                
                # 2. 上傳到伺服器 (包含錯誤檢查)
                res = send_bundle(raw_bundle)
                
                if res and res.status_code in [200, 201]:
                    # 3. 更新系統狀態
                    st.session_state['pid'] = pid
                    st.session_state['has_data'] = True
                    
                    # 4. 存入完整數據 (使用上方定義的變數)
                    st.session_state['vitals'] = {
                        "hr": hr, 
                        "spo2": spo2, 
                        "hrv": hrv, 
                        "stress": stress, 
                        "name": user_name,
                        "sys_bp": sys_bp,
                        "dia_bp": dia_bp,
                        "resp": resp_rate,
                        "sleep": sleep_hours
                    }
                    
                    st.session_state['watch_screen'] = "normal"
                    st.toast("上傳成功", icon="✅")
                else:
                    st.error("上傳失敗，請檢查網路或 Server 狀態")

# ==========================================
#  TAB 2: 醫療中心 (Doctor)
# ==========================================
with tab2:
    st.header("Step 4: AI & Doctor Dashboard")
    
    if st.session_state['has_data']:
        v = st.session_state['vitals']
        st.info(f"當前病患: {v['name']} | HR: {v['hr']} | SpO2: {v['spo2']} | BP: {v['sys_bp']}/{v['dia_bp']}")

        # AI 分析區塊
        if st.button("🤖 AI 風險計算"):
            with st.spinner("AI 分析中..."):
                bundle, status, desc, risk_id = analyze_and_create_report(v, st.session_state['pid'])
                res = send_bundle(bundle)
                
                if res:
                    st.session_state['ai_status'] = status
                    st.session_state['risk_id'] = risk_id
                    
                    if status == "preventive":
                        st.warning(f"預防警報: {desc}")
                        st.session_state['watch_screen'] = "rest"
                    elif status == "emergency":
                        st.error(f"緊急警報: {desc}")
                    else:
                        st.success("數據正常")
                else:
                    st.error("AI 報告上傳失敗")

        st.markdown("---")

        # 醫生操作區
        c_comm, c_ems = st.columns(2)

        # --- 功能 A: 醫生溝通 ---
        with c_comm:
            st.subheader("💬 醫生遠端指令")
            st.caption("透過 CommunicationRequest 傳送訊息")
            
            doc_msg = st.text_input("輸入醫囑:", "請多喝水並保持冷靜。")
            
            if st.button("📤 發送訊息 (Send Msg)"):
                # [修正 3] 接收回傳的 response 物件進行判斷
                req_id, comm_json, res = send_communication_request(
                    st.session_state['pid'], 
                    doc_msg, 
                    priority="routine"
                )
                
                if res and res.status_code in [200, 201]:
                    st.session_state['watch_message'] = doc_msg
                    st.toast("CommunicationRequest 已發送", icon="📨")
                    with st.expander("查看 FHIR 資源 (JSON)"):
                        st.json(comm_json)
                else:
                    st.error("訊息發送失敗")

        # --- 功能 B: 急救處置 ---
        with c_ems:
            st.subheader("🚀 緊急醫療處置")
            st.caption("透過 ServiceRequest 啟動 CPR")
            
            # 只有在緊急狀態才建議按
            is_emergency = st.session_state.get('ai_status') == 'emergency'
            
            # 這裡使用 disabled 參數來控制按鈕可用性，視覺上更直觀
            if st.button("🔴 啟動 CPR 急救", disabled=not is_emergency, help="僅在 AI 判定緊急風險時可用"):
                req_id, sr_json, res = send_service_request(
                    st.session_state['pid'], 
                    st.session_state.get('risk_id')
                )
                
                if res and res.status_code in [200, 201]:
                    st.session_state['watch_screen'] = "cpr"
                    # [優化] 發送緊急處置時，清除可能存在的普通文字訊息，避免干擾
                    st.session_state['watch_message'] = None 
                    
                    st.toast("ServiceRequest 已發送 (Start CPR)", icon="🚑")
                    with st.expander("查看 FHIR 資源 (JSON)"):
                        st.json(sr_json)
                else:
                    st.error("急救請求發送失敗")

    else:
        st.warning("等待數據... 請先至「穿戴裝置」頁面上傳生理數值。")
