# ADR 021 — Vendor Payouts & Accounting Architecture

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-09-15 |
| **Deciders** | Senior Solution Architect, Backend Lead, Frontend Lead, Finance Operations, Security & Compliance |
| **Supersedes** | — |
| **Superseded by** | — |
| **Related** | ADR 004 (Data Access), ADR 005 (Compliance & Audit), ADR 006 (Payment Gateway), ADR 008 (Marketplace), ADR 009 (Resend Email), ADR 011 (Contract Signature & Archival), ADR 012 (Vendor Dashboard), ADR 016 (Fail-Closed Vendor Tenant Identity), ADR 019 (Server-First URL-Driven UI), ADR 020 (Vendor Data Minimisation) |
| **Scope** | `Architecture/Vendor_Payouts_Accounting_Workflow/` — Strategy & Tactical Plan |

---

## Context

The Curetor Marketplace charges vendors a contractual commission (`IndividualVendorContract.CommissionPct`) on every fulfilled order and owes them the net remainder. Today the platform can *describe* that obligation — `VendorTransaction` records the per-order gross/commission/net split, `VendorPayout` records a period settlement header, and `VendorFinanceController` exposes list/summary/detail endpoints — but it cannot *discharge* it. Specifically:

- There is **no banking instrument**: no vendor bank account entity, no verification, no destination for funds.
- There is **no schedule**: disbursement cadence, minimum thresholds, and automation are unmodelled.
- `TriggerDisbursementCommandHandler` creates a `VendorPayout` with **zero amounts**, never calls a payment provider, and immediately reports `Processing` — a placeholder, not a settlement.
- There are **no statutory artefacts**: GST platform-fee invoices and TDS Form 16A certificates (mandatory for Indian marketplace operators under Sec. 194-O) do not exist.
- There is **no reconciliation or ERP export**: `ExportTransactionLedgerQuery` produces a synchronous CSV only; no PDF, no XML, no retention, no match-rate reporting.
- The vendor-facing `/vendor/payouts` page renders **hard-coded mock arrays**, and its BFF routes silently substitute fabricated data when the backend is unreachable — masking failures in a financial screen.

We must close these gaps to deliver the Payout & Accounting Center, while (a) not breaking the endpoints already asserted by `VendorFinanceApiTests`, (b) never moving money incorrectly, and (c) remaining extensible beyond Indian tax law.

This ADR consolidates every architecturally significant decision taken for this feature.

---

## Decision

We will build the Payout & Accounting Center as an **additive extension of the existing Vendor Finance bounded context**, governed by the eleven decisions below.

---

### D-01 — Extend the existing finance aggregates rather than introduce a parallel ledger

**Decision.** `VendorPayout` and `VendorTransaction` remain the canonical settlement aggregates. We add columns (bank account link, schedule link, idempotency key, tax withheld, adjustments, currency, failure code, provider identifiers, `xmin` concurrency token) and a new `VendorPayoutLine` join aggregate that allocates transactions to payouts. Existing routes, verbs, and response shapes are preserved; only additive DTO fields are introduced.

**Rationale.** A parallel "ledger v2" would fork the source of truth for vendor revenue, immediately diverge from `VendorKpiSnapshot` and the vendor dashboard KPIs that already read these tables, and require a dual-write reconciliation process — the exact failure mode we are trying to eliminate. Extension keeps one ledger, keeps the existing integration tests meaningful, and lets the capability land incrementally behind a feature flag.

**Consequences.** `VendorPayouts` grows to ~25 columns and needs a careful back-fill for legacy rows. Accepted: the migration is additive-only and reversible by flag, not by schema rollback.

---

### D-02 — Payouts get a dedicated port that mirrors — but does not extend — the existing payment abstraction

**Decision.** The platform records settlement *intent*; a licensed provider moves the money, behind a new `IPayoutGatewayService` port with `RazorpayXPayoutGatewayService`, `PayUPayoutGatewayService`, and `SandboxPayoutGatewayService` adapters selected by `IPayoutGatewayFactory`.

This new port **deliberately mirrors the structure of the existing pay-in abstraction** and reuses its surrounding assets:

| Existing asset | Reuse posture |
|---|---|
| `PaymentProviderType` enum (`Razorpay`, `PayU`, `Stripe`) | **Reused as-is.** No second provider enum is introduced. |
| `IPaymentServiceFactory` / `PaymentServiceFactory` shape | **Mirrored.** `IPayoutGatewayFactory` uses the identical `IServiceProvider.GetRequiredService<T>()` switch. |
| `PaymentProviders:{Provider}:*` configuration section | **Extended,** not duplicated — payout keys nest as `PaymentProviders:Razorpay:Payouts:*`. |
| `PaymentProvider` reference entity (`IsEnabled`, `DisplayOrder`, `FeePercentage`) | **Reused** for enabling/disabling a provider's payout rail without code change. |
| Razorpay HMAC-SHA256 webhook verification | **Reused as the reference algorithm** in `PspSignatureFilter`, with three defects corrected (see below). |

**Rationale.** `IPaymentService` is a **pay-in** contract: `ProcessPaymentAsync`, `HandleWebhookAsync`, `RefundPaymentAsync`. Payouts require a fundamentally different vocabulary — create fund account, validate fund account (penny-drop), create transfer, query transfer status — operating against different provider *products* with separate credentials and endpoints (Razorpay Payments API vs. **RazorpayX** Payouts API at `/v1/fund_accounts` and `/v1/payouts`; PayU Payments vs. **PayU Payouts**). Widening `IPaymentService` with six payout methods would force `RazorpayPaymentService` and `PayUPaymentService` to implement members irrelevant to collection, violating Interface Segregation and destabilising code paths that the in-progress order-placement flow depends on. Two focused ports that share an enum, a factory shape, and a configuration namespace give consistency without coupling.

**Three defects in the existing pay-in adapters must not be replicated in the payout adapters:**

1. `RazorpayPaymentService` constructs `new HttpClient()` in its constructor as a scoped service — socket exhaustion under load. Payout adapters use `IHttpClientFactory` with the already-referenced `Microsoft.Extensions.Http.Resilience` pipeline.
2. It mutates `_httpClient.DefaultRequestHeaders.Authorization` per call — not thread-safe on a shared client. Payout adapters set `Authorization` per `HttpRequestMessage`.
3. `HandleWebhookAsync` compares signatures with `==` on lowercased hex — a timing oracle. `PspSignatureFilter` uses `CryptographicOperations.FixedTimeEquals`, and additionally enforces a timestamp replay window that the existing implementation lacks entirely.

A sandbox adapter is bound whenever the environment is not Production, so a test double can never reach production — an otherwise catastrophic and silent class of incident.

**Consequences.** Two payment-related abstractions coexist in `HomeCare.Domain/Interfaces`; this is documented here and named consistently (`IPaymentService` = money in, `IPayoutGatewayService` = money out) so the distinction is discoverable. Payout completion is eventually consistent, so the UI must represent `Queued` and `Processing` as first-class, vendor-visible states rather than hiding latency. A follow-up ticket should backport defects 1–3 to the pay-in adapters once the order-placement flow stabilises.

---

### D-03 — Financial invariants are enforced in the database, not only in application code

**Decision.** The settlement equation is a `CHECK` constraint:

```
NetPayoutCents = GrossRevenueCents − PlatformFeeCents − TaxWithheldCents + AdjustmentCents
```

Additional constraints enforce non-negative amounts, `Completed ⇒ PaymentReference IS NOT NULL`, `IsPrimary ⇒ Status = 'Verified'`, and frequency/day coherence on schedules. "Exactly one primary bank account per vendor" is a **partial unique index**, not application logic.

**Rationale.** Application-level guards are bypassed by background jobs, data-fix scripts, future handlers, and concurrent writers. A rounding bug or partial update that violates the ledger equation must fail loudly at write time — not surface months later in a statutory audit as an under- or over-payment. Partial unique indexes make "exactly one primary" race-proof at zero read cost, where service-layer checks are inherently racy under concurrent `Set Primary` calls.

**Consequences.** Constraint violations surface as `DbUpdateException` and must be translated to RFC 7807 responses. Legacy rows require reconciliation via the `AdjustmentCents` back-fill before the constraint is enabled.

---

### D-04 — Money is integer minor units, end to end

**Decision.** Every monetary value is a `bigint` / `long` in ISO 4217 minor units, paired with an explicit `CurrencyCode`. Floating-point money is prohibited in the domain, DTOs, TypeScript types, and export formats. Rounding occurs exactly once per computation via a shared banker's-rounding helper. The UI formats by currency code and never hard-codes a symbol.

**Rationale.** This is already the prevailing convention (`GrossAmountCents`, `NetPayoutCents`). The reference screens show `₹` while the layout blueprint shows `$`; hard-coding either guarantees a defect. Single-point rounding is what keeps the D-03 invariant satisfiable.

**Consequences.** Frontend formatting must be centralised in the existing `utils/currency` helper; a lint rule forbids literal `₹`/`$` in payout components.

---

### D-05 — Idempotency is mandatory and enforced by unique indexes at four levels

**Decision.** Duplicate payment is prevented by four independent unique constraints: `VendorPayouts.IdempotencyKey` (client/scheduler request), `VendorPayouts.ProviderEventId` (settlement webhook), `VendorBankAccountVerifications.ProviderEventId` (verification webhook), and `VendorPayoutLines.VendorTransactionId` (a transaction settles exactly once). Payout creation additionally executes inside `pg_advisory_xact_lock(hash(vendorId))`. Webhook handlers return `200` for duplicates.

**Rationale.** PSPs deliver webhooks at-least-once and retry aggressively on non-2xx. Users double-click. Schedulers overlap with manual triggers. Defence in depth is warranted because the failure mode — paying a vendor twice — is irreversible. The line-level unique index is the last line of defence: even if two runs race past the advisory lock, the second `INSERT` aborts the entire transaction.

**Consequences.** Clients must supply an `Idempotency-Key` header on disbursement and export requests; this is documented in the OpenAPI schema.

---

### D-06 — Bank account numbers are encrypted at rest; only `Last4` and a fingerprint are queryable

**Decision.** The full account number / IBAN is stored as AES-256-GCM ciphertext with a per-record nonce, keyed from the configured secret store. Alongside it we persist `AccountNumberLast4` (display) and `AccountFingerprint` = HMAC-SHA256(accountNumber ‖ ifsc) (duplicate detection). **No API response ever contains the full account number.** A Serilog destructuring policy redacts account number, routing code, GSTIN, and PAN, with a unit test asserting no bank digits reach any sink.

**Rationale.** Bank credentials are the highest-value secret in this feature and sit adjacent to PCI/RBI obligations. Storing a keyed fingerprint lets us detect "this account is already linked" (FR-02.7, `409 Conflict`) without ever decrypting. Redaction is enforced by test, not by convention, because NFR-09 and AI_INSTRUCTIONS.md §4 make PII-free logs non-negotiable.

**Consequences.** Key rotation requires a versioned key-id prefix and a re-encryption job. Lost keys mean the PSP fund-account handle (`ProviderFundAccountRef`) becomes the only usable reference — which is acceptable, since disbursement routes through the PSP handle, not the raw number.

---

### D-07 — Verification and payout history are modelled as append-only event logs

**Decision.** `VendorBankAccountVerifications` is an append-only child collection; the parent `Status` is a denormalised projection of the latest terminal event. Completed payouts and generated tax documents are immutable after reaching a terminal state; corrections are issued as new revisions (`SupersedesDocumentId`), never as in-place edits. `AuditLog` remains append-only via the existing `EnforceAuditLogAppendOnly` guard.

**Rationale.** The UI must render a verification *timeline* with per-stage timestamps (FR-02.4). Regulators require evidence of when each stage occurred. PSP webhooks arrive out of order. An event log satisfies all three requirements, whereas mutable status columns satisfy none. Immutability of financial artefacts is the foundation of legal defensibility — the same reasoning that produced the `VendorContractAcceptance` design in ADR 011.

**Consequences.** More rows and a projection to maintain. Mitigated by a covering index on `(VendorBankAccountId, OccurredAt DESC)`.

---

### D-08 — Commission and withholding rates are snapshotted onto payout lines

**Decision.** `VendorPayoutLine` stores `CommissionRateSnapshot` and `TdsRateSnapshot` captured at allocation time, rather than joining to `IndividualVendorContract.CommissionPct` at read time.

**Rationale.** Contract renewal changes the commission percentage (ADR 011 supports renewals with revised rates). If breakdowns joined live to the contract, a renewal would retroactively rewrite the arithmetic of payouts already settled months earlier — producing statements that no longer reconcile to the money actually transferred. Snapshotting makes every historical breakdown permanently reproducible.

**Consequences.** Rate data is duplicated per line. Accepted: correctness of historical financial records outranks normalisation.

---

### D-09 — Tax documents and statement exports are jurisdiction-agnostic, generated by Strategy behind a Factory

**Decision.** `VendorTaxProfile` stores generic `TaxIdentificationNumber` / `SecondaryTaxIdentifier` keyed by `JurisdictionCode`, not `GSTIN`/`PAN` columns. `TaxDocumentGeneratorFactory` resolves a per-`DocumentType` strategy; `StatementFormatWriterFactory` resolves a per-`FileFormat` writer (PDF / CSV / XML). Jurisdiction-specific format validation lives in FluentValidation rules selected by `JurisdictionCode`. The XML export conforms to a published, versioned XSD served at a stable endpoint.

**Rationale.** Phase 1 targets India, but constraint C-13 requires US 1099-K and EU VAT without a schema migration. Strategy + Factory means a new jurisdiction or document type ships as one new class with zero changes to the dispatcher, the schema, or existing generators — a direct application of Open/Closed. Publishing a versioned XSD is what makes the ERP integration contract (FR-06.8) stable enough for vendors to automate against.

**Consequences.** Slightly more indirection than a `switch`. Justified by the number of anticipated variants and by ERP integrators' need for a frozen contract.

---

### D-10 — Long-running work is asynchronous via the existing Hangfire server; the API returns `202 Accepted`

**Decision.** Disbursement dispatch, penny-drop initiation, tax document generation, statement export, escrow release, and artefact purge run as Hangfire jobs. The corresponding endpoints return `202 Accepted` with a job handle within 200 ms (NFR-03). No new message broker is introduced.

**Rationale.** PDF rendering over a year of ledger data, 250k-row XML exports, and PSP round-trips cannot occupy a request thread without violating latency targets and risking gateway timeouts. Hangfire is already provisioned, already backed by PostgreSQL, and already used by `CheckContractExpirationsJob` — adding Kafka or RabbitMQ for six jobs would be unjustified operational weight.

**Consequences.** The frontend must poll (with backoff) or await notification for completion. Job durability depends on the Hangfire PostgreSQL store, which is backed up with the primary database.

---

### D-11 — The Center is a server-first, URL-driven workspace behind a single sidebar entry; all mock data is deleted

**Decision.** `/vendor/payouts` becomes a Next.js App Router layout hosting six deep-linkable child routes (Overview, Bank Accounts, Schedule, History, Tax Documents, Statements). Shells, tables, and lists are React Server Components; `'use client'` is applied only to stateful forms, the polling timeline, and the breakdown drawer. The sidebar retains one `Payouts` entry. Every mock/fallback constant in `app/(protected)/vendor/payouts/page.tsx` and `app/bff/vendor/payouts/**` is removed; failures render an explicit `error.tsx` boundary with `role="alert"` and a retry action.

**Rationale.** This follows ADR 019, already proven by the fulfilment module. More importantly: **fabricated fallback data in a financial screen is a correctness hazard, not a resilience feature.** A vendor shown a plausible-but-invented balance may make real business decisions on it. An honest error with a retry button is strictly safer. Server-first rendering additionally keeps tokens server-side (BFF pattern, AI_INSTRUCTIONS.md §6) and avoids shipping settlement logic to the browser.

**Consequences.** Six new routes and BFF handlers instead of one page. Offsetting benefit: each view is independently deep-linkable, independently cacheable, and independently ownable by a parallel work package.

---

## Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| **New `Payouts` microservice with its own database** | Requires distributed transactions or an outbox between order settlement and payout allocation for a single-digit-QPS workload. The existing modular monolith with Clean Architecture boundaries provides the needed isolation at a fraction of the operational cost. Revisit only if payout volume or team topology demands it. |
| **Full double-entry general ledger (debit/credit journal lines)** | Architecturally superior in the abstract, but would require re-platforming `VendorTransaction`, invalidating the vendor dashboard KPIs, and re-deriving all historical data. The `CHECK`-enforced invariant plus `VendorPayoutLine` allocation delivers the required auditability for this scope. A future ADR may migrate to full double-entry. |
| **Direct bank integration (NACH/SFTP file rails) instead of a PSP** | Requires banking partnerships, file-format certification per bank, and a settlement-reconciliation team. A PSP provides penny-drop, multi-rail routing, and webhook reconciliation out of the box. `IPayoutGatewayService` keeps a direct-rail adapter available later. |
| **Widening the existing `IPaymentService` with payout methods** | `RazorpayPaymentService` and `PayUPaymentService` already implement it for collection. Adding `CreateFundAccountAsync`, `ValidateFundAccountAsync`, `CreatePayoutAsync`, and `GetPayoutStatusAsync` would force both to implement members irrelevant to pay-in (violating Interface Segregation) and would destabilise adapters the in-progress order-placement flow depends on. Razorpay Payments and RazorpayX Payouts are separate products with separate credentials and endpoints; one interface cannot honestly represent both. |
| **A wholly independent payout provider enum, factory, and configuration section** | Would leave the codebase with two unrelated provider taxonomies, two config shapes, and two enable/disable mechanisms for the same three vendors. Rejected in favour of reusing `PaymentProviderType`, mirroring `PaymentServiceFactory`, and nesting payout keys under the existing `PaymentProviders:{Provider}` section. |
| **Compute available balance by joining order fulfilment state at query time** | Forces every balance read through `VendorOrders → PurchaseShipments/RentalContracts`, breaching the p95 < 300 ms target (NFR-02) at scale. A denormalised, indexed `SettlementState` driven by `ReleaseEscrowJob` keeps balance a single-table indexed aggregate. |
| **Synchronous tax-document and statement generation** | A year-long PDF or a 250k-row XML export cannot complete inside an HTTP request without timeouts. Rejected on NFR-03. |
| **Storing `GSTIN` and `PAN` as dedicated columns** | Directly violates constraint C-13 (extensibility to US/EU without migration). Rejected in favour of jurisdiction-keyed generic identifiers. |
| **Separate sidebar entries for Bank Accounts / Tax / Statements** (mirroring the reference screenshots' own nav) | The reference screenshots come from a standalone payouts product whose entire app *is* the payout centre. Inside the Curetor vendor portal, five additional top-level entries would crowd out Catalog, Orders, Provisioning, and Reviews. Constraint C-11 keeps one entry with in-page tabs; the visual design of each screen is reproduced faithfully. |
| **Keeping the existing BFF mock fallbacks for resilience** | Rejected on safety grounds — see D-11. |

---

## Consequences

### Positive

- One ledger, one source of truth; vendor dashboard KPIs and payout statements cannot diverge.
- Double payment is structurally prevented at four independent levels, not merely code-reviewed against.
- Ledger arithmetic errors fail at write time rather than at audit time.
- Bank credentials are encrypted at rest and provably absent from logs and API responses.
- Historical breakdowns remain reproducible across contract renewals.
- New jurisdictions, document types, export formats, and payment providers each ship as a single new class.
- Fifteen work packages, of which up to seven run concurrently on disjoint files after a single blocking foundation package.
- No new infrastructure: reuses PostgreSQL, Hangfire, S3/MinIO, QuestPDF, Resend, Redis, and the existing BFF and auth stack.

### Negative / Accepted Trade-offs

- `VendorPayouts` becomes a wide table (~25 columns) requiring a careful, one-time legacy back-fill.
- Eventual consistency in payout completion demands explicit `Queued`/`Processing` UX rather than instant confirmation.
- Rate snapshotting duplicates data per payout line.
- Key rotation for field encryption requires a dedicated re-encryption job.
- Six routes replace one page, increasing frontend surface area.
- Strategy/Factory indirection adds classes relative to a `switch` statement.

### Risks Accepted with Mitigation

| Risk | Mitigation |
|---|---|
| Legacy transactions re-paid on first scheduled run | Back-fill marks all historical `Completed` transactions as `Settled` (fail-safe direction); genuine arrears handled by an explicit, audited Finance Ops adjustment |
| PSP outage stalls disbursement | Circuit breaker + durable `Queued` state + `DispatchQueuedPayoutsJob` retry; vendor-visible status, never silent failure |
| Encryption key loss | Key stored in the managed secret store with backup/rotation policy; PSP `ProviderFundAccountRef` remains an independent disbursement path |
| Tax generation on an incomplete profile | Server-side precondition returns `422` with field-level Problem Details; UI blocks the action and deep-links to the Tax Profile form |

---

## Compliance Notes

- **HIPAA / GDPR** — No PHI enters the payout domain. `VendorPayoutLine` references `VendorTransaction`, which references `VendorOrder` by id only; buyer/patient details are never projected into payout DTOs, exports, or tax documents, consistent with ADR 020.
- **Audit** — Every mutation writes an `AuditLog` entry through `IAuditLogService`; the table is append-only (ADR 005).
- **Retention** — Payout and ledger records retained ≥ 8 years per Indian statutory requirement; export artefacts purged on a configurable TTL (default 7 days) with metadata retained.
- **Statutory** — GST platform-fee invoices and TDS Form 16A (Sec. 194-O) are generated, content-hashed, and archived immutably. Government portal filing remains a Finance Ops responsibility in Phase 1.

---

## Validation

This ADR is considered validated when:

1. The ledger-invariant `CHECK` holds across all staging rows after back-fill.
2. Concurrency tests demonstrate that two simultaneous `POST /disburse` calls produce exactly one payout, and two simultaneous `set-primary` calls produce exactly one primary account.
3. A security integration test proves no full account number appears in any API response body or any Serilog sink.
4. The 7-day plan-only scheduler dry-run reconciles against manual Finance calculations for a 10-vendor sample.
5. Pilot payouts for three vendors settle with correct UTR references and zero duplicates.
