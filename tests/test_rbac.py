import pytest
from datetime import date
from tests.conftest import login_as

def test_member_cannot_access_class_schedule(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/classes/schedule')
    assert resp.status_code == 403

def test_member_cannot_access_workouts_management(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/classes/workouts')
    assert resp.status_code == 403

def test_member_cannot_post_pt_session_scheduling(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post('/classes/pt-sessions', data={
        'trainer_id': 1,
        'member_id': 1,
        'session_date': str(date.today()),
        'start_time': '10:00',
        'duration_minutes': 60,
        'focus_area': 'Core'
    })
    assert resp.status_code == 403

def test_member_cannot_access_lockers(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/operations/lockers')
    assert resp.status_code == 403

def test_member_cannot_access_equipment_maintenance(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/equipment/maintenance')
    assert resp.status_code == 403

def test_member_cannot_access_equipment_issues(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/equipment/issues')
    assert resp.status_code == 403

def test_member_cannot_create_diet_plan(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post('/nutrition/diet-plans', data={
        'action': 'create_plan',
        'title': 'Unauthorized Plan',
        'goal': 'Cut',
        'daily_calories': 2000
    })
    assert resp.status_code == 403

def test_member_cannot_access_supplements_management(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/nutrition/supplements')
    assert resp.status_code == 403

def test_member_cannot_access_supplement_sales(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/nutrition/sales')
    assert resp.status_code == 403

def test_member_cannot_access_revenue_analytics_api(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.get('/api/analytics/revenue-monthly')
    assert resp.status_code == 403

def test_member_cannot_add_staff_notes(client):
    login_as(client, 'member', 'Admin@12345')
    resp = client.post('/members/1/notes', data={
        'note_type': 'General',
        'note_text': 'Unauthorized note'
    })
    assert resp.status_code == 403

def test_trainer_cannot_create_invoices(client):
    login_as(client, 'trainer', 'Admin@12345')
    resp = client.get('/finance/invoice-create')
    assert resp.status_code == 403

def test_receptionist_cannot_access_audit_logs(client):
    login_as(client, 'receptionist', 'Admin@12345')
    resp = client.get('/reports/audit-logs')
    assert resp.status_code == 403

def test_manager_can_access_revenue_analytics(client):
    login_as(client, 'manager', 'Admin@12345')
    resp = client.get('/api/analytics/revenue-monthly')
    assert resp.status_code == 200
    assert 'revenue' in resp.get_json()
