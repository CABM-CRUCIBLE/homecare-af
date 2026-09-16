# Orders & Services Fulfillment Workflow — Documentation Index

**Feature:** Vendor "Orders & Services Fulfillment" dashboard (Device Purchases / Device Rentals / Nurse Provisioning)
**Owner:** Solution Architecture
**Status:** Proposed — awaiting sign-off
**Date:** 2026-09-14

---

## 1. Reading Order

| # | Document | Purpose |
| --- | --- | --- |
| 1 | [STRATEGY-Order-Service-Request-Fulfillment.md](STRATEGY-Order-Service-Request-Fulfillment.md) | Requirements (FR / NFR / Constraints), current-state gap analysis, use-case map, sequence diagrams, C4 Container & Component views |
| 2 | [TACTICAL-PLAN-Order-Service-Request-Fulfillment.md](TACTICAL-PLAN-Order-Service-Request-Fulfillment.md) | ERD, physical schema, migrations, high-level component design, API surface, UI composition, work-package breakdown, test strategy |
| 3 | [AGENTIC-PROMPTS-Order-Service-Request-Fulfillment.md](AGENTIC-PROMPTS-Order-Service-Request-Fulfillment.md) | Self-contained, parallelisable implementation prompts (one per work package) |
| 4 | ADR 015 – 020 (below) | Load-bearing decisions with rationale and consequences |

## 2. Architecture Decision Records

| ADR | Title | Decides |
| --- | --- | --- |
| [ADR 015](ADR%20015%20-%20Fulfillment%20State%20Ownership%20and%20Satellite%20Aggregates.md) | Fulfillment State Ownership and Satellite Aggregates | No parallel order table; commercial vs. logistics state separation |
| [ADR 016](ADR%20016%20-%20Fail-Closed%20Vendor%20Tenant%20Identity%20Resolution.md) | Fail-Closed Vendor Tenant Identity Resolution | Tenant boundary must deny by default; audited admin impersonation |
| [ADR 017](ADR%20017%20-%20Fulfillment%20Type%20Derivation%20and%20Marketplace%20Identity%20Reconciliation.md) | Fulfillment Type Derivation and Marketplace Identity Reconciliation | Purchase vs. rental intent threaded from catalog; `MarketplaceVendor` ↔ `Vendor` reconciliation |
| [ADR 018](ADR%20018%20-%20Serial%20Number%20Allocation%20Concurrency%20Control.md) | Serial Number Allocation Concurrency Control | Optimistic concurrency + single-column allocation invariant |
| [ADR 019](ADR%20019%20-%20Server-First%20Fulfillment%20UI%20with%20URL-Driven%20View%20State.md) | Server-First Fulfillment UI with URL-Driven View State | RSC route segments, client islands, grid/card toggle in the URL |
| [ADR 020](ADR%20020%20-%20Vendor%20Data%20Minimisation%20for%20Buyer%20Information.md) | Vendor Data Minimisation for Buyer Information | Order-time delivery snapshot; no clinical data in vendor DTOs |

## 3. Reference Screens

Located in [Resources/](Resources):

| File | Screen |
| --- | --- |
| `Device_Purchases.jpg` | Tab A — Orders & Services Fulfillment / Device Purchases |
| `Shipment_Registry.jpg` | Tab A detail — Shipment Registry |
| `Device_Rentals.jpg` | Tab B — Device Rentals |
| `Deployment_Rental_Setup.jpg` | Tab B detail — Deploy Rental Setup |

## 4. Relationship to Prior Work

The folder `Architecture/REJECTED - Order_Service_Request_Fulfillment_Workflow/` contains a
superseded proposal and the architecture review (`Architecture_Review_Findings.md`) that
rejected it. **That review is the primary input to this document set.** Every blocking and
critical finding is either resolved here or explicitly descoped:

| Finding | Disposition in this design |
| --- | --- |
| F1 — Marketplace creates vendor orders under the wrong tenant identity | Resolved — WP0, [ADR 017](ADR%20017%20-%20Fulfillment%20Type%20Derivation%20and%20Marketplace%20Identity%20Reconciliation.md) |
| F2 — Tenant isolation falls back to trusting a user ID | Resolved — WP0, [ADR 016](ADR%20016%20-%20Fail-Closed%20Vendor%20Tenant%20Identity%20Resolution.md) |
| F3 — Telemetry design has no join path | Descoped — IoMT telemetry is explicitly out of scope for this release |
| F4 — Caregiver visit logs on a vendor policy | Descoped — Tab C ships as an empty placeholder |
| F5 — Two competing sources of truth for order state | Resolved by elimination — [ADR 015](ADR%20015%20-%20Fulfillment%20State%20Ownership%20and%20Satellite%20Aggregates.md) removes the duplicate table rather than reconciling it |
| F6 — Strategy assumed a non-existent event backbone | Resolved — all diagrams depict in-process synchronous calls; no outbox is claimed |
| F7 — No ingress path for carrier callbacks | Descoped — vendor-entered logistics status only; schema is forward-compatible |
| F8 — Concurrency gaps on serial allocation and status transitions | Resolved — [ADR 018](ADR%20018%20-%20Serial%20Number%20Allocation%20Concurrency%20Control.md) |
| F9 — `OrderType` hardcoded; `DevicePurchase` missing | Resolved — WP0, [ADR 017](ADR%20017%20-%20Fulfillment%20Type%20Derivation%20and%20Marketplace%20Identity%20Reconciliation.md) |
| F10 — PHI minimisation asserted but not designed | Resolved — [ADR 020](ADR%20020%20-%20Vendor%20Data%20Minimisation%20for%20Buyer%20Information.md) |
| M1 — No payment linkage on the order aggregate | Resolved — `VendorOrder.PaymentId`, derived verification status |
| M2 — Shared primary key coupling | Resolved — `VendorOrder.MarketplaceOrderId` replaces the shared PK |
| M3 — Frontend anti-pattern endorsed | Resolved — [ADR 019](ADR%20019%20-%20Server-First%20Fulfillment%20UI%20with%20URL-Driven%20View%20State.md); mock fallbacks banned |
| M4 — Telemetry is a static column | Descoped with F3 |
| M5 — SQL Server type in an Npgsql migration | Tracked as a prerequisite chore in WP0 |
| M6 — Status values remain magic strings | Resolved — constant classes plus DB `CHECK` constraints |
| M7 — No backfill story | Resolved — WP0 defines backfill and a reconciliation report |

> Note: the ADR numbered 015 inside the `REJECTED` folder is **withdrawn**. The ADR 015 in
> this folder is the active record and reverses its Decision 8.

## 5. Open Questions

Four questions — buyer model, mixed baskets, the meaning of "Pending Verification", and carrier
integration — were **answered by the product owner on 2026-09-14** and are recorded as binding
decisions in [STRATEGY §12.1](STRATEGY-Order-Service-Request-Fulfillment.md#121-resolved). None changed the schema or the API surface.

Six lower-impact questions remain outstanding in [STRATEGY §12.2](STRATEGY-Order-Service-Request-Fulfillment.md#122-outstanding); each has a
stated working assumption, and answers are required before WP1 begins.
