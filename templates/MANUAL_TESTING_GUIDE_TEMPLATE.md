# Manual Testing Guide: {{ feature_name }}

**Target Branch:** `{{ branch_name }}`  
**Environment:** Local Development / Staging  
**Author:** Automated Agentic Quality Assurance  
**Companion PR:** #{{ pr_number }}  

---

## 1. Prerequisites & Environment Setup

1. **Backend Database:**
   ```bash
   cd code/backend
   dotnet ef database update
   ```
2. **Backend Server:**
   ```bash
   dotnet run --project Presentation/HomeCare.Api
   ```
3. **Frontend Server:**
   ```bash
   cd code/frontend
   npm install
   npm run dev
   ```

---

## 2. Test User Accounts & Tenants

| Persona | Tenant ID | User / Email | Role / Permissions |
| ------- | --------- | ------------ | ------------------ |
| Vendor Admin | `tenant-001` | vendor.admin@test.local | Orders.Manage, Fulfill.Write |
| Vendor Dispatcher | `tenant-001` | vendor.logistics@test.local | Logistics.Write |
| Cross-Tenant Attacker | `tenant-002` | external.vendor@test.local | Isolation validation |

---

## 3. Step-by-Step Test Scenarios

### Scenario 1: Happy Path End-to-End Flow
1. Navigate to `{{ primary_frontend_route }}`.
2. Verify summary metrics header displays correct counts.
3. Select an item in `Pending` status and click **Accept**.
4. Verify status transitions immediately to `In Progress`.
5. Enter shipment/dispatch details (Carrier, Waybill number).
6. Submit form and verify successful persistence and audit log entry.

### Scenario 2: Validation & Negative Constraints
1. Attempt submission with missing mandatory fields (e.g. tracking number).
2. Verify frontend displays inline validation error from schema.
3. Attempt state transition out of order (e.g. mark completed before dispatch).
4. Verify backend returns RFC 7807 Bad Request with informative detail message.

### Scenario 3: Multi-Tenant Data Isolation Test
1. Log in as user in `tenant-002`.
2. Attempt direct API request `GET /api/{{ api_resource }}/{id}` for an order belonging to `tenant-001`.
3. Verify response is `404 Not Found` or `403 Forbidden` (never data leak).

---

## 4. Verification Checklist

- [ ] UI layout responsive across Desktop (1920x1080) and Mobile (375x812)
- [ ] Accessibility: Keyboard navigable, color contrast WCAG AA compliant
- [ ] No browser console errors during navigation
- [ ] No PII exposed in network request/response payloads or server logs
