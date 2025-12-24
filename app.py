import streamlit as st
import json
import uuid
from datetime import datetime, timezone

# --- 設定網頁配置 ---
st.set_page_config(layout="wide", page_title="h1 健康照護手錶 - FHIR 模擬系統")

# --- 核心功能：FHIR 轉換邏輯 ---
def create_fhir_bundle(heart_rate, lat, lon, patient_name):
    # 生成 UUID
    patient_id = str(uuid.uuid4())
    obs_id = str(uuid.uuid4())
    risk_id = str(uuid.uuid4())
    
    timestamp = datetime.now(timezone.utc).isoformat()

    # 1. Observation (生理數據)
    observation = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4", "display": "Heart rate"}]},
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "valueQuantity": {"value": heart_rate, "unit": "beats/minute", "system": "http://unitsofmeasure.org", "code": "/min"},
        "effectiveDateTime": timestamp
    }

    # 2. RiskAssessment (AI 判定)
    risk_level = "high" if heart_rate > 150 else "low"
    prediction_prob = 0.85 if risk_level == "high" else 0.12
    risk_assessment = {
        "resourceType": "RiskAssessment",
        "id": risk_id,
        "status": "final",
        "subject": {"reference": f"urn:uuid:{patient_id}"},
        "prediction": [{
            "outcome": {"text": "Cardiac Event Risk"},
            "probabilityDecimal": prediction_prob,
            "qualitativeRisk": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/risk-probability", "code": risk_level}]}
        }],
        "basis": [{"reference": f"urn:uuid:{obs_id}"}]
    }

    # 打包成 Bundle
    bundle = {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [
            {"fullUrl": f"urn:uuid:{obs_id}", "resource": observation, "request": {"method": "POST", "url": "Observation"}},
            {"fullUrl": f"urn:uuid:{risk_id}", "resource": risk_assessment, "request": {"method": "POST", "url": "RiskAssessment"}}
        ]
    }
    return bundle, risk_level

# --- 前端介面設計 ---
st.title("🏥 h1 健康照護手錶 - FHIR 互通性演示")
st.markdown("---")

col1, col2 = st.columns([1, 1])

# === 左欄：模擬穿戴裝置 ===
with col1:
    st.header("⌚ 用戶端 (Wearable)")
    st.info("請在此處模擬手錶偵測到的數據")
    
    name = st.text_input("病患姓名", "Wang Xiao-Ming")
    heart_rate = st.slider("❤️ 即時心率 (BPM)", min_value=40, max_value=220, value=75)
    
    st.write("📍 GPS 位置模擬")
    gps_lat = st.number_input("緯度", value=25.0330)
    gps_lon = st.number_input("經度", value=121.5654)

    if heart_rate > 150:
        st.error(f"⚠️ 警告：偵測到異常心率 {heart_rate} BPM")
    else:
        st.success(f"✅ 狀態正常：{heart_rate} BPM")

# === 右欄：FHIR Gateway & 醫院端 ===
with col2:
    st.header("🔗 FHIR Gateway & 醫院端")
    
    bundle_data, risk_level = create_fhir_bundle(heart_rate, gps_lat, gps_lon, name)
    
    st.subheader("🤖 AI Engine 分析")
    if risk_level == "high":
        st.error("🛑 判定結果：高風險 (High Risk) -> 觸發 ServiceRequest (急救)")
        st.metric(label="心臟驟停機率", value="85%", delta="CRITICAL")
    else:
        st.success("🟢 判定結果：低風險 (Low Risk) -> 持續監測")
        st.metric(label="心臟驟停機率", value="12%")

    st.subheader("📄 FHIR JSON Output (標準格式)")
    with st.expander("點擊查看完整的 FHIR Bundle JSON"):
        st.json(bundle_data)

# --- 底部：模擬傳輸按鈕 ---
st.markdown("---")
if st.button("🚀 發送數據至醫院電子病歷系統 (Simulate Upload)", type="primary"):
    with st.spinner('正在透過 FHIR API 傳輸...'):
        import time
        time.sleep(1) 
    st.toast('數據已成功寫入 FHIR Server!', icon='✅')
    if risk_level == "high":
        st.toast('已派遣救護車！', icon='🚑')