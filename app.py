import streamlit as st
import requests
import uuid
import time
from datetime import datetime, timezone

# --- 匯入模組 (請確保您的資料夾中有這兩個檔案) ---
try:
    from fhir_gateway import create_raw_data_bundle
    from ai_engine import analyze_and_create_report
except ImportError:
    st.error("❌ 找不到必要的模組 (fhir_gateway.py 或 ai_engine.py)。請確認檔案是否在同一目錄下。")
    st.stop()

st.set_page_config(layout="wide", page_title="h1 雙軌醫療系統 (FHIR 標準版)")

# [修正 1] 改用 HAPI FHIR R4 公用伺服器 (比 fire.ly 穩定且權限較寬鬆)
FHIR_SERVER_URL = "https://hapi.fhir.org/baseR4"

# --- 初始化 Session State ---
if 'watch_screen' not in st.session_state: st.session_state['watch_screen'] = "normal"
if 'watch_message' not in st.session_state: st.session_state['watch_message'] = None 
if 'has_data' not in st.session_state: st.session_state['has_data'] = False
if 'vitals' not in st.session_state: st.session_state['vitals'] = {}
if 'pid' not in st.session_state: st.session_state['pid'] = None
if 'ai_status' not in st.session_state: st.session_state['ai_status'] = "unknown"
if 'risk_id' not in st.session_state: st.session_state['risk_id'] = None

# --- Helper Functions ---

def send_bundle(bundle):
    headers = {"Content-Type": "application/fhir+json"}
    
    # [修正 2] 強制將 Bundle 類型設為 transaction，這是根目錄寫入的標準格式
    if bundle.get("resourceType") == "Bundle":
        bundle["type"] = "transaction"
        # 確保 bundle 內的每個 entry 都有 request 方法 (如果是 create_raw_data_bundle 產生的，通常需要檢查這裡)
        # 這裡假設您的 fhir_gateway 已經有處理 entry.request (POST/PUT)
    
    try:
        # 設定 timeout 避免卡死
        response = requests.post(FHIR_SERVER_URL, json=bundle, headers=headers, timeout=20)
        
        # [修正 3] 詳細的錯誤處理
        if response.status_code not in [200, 201]:
            st.error(f"上傳失敗 (HTTP {response.status_code})")
            with st.expander("🔍 查看伺服器錯誤詳情 (Server Response)"):
                st.text(response.text)  # 印出伺服器具體報錯原因
            return None
            
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"連線錯誤: {e}")
        return None

def send_service_request(patient_id, risk_id):
    """發送醫療處置請求 (Start CPR)"""
    req_id = str(uuid.uuid4())
    safe_risk_id = risk_id if risk_id else "unknown"
    
    sr = {
        "resourceType": "ServiceRequest",
        "id": req_id,
        "status": "active",
        "intent": "order",
        "priority": "stat",
        "code": {"coding": [{"system": "http://snomed.info/sct", "code": "40617009", "display": "Start CPR"}]},
        "subject": {"reference": f"Patient/{patient_id}"},
        "reasonReference": [{"reference": f"RiskAssessment/{safe_risk_id}"}],
        # 為了 transaction bundle，通常需要一個 request 欄位，但在單獨 POST resource 時不需要
        # 如果是單獨 POST SR，Server URL 應該要加上 /ServiceRequest，但這裡我們用 Bundle 包裝較好
        # 為了簡化，我們這裡把它包成一個小 Bundle 傳送
    }
    
    # 包裝成 Transaction Bundle 發送
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [{
            "resource": sr,
            "request": {"method": "POST", "url": "ServiceRequest"}
        }]
    }
    res = send_bundle(bundle)
    return req_id, sr, res

def send_communication
