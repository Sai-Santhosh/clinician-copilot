"""API Test Script for Clinician Copilot"""
import requests
import json

BASE = 'http://localhost:8000/api/v1'

def test_api():
    # Test 1: Health check
    print('=== Health Check ===')
    r = requests.get(f'{BASE}/healthz')
    print(f'Status: {r.status_code}, Response: {r.json()}')

    # Test 2: Login as admin
    print('\n=== Login as Admin ===')
    r = requests.post(f'{BASE}/auth/login', json={
        'email': 'admin@example.com',
        'password': 'admin123!'
    })
    print(f'Status: {r.status_code}')
    if r.status_code != 200:
        print(f'Login failed: {r.text}')
        return
    
    login_data = r.json()
    token = login_data['access_token']
    user = login_data['user']
    print(f"User: {user['email']}, Role: {user['role']}")

    headers = {'Authorization': f'Bearer {token}'}

    # Test 3: Get current user
    print('\n=== Get Current User ===')
    r = requests.get(f'{BASE}/auth/me', headers=headers)
    print(f'Status: {r.status_code}')
    print(f"Current user: {r.json()['email']}")

    # Test 4: Create a patient
    print('\n=== Create Patient ===')
    r = requests.post(f'{BASE}/patients', headers=headers, json={
        'name': 'John Doe',
        'dob': '1985-03-15',
        'external_id': 'PAT001'
    })
    print(f'Status: {r.status_code}')
    if r.status_code == 201:
        patient = r.json()
        print(f"Created patient: {patient['name']} (ID: {patient['id']})")
    elif r.status_code in [400, 409]:
        # Patient might already exist, list patients instead
        print('Patient may already exist, listing patients...')
        r = requests.get(f'{BASE}/patients', headers=headers)
        patients = r.json()
        patient = patients[0] if patients else None
        if patient:
            print(f"Using existing patient: {patient['name']} (ID: {patient['id']})")
    else:
        print(f'Failed: {r.text}')
        return

    # Test 5: List patients
    print('\n=== List Patients ===')
    r = requests.get(f'{BASE}/patients', headers=headers)
    print(f'Status: {r.status_code}, Count: {len(r.json())}')
    for p in r.json():
        print(f"  - {p['name']} (ID: {p['id']})")

    # Test 6: Create a session with transcript
    print('\n=== Create Session ===')
    transcript = """
Patient is a 35-year-old male presenting with symptoms of depression for the past 3 months. 
He reports feeling sad most of the day, nearly every day. Sleep has been poor - he wakes up at 3 AM and cannot fall back asleep. 
Appetite is decreased with 10 lb weight loss. He denies suicidal ideation but admits to feeling hopeless. 
He has a history of one previous depressive episode 5 years ago which responded well to sertraline.
Patient works as an accountant and reports increased work stress. He is married with two children.
No current medications. No alcohol or substance use.
Mental status exam shows psychomotor retardation, flat affect, and poor eye contact.
"""
    r = requests.post(f"{BASE}/sessions/patients/{patient['id']}/sessions", headers=headers, json={
        'transcript': transcript
    })
    print(f'Status: {r.status_code}')
    if r.status_code == 201:
        session = r.json()
        print(f"Created session ID: {session['id']}, Transcript length: {session['transcript_length']}")
    else:
        print(f'Failed: {r.text}')
        return

    # Test 7: Get session details
    print('\n=== Get Session Details ===')
    r = requests.get(f"{BASE}/sessions/{session['id']}", headers=headers)
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        sess_data = r.json()
        print(f"Session has AI suggestions: {sess_data.get('has_ai_suggestions', False)}")
    else:
        print(f'Response: {r.json()}')

    # Test 8: Generate AI suggestions (this calls Gemini!)
    print('\n=== Generate AI Suggestions (calling Gemini) ===')
    r = requests.post(
        f"{BASE}/sessions/{session['id']}/generate", 
        headers=headers,
        json={"prompt_version": "v1", "mode": "full"}
    )
    print(f'Status: {r.status_code}')
    if r.status_code == 201:
        ai_data = r.json()
        print('AI Suggestions generated successfully!')
        print(f"\n--- SOAP Note ---")
        soap = ai_data.get('soap_note', {})
        print(f"Subjective: {soap.get('subjective', 'N/A')[:100]}...")
        print(f"Objective: {soap.get('objective', 'N/A')[:100]}...")
        print(f"Assessment: {soap.get('assessment', 'N/A')[:100]}...")
        print(f"Plan: {soap.get('plan', 'N/A')[:100]}...")
        
        print(f"\n--- Diagnoses ---")
        for dx in ai_data.get('diagnoses', [])[:3]:
            print(f"  - {dx.get('name')} (ICD: {dx.get('icd10_code')}, confidence: {dx.get('confidence')})")
        
        print(f"\n--- Medications ---")
        for med in ai_data.get('medications', [])[:3]:
            print(f"  - {med.get('name')}: {med.get('patient_education', 'N/A')[:50]}...")
        
        print(f"\n--- Safety Plan ---")
        safety = ai_data.get('safety_plan', {})
        print(f"Risk Level: {safety.get('risk_level')}")
        print(f"Warning Signs: {safety.get('warning_signs', [])[:2]}")
        
        print(f"\n--- Citations ---")
        for cite in ai_data.get('citations', [])[:3]:
            print(f"  - {cite}")
    else:
        print(f'Failed: {r.text}')

    # Test 9: List audit logs (admin only)
    print('\n=== Audit Logs ===')
    r = requests.get(f'{BASE}/audit', headers=headers)
    print(f'Status: {r.status_code}')
    if r.status_code == 200:
        logs = r.json()
        print(f'Total audit logs: {len(logs)}')
        for log in logs[:5]:
            print(f"  - {log['action']} by user {log['user_id']} at {log['created_at']}")

    # Test 10: Metrics endpoint
    print('\n=== Prometheus Metrics ===')
    r = requests.get('http://localhost:8000/metrics')
    print(f'Status: {r.status_code}')
    print(f'Metrics available: {len(r.text)} bytes')

    print('\n' + '='*50)
    print('ALL TESTS COMPLETED!')
    print('='*50)
    print('\nAPI Documentation available at: http://localhost:8000/docs')
    print('Alternative docs at: http://localhost:8000/redoc')

if __name__ == '__main__':
    test_api()
