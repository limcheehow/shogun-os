---
name: contract
category: connector
setup_time: 0
cost: $0
depends_on: []
---

# Compliance Provider Contract

> **Standard tool names and response shapes for compliance integrations.**
> Covers document signing, policy management, audit trails, and evidence collection.

## Tools

### comp_list_documents

List compliance documents.

**Input:** `{ "search": "string", "status": "string (draft | signed | expired)", "type": "string", "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "limit": 50 }`

**Output:** `{ "documents": [{ "id": "string", "name": "string", "type": "string", "status": "string", "signers": ["string"], "created_date": "YYYY-MM-DD", "completed_date": "YYYY-MM-DD" }], "total": 0 }`

### comp_send_for_signature

Send a document for e-signature.

**Input:** `{ "name": "string (required)", "file_path": "string (required)", "signers": [{ "name": "string", "email": "string", "role": "string (signer | cc)" }], "message": "string", "expires_in_days": 30 }`

**Output:** `{ "id": "string", "status": "sent", "signing_url": "string" }`

### comp_list_policies

List compliance policies.

**Input:** `{ "search": "string", "category": "string", "status": "string (active | draft | archived)", "limit": 50 }`

**Output:** `{ "policies": [{ "id": "string", "name": "string", "category": "string", "version": "string", "status": "string", "effective_date": "YYYY-MM-DD", "review_date": "YYYY-MM-DD", "owner": "string" }], "total": 0 }`

### comp_list_audit_logs

List audit trail entries.

**Input:** `{ "date_from": "YYYY-MM-DD", "date_to": "YYYY-MM-DD", "action": "string", "user": "string", "limit": 50 }`

**Output:** `{ "audit_logs": [{ "id": "string", "timestamp": "ISO 8601", "user": "string", "action": "string", "resource_type": "string", "resource_id": "string", "details": "string" }], "total": 0 }`

### comp_check_compliance

Check compliance status for a specific standard/requirement.

**Input:** `{ "standard": "string (required, e.g. ISO27001, SOC2, GDPR)", "scope": "string" }`

**Output:** `{ "standard": "string", "overall_status": "string (compliant | partial | non_compliant)", "controls": [{ "name": "string", "status": "string", "evidence_count": 0, "last_reviewed": "YYYY-MM-DD" }] }`

## Error Response Shape

All tools return `{"error": "string", "code": "..."}`.

## Provider Requirements

| Tool | Priority |
|------|----------|
| `comp_list_documents` | P0 |
| `comp_send_for_signature` | P0 |
| `comp_list_policies` | P1 |
| `comp_list_audit_logs` | P1 |
| `comp_check_compliance` | P2 |