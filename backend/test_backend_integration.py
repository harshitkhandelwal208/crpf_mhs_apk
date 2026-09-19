"""
Automated Integration Test for CRPF MHS Backend
Validates Android APK and Web API contracts, AI pipeline, RAG retrieval,
and risk engine alert escalation.
"""

import sys
import os
import io

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_full_integration():
    print("\n" + "="*60)
    print(" [START] STARTING CRPF MHS BACKEND INTEGRATION TEST")
    print("="*60)

    # 1. Health Check
    res = client.get("/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    assert res.json()["status"] == "healthy"
    print("[OK] [1/14] Health Check Passed")

    # 2. Login as PERSONNEL (Android contract)
    login_payload = {
        "username": "personnel1@sentinel.mil",
        "password": "sentinel-pers-2024"
    }
    # Test /api/auth/login
    res_api = client.post("/api/auth/login", json=login_payload)
    assert res_api.status_code == 200, f"Login on /api failed: {res_api.text}"
    tokens = res_api.json()
    assert "access_token" in tokens and "refresh_token" in tokens
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    # Test /api/v1/auth/login
    res_v1 = client.post("/api/v1/auth/login", json=login_payload)
    assert res_v1.status_code == 200, f"Login on /api/v1 failed: {res_v1.text}"
    print("[OK] [2/14] Dual-Route Auth Login Passed (/api and /api/v1)")

    headers = {"Authorization": f"Bearer {access_token}"}

    # 3. Token Refresh (Android TokenAuthenticator contract)
    res_ref = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert res_ref.status_code == 200, f"Refresh failed: {res_ref.text}"
    ref_tokens = res_ref.json()
    assert "access_token" in ref_tokens and "refresh_token" in ref_tokens
    # Update access token
    headers = {"Authorization": f"Bearer {ref_tokens['access_token']}"}
    print("[OK] [3/14] Auth Token Refresh Passed")

    # 4. User Profile (Android UserResponse contract: id, email, name, role='PERSONNEL', onboarding_complete)
    res_user = client.get("/api/users/me", headers=headers)
    assert res_user.status_code == 200, f"User profile failed: {res_user.text}"
    user_data = res_user.json()
    assert user_data["role"] == "PERSONNEL", f"Role mismatch: {user_data['role']}"
    assert user_data["name"] == "Sgt. Mike Johnson"
    assert user_data["email"] == "personnel1@sentinel.mil"
    assert user_data["onboarding_complete"] is True
    print(f"[OK] [4/14] Android User Profile Passed: {user_data['name']} ({user_data['role']})")

    # 5. AI Companion Chat - Positive / Joy Turn
    chat_payload_joy = {
        "message": "Good morning companion! The platoon completed our tactical march and our team morale is high today."
    }
    res_chat_joy = client.post("/api/ai/chat", json=chat_payload_joy, headers=headers)
    assert res_chat_joy.status_code == 200, f"Chat joy failed: {res_chat_joy.text}"
    chat_res_joy = res_chat_joy.json()
    assert "conversation_id" in chat_res_joy
    assert chat_res_joy["support_escalation"] is False
    assert chat_res_joy["morale_score"] >= 60
    conv_id = chat_res_joy["conversation_id"]
    print(f"[OK] [5/14] AI Chat (Joy) Passed. Morale: {chat_res_joy['morale_score']}/100, Escalation: {chat_res_joy['support_escalation']}")

    # 6. AI Companion Chat - RAG Skill Retrieval & Operational Triage Turn
    chat_payload_triage = {
        "conversation_id": conv_id,
        "message": "I've been on night shift duty for 4 days straight. Cannot sleep and feeling completely exhausted."
    }
    res_chat_triage = client.post("/api/ai/chat", json=chat_payload_triage, headers=headers)
    assert res_chat_triage.status_code == 200, f"Chat triage failed: {res_chat_triage.text}"
    chat_res_triage = res_chat_triage.json()
    assert chat_res_triage["support_escalation"] is False
    assert chat_res_triage["message"]["content"]
    print(f"[OK] [6/14] AI Chat (RAG Triage) Passed. Morale: {chat_res_triage['morale_score']}/100")
    print(f"   Companion Response Snippet: {chat_res_triage['message']['content'][:100]}...")

    # 7. AI Companion Chat - Crisis Safety Net & Escalation
    chat_payload_crisis = {
        "conversation_id": conv_id,
        "message": "I can't take this anymore, I want to end it all and kill myself."
    }
    res_chat_crisis = client.post("/api/ai/chat", json=chat_payload_crisis, headers=headers)
    assert res_chat_crisis.status_code == 200, f"Chat crisis failed: {res_chat_crisis.text}"
    chat_res_crisis = res_chat_crisis.json()
    assert chat_res_crisis["support_escalation"] is True, "Crisis MUST trigger support_escalation"
    assert chat_res_crisis["risk_flag"] is True
    print(f"[OK] [7/14] AI Chat (Crisis Safety Net) Passed. Escalation Triggered: {chat_res_crisis['support_escalation']}")

    # 8. List & Detail AI Conversations
    res_convs = client.get("/api/ai/conversations", headers=headers)
    assert res_convs.status_code == 200
    conv_list = res_convs.json()
    assert len(conv_list) >= 1
    res_conv_detail = client.get(f"/api/ai/conversations/{conv_id}", headers=headers)
    assert res_conv_detail.status_code == 200
    detail_data = res_conv_detail.json()
    assert len(detail_data["messages"]) >= 6  # 3 user messages + 3 assistant responses
    print(f"[OK] [8/14] AI Conversations History Passed: {len(detail_data['messages'])} turns retrieved")

    # 9. Journal Submission (Android JournalResponse contract: { "journal": { "id", "mood", "content", "status", "created_at" } })
    journal_payload = {
        "content": "Sustained deployment is wearing down our squad. Several personnel having difficulty sleeping.",
        "mood": "stressed",
        "status": "SUBMITTED"
    }
    res_journal = client.post("/api/journals", json=journal_payload, headers=headers)
    assert res_journal.status_code == 201, f"Journal submission failed: {res_journal.text}"
    j_data = res_journal.json()
    assert "journal" in j_data, f"Missing 'journal' key in response: {j_data}"
    journal_item = j_data["journal"]
    assert journal_item["mood"] == "stressed"
    assert journal_item["status"] == "SUBMITTED"
    assert "id" in journal_item and "created_at" in journal_item
    print(f"[OK] [9/14] Android Journal Submission Passed. ID: {journal_item['id']}")

    # 10. List My Journals
    res_my_journals = client.get("/api/journals", headers=headers)
    assert res_my_journals.status_code == 200
    assert len(res_my_journals.json()["journals"]) >= 1
    print(f"[OK] [10/14] List Journals Passed: {len(res_my_journals.json()['journals'])} entries")

    # 11. Voice Audio Transcription (Multipart Audio Upload)
    dummy_wav = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00")
    files = {"audio": ("reflection.wav", dummy_wav, "audio/wav")}
    res_voice = client.post("/api/voice/transcribe", files=files, headers=headers)
    assert res_voice.status_code == 200, f"Voice transcribe failed: {res_voice.text}"
    voice_data = res_voice.json()
    assert "transcript" in voice_data
    assert voice_data["requires_review"] is True
    print(f"[OK] [11/14] Voice STT Transcription Passed: \"{voice_data['transcript']}\"")

    # 12. Support Request (Android SupportResponse contract: { "id", "status" })
    support_payload = {
        "type": "urgent",
        "message": "Requesting confidential discussion regarding family medical emergency and transfer options."
    }
    res_support = client.post("/api/support/request", json=support_payload, headers=headers)
    assert res_support.status_code == 201, f"Support request failed: {res_support.text}"
    sup_data = res_support.json()
    assert "id" in sup_data and sup_data["status"] == "PENDING"
    print(f"[OK] [12/14] Support Request Passed. ID: {sup_data['id']}, Status: {sup_data['status']}")

    # 13. Emergency Contacts & Resources
    res_contacts = client.get("/api/emergency-contacts")
    assert res_contacts.status_code == 200
    assert len(res_contacts.json()) >= 4
    res_resources = client.get("/api/resources")
    assert res_resources.status_code == 200
    assert len(res_resources.json()) >= 3
    print(f"[OK] [13/14] Emergency Contacts ({len(res_contacts.json())}) & Resources ({len(res_resources.json())}) Passed")

    # 14. Admin Verification & Automated Alert Escalation
    # Login as admin to verify operational alerting generated by personnel crisis turn
    admin_login = {
        "username": "admin@sentinel.mil",
        "password": "sentinel-admin-2024"
    }
    res_admin = client.post("/api/auth/login", json=admin_login)
    assert res_admin.status_code == 200
    admin_headers = {"Authorization": f"Bearer {res_admin.json()['access_token']}"}

    res_alerts = client.get("/api/alerts", headers=admin_headers)
    assert res_alerts.status_code == 200
    alerts_data = res_alerts.json()
    # Check that AI_FLAGGED alert exists
    ai_flagged_alerts = [a for a in alerts_data["items"] if a["type"] == "AI_FLAGGED"]
    assert len(ai_flagged_alerts) >= 1, "Automated AI_FLAGGED alert MUST be present after crisis message"
    print(f"[OK] [14/14] Admin & Risk Escalation Passed: Verified {len(ai_flagged_alerts)} automated welfare alerts generated")

    print("\n" + "="*60)
    print(" [SUCCESS] ALL 14 BACKEND INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_full_integration()
