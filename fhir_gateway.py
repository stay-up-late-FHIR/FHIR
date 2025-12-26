import uuid
import json
from datetime import datetime, timezone

# 模擬的組織資訊 (幫你設定好了)
ORG_ID = "org-h1-hospital"
ORG_NAME = "H1 Smart Hospital (H1 智慧醫院)"

def create_raw_data_bundle(user_id, user_name, hr, spo2, hrv, sys_bp, dia_bp, resp, sleep, lat, lon):
    
    # 1. 生成 ID
    patient_uuid = str(uuid.uuid4())
    obs_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # --- 2. 建立 Organization (醫院/組織) ---
    # 這是為了滿足你 "PHR 紀錄與組織 ID" 的需求
    organization = {
        "resourceType": "Organization",
        "id": ORG_ID,
        "name": ORG_NAME,
        "type": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/organization-type", "code": "prov", "display": "Healthcare Provider"}]}]
    }

    # --- 3. 建立 Patient (病人) ---
    patient = {
        "resourceType": "Patient",
        "id": patient_uuid,
        "identifier": [{"system": "http://hospital.org/id", "value": user_id}],
        "name": [{"family": "User", "given": [user_name]}],
        "gender": "unknown",
        "managingOrganization": {"reference": f"Organization/{ORG_ID}"} # 綁定組織
    }

    # --- 4. 建立 Observation (生理數據) ---
    # 這裡只保留你需要的：HR, SpO2, HRV, 以及背景數據(血壓,呼吸,睡眠)
    
    observations = []
    def make_obs(code, display, value, unit, unit_code):
        return {
            "resourceType": "Observation",
            "id": str(uuid.uuid4()),
            "status": "final",
            "code": {"coding": [{"system": "http://loinc.org", "code": code, "display": display}]},
            "subject": {"reference": f"Patient/{patient_uuid}"},
            "performer": [{"reference": f"Organization/{ORG_ID}"}], # 紀錄是哪個組織測量的
            "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": unit_code},
            "effectiveDateTime": timestamp
        }

    # 顯示在手錶的三大數據
    observations.append(make_obs("8867-4", "Heart rate", hr, "beats/minute", "/min"))
    observations.append(make_obs("2708-6", "Oxygen saturation", spo2, "%", "%"))
    observations.append(make_obs("80404-7", "Heart rate variability (SDNN)", hrv, "ms", "ms"))
    
    # 背景數據 (AI 判斷用，但不一定顯示)
    observations.append(make_obs("9383-2", "Sleep duration", sleep, "h", "h"))
    observations.append(make_obs("9279-1", "Respiratory rate", resp, "breaths/minute", "/min"))

    # 血壓 Panel + GPS
    bp_obs = {
        "resourceType": "Observation",
        "id": obs_id,
        "status": "final",
        "code": {"coding": [{"system": "http://loinc.org", "code": "85354-9", "display": "Blood pressure panel"}]},
        "subject": {"reference": f"Patient/{patient_uuid}"},
        "effectiveDateTime": timestamp,
        "component": [
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8480-6", "display": "Systolic"}]}, "valueQuantity": {"value": sys_bp, "unit": "mmHg"}},
            {"code": {"coding": [{"system": "http://loinc.org", "code": "8462-4", "display": "Diastolic"}]}, "valueQuantity": {"value": dia_bp, "unit": "mmHg"}}
        ],
        "extension": [{"url": "http://hl7.org/fhir/StructureDefinition/geolocation", "valueAddress": {"text": f"{lat},{lon}"}}]
    }
    observations.append(bp_obs)

    # --- 5. 打包 ---
    entries = []
    # 確保組織存在
    entries.append({"fullUrl": f"urn:uuid:{ORG_ID}", "resource": organization, "request": {"method": "PUT", "url": f"Organization/{ORG_ID}"}})
    # 病人
    entries.append({"fullUrl": f"urn:uuid:{patient_uuid}", "resource": patient, "request": {"method": "PUT", "url": f"Patient/{patient_uuid}"}})
    # 數據
    for obs in observations:
        entries.append({"fullUrl": f"urn:uuid:{obs['id']}", "resource": obs, "request": {"method": "POST", "url": "Observation"}})

    bundle = {"resourceType": "Bundle", "type": "transaction", "entry": entries}
    return bundle, patient_uuid
