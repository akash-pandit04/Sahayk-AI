def test_create_category(client, admin_token_headers):
    response = client.post("/api/v1/admin/categories", headers=admin_token_headers, json={
        "name": "Health",
        "description": "Health related schemes"
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Health"
    return data["id"]

def test_create_scheme(client, admin_token_headers):
    cat_id = test_create_category(client, admin_token_headers)
    
    response = client.post("/api/v1/admin/schemes", headers=admin_token_headers, json={
        "name": "Test Scheme",
        "short_description": "Short desc",
        "detailed_description": "Detailed desc",
        "category_ids": [cat_id]
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Test Scheme"
    assert data["status"] == "DRAFT"
    
def test_publish_scheme_fails_without_requirements(client, admin_token_headers):
    # Create scheme
    r = client.post("/api/v1/admin/schemes", headers=admin_token_headers, json={
        "name": "Incomplete Scheme",
        "short_description": "Short desc",
        "detailed_description": "Detailed desc"
    })
    scheme_id = r.json()["data"]["id"]
    
    # Try publishing immediately
    r_patch = client.patch(f"/api/v1/admin/schemes/{scheme_id}", headers=admin_token_headers, json={
        "status": "PUBLISHED"
    })
    assert r_patch.status_code == 400
    assert "source" in r_patch.json()["detail"] if "detail" in r_patch.json() else "source" in r_patch.json().get("error", {}).get("message", "")

def test_publish_scheme_success_with_requirements(client, admin_token_headers):
    r = client.post("/api/v1/admin/schemes", headers=admin_token_headers, json={
        "name": "Complete Scheme",
        "short_description": "Short desc",
        "detailed_description": "Detailed desc"
    })
    scheme_id = r.json()["data"]["id"]
    
    # Add source
    client.post(f"/api/v1/admin/schemes/{scheme_id}/sources", headers=admin_token_headers, json={
        "title": "Gov URL",
        "url": "https://gov.in",
        "source_type": "OFFICIAL_GOVERNMENT",
        "verification_status": "VERIFIED"
    })
    
    # Add benefit
    client.post(f"/api/v1/admin/schemes/{scheme_id}/benefits", headers=admin_token_headers, json={
        "benefit_type": "FINANCIAL",
        "description": "5000 INR"
    })
    
    # Add rule
    client.post(f"/api/v1/admin/schemes/{scheme_id}/rules", headers=admin_token_headers, json={
        "field": "age",
        "operator": "GREATER_THAN_EQUALS",
        "value": "60",
        "data_type": "NUMBER"
    })
    
    # Publish
    r_patch = client.patch(f"/api/v1/admin/schemes/{scheme_id}", headers=admin_token_headers, json={
        "status": "PUBLISHED"
    })
    assert r_patch.status_code == 200
    assert r_patch.json()["data"]["status"] == "PUBLISHED"

def test_audit_logs(client, admin_token_headers):
    # Trigger an audit log
    client.post("/api/v1/admin/categories", headers=admin_token_headers, json={
        "name": "Audit Test",
        "description": "Desc"
    })
    r = client.get("/api/v1/admin/audit-logs", headers=admin_token_headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["total"] > 0
    
    # Check return not none warning
    return None
