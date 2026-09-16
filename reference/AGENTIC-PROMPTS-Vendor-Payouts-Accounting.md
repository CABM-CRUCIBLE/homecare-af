# Vendor Payouts & Accounting — Agentic Execution Prompts

**Purpose:** Self-contained, copy-paste goals for individual team members (human or AI agent). Each prompt is scoped so it can be executed **independently and in parallel** with the others in its wave, touching a disjoint set of files.

**Companion Documents:** `STRATEGY-Vendor-Payouts-Accounting.md`, `TACTICAL-PLAN-Vendor-Payouts-Accounting.md`, `ADR-021-Vendor-Payouts-Accounting-Architecture.md`

---

## How to Use

1. **Wave 0 (`WP0`) must complete and merge before any Wave 1 prompt starts.** It creates the entities, migrations, and shared DI/DbContext registrations that every other package depends on.
2. Within a wave, assign one prompt per owner. Prompts in the same wave never edit the same file.
3. Every prompt below implicitly carries the **Standing Instructions** in §0. Paste §0 together with the chosen prompt.

### File-Ownership Matrix (collision avoidance)

| Shared File | Edited Exclusively By |
|---|---|
| `HomeCare.Infrastructure/Data/HomeCareDbContext.cs` | **WP0** |
| `HomeCare.Infrastructure/Data/UnitOfWork.cs` + `IUnitOfWork` | **WP0** |
| `HomeCare.API/Extensions/ServiceCollectionExtensions.cs` | **WP0** (all new DI registrations pre-wired against interfaces) |
| `HomeCare.API/Program.cs` (job registration) | **WP6** |
| `app/(protected)/vendor/payouts/layout.tsx` | **WP7** |
| `app/(protected)/vendor/layout.tsx` (sidebar) | **WP7** |
| Migrations folder | **WP0** |

---

## §0 — Standing Instructions (prepend to every prompt)

```
You are working in the Curetor HomeCare monorepo at c:\WorkingFolder\homecare.

MANDATORY READING BEFORE YOU WRITE CODE
1. AI_Instructions.md (repository root) — Enterprise Code Quality Standards. Non-negotiable.
2. Architecture/Vendor_Payouts_Accounting_Workflow/STRATEGY-Vendor-Payouts-Accounting.md
3. Architecture/Vendor_Payouts_Accounting_Workflow/TACTICAL-PLAN-Vendor-Payouts-Accounting.md
4. Architecture/Vendor_Payouts_Accounting_Workflow/ADR-021-Vendor-Payouts-Accounting-Architecture.md

NON-NEGOTIABLE RULES
- Clean Architecture layering: Domain -> Application -> Infrastructure -> API. Never
  reference Infrastructure from Application, or EF Core from Application.
- CQRS via MediatR. Commands/Queries/Handlers/Validators live under
  HomeCare.Application/Features/<Feature>/.
- Repository + Unit of Work for all data access. No DbContext in the Application layer.
- XML doc comments (/// <summary>) on every public type, member, and interface.
- C#: PascalCase types/methods, _camelCase private fields. TypeScript: camelCase
  values, PascalCase components. NO `any` in TypeScript — strict interfaces only.
- FluentValidation on the backend, Zod on the frontend. Both, never one.
- All errors as RFC 7807 ProblemDetails via the existing global exception middleware.
  Never leak stack traces.
- Structured Serilog logging. Logs must NEVER contain bank account numbers, routing/IFSC
  codes, GSTIN, PAN, patient names, or any PHI/PII. Log identifiers only.
- Money is ALWAYS integer minor units (long / bigint) plus an ISO 4217 currency code.
  Never float, never decimal-for-money, never a hard-coded currency symbol.
- Every mutation writes an AuditLog entry via the existing IAuditLogService.
- Vendor identity comes ONLY from IVendorIdentityResolver (JWT claims, fail-closed per
  ADR 016). NEVER accept vendorId from a route, query string, or request body.
- No secrets in source or appsettings.json. Use User Secrets / environment variables.
- All external dependencies injected via interfaces so they can be mocked in unit tests.

DELIVERABLE FORMAT
- Provide COMPLETE file contents. No "// ... rest of code" placeholders.
- After each major code block, add a short "Architectural Decision" note explaining WHY
  the pattern, index, or structure was chosen.
- Include unit tests for everything you write. Run `dotnet build` and `dotnet test`
  (backend) or `npm run build` and `npm run lint` (frontend) before declaring done.

DO NOT
- Do not modify files owned by another work package (see the File-Ownership Matrix).
- Do not add mock, fixture, or fallback data to any runtime path.
- Do not change existing endpoint routes, verbs, or response field names.
```

---

# WAVE 0 — BLOCKING FOUNDATION

## Prompt WP0 — Domain Entities, EF Configurations & Migrations

> **Owner:** Backend Lead · **Parallel:** No (blocks everything) · **Est. effort:** 4 days

```
GOAL
Create the complete persistence foundation for the Vendor Payout & Accounting Center.
This is the blocking work package — six other packages start the moment this merges.

SCOPE

A. NEW DOMAIN ENTITIES — HomeCare.Domain/Entities/
   Create exactly these, each inheriting BaseEntity, with full XML docs on every property.
   Property names, types, and nullability are specified in TACTICAL-PLAN §2.
   1. VendorBankAccount
   2. VendorBankAccountVerification   (append-only child)
   3. VendorPayoutSchedule
   4. VendorPayoutLine
   5. VendorTaxProfile
   6. VendorTaxDocument
   7. VendorStatementExport

B. EXTEND EXISTING ENTITIES (additive only — do not rename or remove anything)
   - VendorPayout: add BankAccountId, ScheduleId, IdempotencyKey, TaxWithheldCents,
     AdjustmentCents, CurrencyCode, Origin, ProviderPayoutId, ProviderEventId,
     FailureCode, FailureReason, RetryCount, InitiatedByUserId, Version (xmin),
     plus navigation properties.
   - VendorTransaction: add PayoutId, SettlementState, EscrowReleasedAt,
     TaxWithheldCents, CurrencyCode, plus navigation properties.

C. DOMAIN ENUMS/CONSTANTS — HomeCare.Domain/Constants/ (follow the existing pattern)
   PayoutStatus, PayoutOrigin, BankAccountStatus, VerificationStage, PayoutFrequency,
   SettlementState, TaxDocumentType, TaxDocumentStatus, StatementAccountingType,
   StatementFileFormat, StatementExportStatus.

D. EF CORE CONFIGURATIONS — HomeCare.Infrastructure/Data/Configurations/
   One IEntityTypeConfiguration<T> per entity. Each MUST declare:
   - Table name, PK, column types and max lengths exactly as in TACTICAL-PLAN §2.
   - HasQueryFilter(e => !e.IsDeleted) for all soft-deletable entities.
   - Version mapped to the PostgreSQL xmin system column as a concurrency token
     (copy the technique already used for VendorOrder.Version).
   - EVERY index and CHECK constraint listed in TACTICAL-PLAN §2.1 through §2.9,
     including all partial (filtered) indexes. Do not omit any.
   - FK delete behaviours exactly as specified (RESTRICT vs SET NULL vs CASCADE).

E. DbContext + UnitOfWork  (you are the sole owner of these files)
   - Register all seven DbSets in HomeCareDbContext under a new
     "// Vendor Payout & Accounting Center" region.
   - Add repository properties to IUnitOfWork and UnitOfWork.

F. REPOSITORY INTERFACES ONLY — HomeCare.Application/Interfaces/
   Define (do NOT implement — Wave 1 owners implement these):
   IVendorBankAccountRepository, IVendorPayoutScheduleRepository,
   IVendorTaxRepository, IVendorStatementRepository,
   and the additive methods on IVendorFinanceRepository
   (GetPayoutBalanceAsync, GetPayoutBreakdownAsync, GetUpcomingPayoutsAsync,
    AllocateTransactionsToPayoutAsync).
   Also define the service ports so Wave 1 can code against them immediately:
   IPayoutGatewayService, IPayoutGatewayFactory, IFieldEncryptionService,
   IBankDirectoryService.
   IPayoutGatewayFactory MUST take the EXISTING HomeCare.Domain.Enums.PaymentProviderType
   (Razorpay = 1, PayU = 2, Stripe = 3) and mirror the signature of the existing
   IPaymentServiceFactory. Do NOT introduce a second provider enum — the platform
   already has working Razorpay and PayU pay-in adapters using this enum.
   IPayoutGatewayService is a SEPARATE port from the existing IPaymentService because
   that interface is pay-in only (ProcessPayment / HandleWebhook / RefundPayment) and
   cannot honestly represent fund accounts, penny-drop, or transfers. See ADR 021 D-02.
   Every method fully XML-documented.

G. MIGRATIONS
   Two additive EF Core migrations, in order:
     1. AddVendorPayoutAccountingCore
     2. AddVendorTaxAndStatementArtefacts
   Migration 1 MUST embed the back-fill SQL from TACTICAL-PLAN §2.10, executed BEFORE
   the CHECK constraints are added. Pay particular attention to back-fill step 3: legacy
   completed transactions are marked 'Settled', NOT 'Available'. Marking them
   'Available' would cause the first scheduled run to disburse a vendor's entire
   revenue history. Add an explanatory comment in the migration stating this.

H. DI PRE-WIRING — ServiceCollectionExtensions.cs (you are the sole owner)
   Register all new repositories and services against their interfaces so Wave 1 owners
   never touch this file. Place the payout gateway registrations immediately after the
   existing "// Payment services (Strategy Pattern with Factory)" block and follow its
   exact shape: register each concrete adapter as scoped, then register
   IPayoutGatewayFactory. Bind the sandbox adapter whenever the environment is not
   Production or PaymentProviders:{Provider}:Payouts is unconfigured. Reuse the
   existing PaymentProviders:* configuration namespace — do not create a new one.

ACCEPTANCE CRITERIA
- `dotnet build` succeeds with zero warnings.
- `dotnet ef migrations script` produces valid SQL containing every index and CHECK.
- Applying both migrations to a database seeded with legacy VendorPayouts/
  VendorTransactions rows succeeds with zero constraint violations.
- A new integration test asserts the ledger-invariant CHECK rejects a row where
  NetPayoutCents != Gross - Fee - Tax + Adjustment.
- A new integration test asserts the partial unique index rejects a second primary
  bank account for the same vendor.
- All existing tests, especially VendorFinanceApiTests, still pass unchanged.
```

---

# WAVE 1 — PARALLEL BACKEND (5 concurrent owners)

## Prompt WP1 — Bank Account Linking & Verification Backend

> **Owner:** Backend Engineer A · **Depends on:** WP0 · **Parallel-safe:** Yes

```
GOAL
Implement the complete backend for vendor bank account linking with penny-drop
verification (FR-02, endpoints 1–10 in TACTICAL-PLAN §4.1).

SCOPE
1. HomeCare.Infrastructure/Data/Repositories/VendorBankAccountRepository.cs
   Implement IVendorBankAccountRepository. EVERY query filtered by VendorId and
   !IsDeleted. Use AsNoTracking for reads. Duplicate detection via AccountFingerprint.

2. HomeCare.Infrastructure/Services/AesGcmFieldEncryptionService.cs
   Implement IFieldEncryptionService using AES-256-GCM with a per-record random nonce.
   Output layout: [keyVersion(1)][nonce(12)][tag(16)][ciphertext]. Key read from
   configuration "VendorPayouts:EncryptionKey" via IOptions with ValidateOnStart()
   that fails startup outside Development when absent. Also expose
   ComputeFingerprint(accountNumber, ifsc) using HMAC-SHA256.

3. HomeCare.Infrastructure/Services/CachedBankDirectoryService.cs
   Implement IBankDirectoryService. Resolve bank/branch from an IFSC/routing code via
   an allow-listed HTTP endpoint, wrapped in the existing
   Microsoft.Extensions.Http.Resilience pipeline, cached in ICacheService for 24h.
   Return null (never throw) on miss so the UI degrades to manual entry.

4. HomeCare.Application/Features/VendorBankAccounts/
   Commands: LinkBankAccountCommand, UpdateBankAccountCommand,
             RemoveBankAccountCommand, SetPrimaryBankAccountCommand,
             ReverifyBankAccountCommand, RecordVerificationOutcomeCommand.
   Queries:  GetBankAccountsQuery, GetBankAccountByIdQuery,
             GetVerificationTimelineQuery, LookupBankByCodeQuery.
   DTOs:     VendorBankAccountDto, VerificationTimelineDto, VerificationStageDto,
             BankDirectoryEntryDto.
   Validators: as specified in TACTICAL-PLAN §6.1.
   CRITICAL: VendorBankAccountDto must expose AccountNumberLast4 and
   MaskedAccountNumber ONLY. The full number must be impossible to obtain through any
   DTO, projection, or serialization path.

5. HomeCare.API/Controllers/VendorBankAccountController.cs
   Route: api/v{version:apiVersion}/vendor/bank-accounts
   [Authorize(Policy = "VendorPolicy")]. Resolve vendorId via IVendorIdentityResolver.
   Implement endpoints 1–10 exactly as specified, with correct status codes:
   201 + Location on create, 409 on duplicate, 413 oversize, 415 bad type,
   422 on set-primary of an unverified account, 429 on reverify rate limit.

6. File upload safety
   Validate by MAGIC BYTES, not extension or Content-Type. Cap at 5 MB. Store via the
   existing IObjectStorageService to a private bucket with a randomised object key.
   Serve only through a server-verified, short-lived pre-signed URL.

7. Serilog redaction
   Add a destructuring policy that redacts AccountNumber*, IfscOrRoutingCode,
   TaxIdentificationNumber, SecondaryTaxIdentifier. Write a unit test that captures
   log output during a link-account flow and asserts no 6+ consecutive digits appear.

ACCEPTANCE CRITERIA
- Unit tests for every handler and validator (mock all repositories/services).
- Integration tests: 401 unauthenticated; 404 cross-tenant; 409 duplicate fingerprint;
  201 happy path; 422 set-primary on unverified; concurrent set-primary yields exactly
  one primary.
- Security test: no response body from any of the 10 endpoints contains the full
  account number.
- >= 85% line coverage on the new Application feature folder.
```

---

## Prompt WP2 — Payout Engine & Schedule Backend

> **Owner:** Backend Engineer B · **Depends on:** WP0 · **Parallel-safe:** Yes

```
GOAL
Implement the settlement engine, schedule configuration, and the extended payout API
(FR-01, FR-03, FR-04; endpoints 11–21 in TACTICAL-PLAN §4.2).

SCOPE
1. HomeCare.Application/Services/PayoutCalculationService.cs
   Compute {grossCents, platformFeeCents, taxWithheldCents, adjustmentCents, netCents}
   from VendorTransactions in SettlementState = 'Available'. Rounding happens exactly
   ONCE per computation via a shared banker's-rounding helper. The result MUST satisfy
   Net = Gross - Fee - Tax + Adjustment (the database CHECK will reject it otherwise).
   Snapshot CommissionRate and TdsRate per line at allocation time — never join live to
   IndividualVendorContract (ADR 021 D-08).

2. HomeCare.Application/Services/PayoutScheduleCalculator.cs
   Pure function: (frequency, preferredDay, timeZoneId, fromUtc) -> nextRunAtUtc.
   Handle: Weekly, BiWeekly (anchored to LastRunAtUtc), Monthly with day 1–28 and the
   99 = last-day sentinel, DST transitions, and month-length variation.

3. HomeCare.Application/Services/PayoutEligibilityPolicy.cs
   Single source of truth for gating. Returns an explicit reason code:
   Eligible | BelowThreshold | NoVerifiedAccount | PayoutInFlight | ContractExpired |
   ZeroBalance. Used identically by the instant-payout handler and the scheduler job.

4. HomeCare.Application/Services/PayoutStateMachine.cs
   Mirror the existing FulfillmentStateMachine. Reject illegal transitions such as
   Completed -> Queued. Expose CanTransition(from, to) and AssertTransition(from, to).

5. Repositories
   - VendorPayoutScheduleRepository (implements IVendorPayoutScheduleRepository).
   - Extend VendorFinanceRepository with GetPayoutBalanceAsync,
     GetPayoutBreakdownAsync, GetUpcomingPayoutsAsync, AllocateTransactionsToPayoutAsync.
     AllocateTransactionsToPayoutAsync MUST run inside a transaction that first takes
     pg_advisory_xact_lock(hashtext(vendorId::text)).

6. HomeCare.Application/Features/VendorFinance/ (extend the existing folder)
   New: GetPayoutBalanceQuery, GetPayoutBreakdownQuery, GetUpcomingPayoutsQuery,
        GetPayoutScheduleQuery, UpsertPayoutScheduleCommand, CancelPayoutCommand,
        ExportPayoutHistoryQuery.
   REWRITE TriggerDisbursementCommandHandler: it currently creates a payout with ZERO
   amounts and no gateway call. Replace with: eligibility check -> advisory lock ->
   calculate -> insert payout + lines -> mark transactions Allocated -> audit log ->
   call IPayoutGatewayService with the idempotency key -> return 202.
   Keep the existing route, verb, and response DTO shape; additive fields only.

7. HomeCare.API/Controllers/VendorFinanceController.cs
   Add endpoints 15–21. REFACTOR the private GetCurrentVendorIdAsync to delegate to
   IVendorIdentityResolver (ADR 016 compliance) and apply the same refactor to
   VendorTransactionController. Do not change existing routes or DTO field names.

8. Add a "payout-mutations" rate-limit policy (10 req/min/vendor) and apply it to
   /disburse and /schedule.

ACCEPTANCE CRITERIA
- 100% BRANCH coverage on PayoutCalculationService, PayoutScheduleCalculator,
  PayoutEligibilityPolicy, PayoutStateMachine. These are the financial core.
- Property-based or table-driven tests proving the ledger invariant holds across
  rounding boundaries and for zero/negative adjustment cases.
- Schedule calculator tests for: month-end, leap day, DST spring-forward and
  fall-back, last-day sentinel, bi-weekly anchoring.
- Concurrency integration test: two simultaneous POST /disburse produce exactly ONE
  payout; the second returns the first payout (idempotent) or 409.
- All pre-existing VendorFinanceApiTests still pass unmodified.
```

---

## Prompt WP3 — Payout Gateway Adapters (Razorpay / PayU) & Webhook Ingestion

> **Owner:** Backend Engineer C · **Depends on:** WP0 (interface only) · **Parallel-safe:** Yes

```
GOAL
Implement the payout gateway adapters and secure, idempotent webhook ingestion
(endpoints 39–40 in TACTICAL-PLAN §4.6).

READ FIRST — EXISTING CODE YOU MUST ALIGN WITH AND LEARN FROM
  HomeCare.Domain/Interfaces/IPaymentService.cs
  HomeCare.Domain/Enums/PaymentProviderType.cs
  HomeCare.Domain/Entities/PaymentProvider.cs
  HomeCare.Infrastructure/Services/PaymentServiceFactory.cs
  HomeCare.Infrastructure/Services/RazorpayPaymentService.cs
  HomeCare.Infrastructure/Services/PayUPaymentService.cs

The platform ALREADY has working Razorpay and PayU integrations — but they are PAY-IN
only (ProcessPaymentAsync / HandleWebhookAsync / RefundPaymentAsync). They have no
fund-account, penny-drop, or transfer capability, and they target different provider
products (Razorpay Payments vs RazorpayX Payouts; PayU Payments vs PayU Payouts) with
separate credentials and endpoints.

DO NOT widen IPaymentService with payout methods. That would force both existing
adapters to implement members irrelevant to collection (Interface Segregation
violation) and would destabilise code paths the in-progress order-placement flow
depends on. See ADR 021 D-02.

DO reuse, verbatim where possible:
  - PaymentProviderType enum (Razorpay = 1, PayU = 2, Stripe = 3). Do NOT create a
    second provider enum.
  - The PaymentServiceFactory shape — IServiceProvider.GetRequiredService<T>() switch
    with a NotImplementedException arm for Stripe.
  - The PaymentProviders:{Provider}:* configuration namespace. Payout keys nest as
    PaymentProviders:Razorpay:Payouts:* and PaymentProviders:PayU:Payouts:*.
  - The PaymentProvider reference entity (IsEnabled, DisplayOrder) to enable/disable a
    provider's payout rail without a code change.
  - The HMAC-SHA256 webhook algorithm from RazorpayPaymentService.HandleWebhookAsync.

SCOPE
1. HomeCare.Domain/Interfaces/IPayoutGatewayService.cs  (if WP0 has not already landed it)
   CreateFundAccountAsync, ValidateFundAccountAsync (penny-drop), CreatePayoutAsync,
   GetPayoutStatusAsync, VerifyWebhookSignature. Plus IPayoutGatewayFactory with
   CreatePayoutGateway(PaymentProviderType providerType) — mirroring
   IPaymentServiceFactory exactly. Full XML docs.

2. HomeCare.Infrastructure/Services/Payouts/SandboxPayoutGatewayService.cs
   Deterministic in-memory implementation for Development, Docker, and Testing.
   Simulates fund-account creation, penny-drop, and payout dispatch with configurable
   success/failure/latency. Bound by default whenever the environment is not Production.

3. HomeCare.Infrastructure/Services/Payouts/RazorpayXPayoutGatewayService.cs
   Targets the RazorpayX Payouts API (/v1/fund_accounts, /v1/payouts) — NOT the
   Payments API base URL used by RazorpayPaymentService.

4. HomeCare.Infrastructure/Services/Payouts/PayUPayoutGatewayService.cs
   Targets PayU Payouts.

   CORRECT THESE THREE DEFECTS present in the existing pay-in adapters. Do not copy
   them forward:
     a) RazorpayPaymentService does `new HttpClient()` in a scoped constructor —
        socket exhaustion under load. Use IHttpClientFactory with a NAMED client
        ("razorpayx-payouts" / "payu-payouts") wrapped in the already-referenced
        Microsoft.Extensions.Http.Resilience pipeline (jittered exponential retry +
        circuit breaker).
     b) It mutates _httpClient.DefaultRequestHeaders.Authorization per call — not
        thread-safe on a shared client. Set Authorization per HttpRequestMessage.
     c) Its HandleWebhookAsync compares signatures with `==` on lowercased hex — a
        timing oracle. Use CryptographicOperations.FixedTimeEquals.

   Pass the platform IdempotencyKey to the provider on every mutating call.
   Credentials from configuration only — never in source, never logged.

5. HomeCare.Infrastructure/Services/Payouts/PayoutGatewayFactory.cs
   Implements IPayoutGatewayFactory. Resolve by PaymentProviderType, exactly mirroring
   PaymentServiceFactory. Stripe throws NotImplementedException, consistent with the
   existing factory. Throw at STARTUP (not at request time) if Production is
   configured with the sandbox provider.

6. HomeCare.API/Filters/PspSignatureFilter.cs
   IAsyncAuthorizationFilter. Resolve the signing secret from
   PaymentProviders:{provider}:Payouts:WebhookSecret using the {provider} route value.
   Verify HMAC-SHA256 over the RAW request body with
   CryptographicOperations.FixedTimeEquals. Reject if X-Timestamp is absent or skew
   exceeds 300 seconds — the existing implementation has NO replay protection, which
   is the gap this filter closes. Enable request buffering so the raw body is read
   before model binding. Return 401 ProblemDetails on failure.

7. HomeCare.API/Controllers/PayoutWebhookController.cs
   Route: api/v{version:apiVersion}/webhooks/payouts/{provider}
   [AllowAnonymous] + [ServiceFilter(typeof(PspSignatureFilter))].
   POST /bank-verification -> RecordVerificationOutcomeCommand
   POST /payout-status     -> RecordPayoutOutcomeCommand
   Both MUST be idempotent via the unique ProviderEventId index, and MUST return 200
   even for duplicates or events referencing unknown entities (log and park). Only a
   signature failure returns non-2xx. Rationale: PSPs treat any non-2xx as delivery
   failure and enter retry storms.

8. HomeCare.Application/Features/VendorFinance/Commands/RecordPayoutOutcomeCommand.cs
   On success: set Status=Completed, PaymentReference=UTR/ACH trace id, DisbursedAt;
   transition contributing transactions to SettlementState='Settled'; audit; email.
   On failure: set Status=Failed, FailureCode, FailureReason; release the transactions
   back to SettlementState='Available' so they roll into the next cycle; audit; email.
   Use PayoutStateMachine.AssertTransition before any status change.

9. Health check: add a payout-gateway connectivity probe to the existing /health
   endpoint, tagged so it can be excluded from liveness probes.

10. Raise a follow-up ticket (do not action it here) to backport defects (a), (b), and
    (c) to RazorpayPaymentService and PayUPaymentService once the order-placement flow
    stabilises. Reference ADR 021 D-02.

ACCEPTANCE CRITERIA
- Unit tests for signature verification: valid, tampered body, wrong secret, stale
  timestamp, missing header, and a timing-safety assertion that comparison does not
  short-circuit.
- Unit test proving each adapter resolves its HttpClient from IHttpClientFactory and
  never sets DefaultRequestHeaders.
- Integration test: replaying the identical webhook twice produces exactly one state
  change and two 200 responses.
- Integration test: an unsigned webhook returns 401.
- Integration test: a failed payout returns its transactions to 'Available'.
- Factory test: PaymentProviderType.Stripe throws NotImplementedException, matching
  the existing PaymentServiceFactory behaviour.
- Startup test: Production + sandbox provider fails fast with a clear message.
- No existing payment tests or the in-progress order-placement flow are affected —
  IPaymentService, RazorpayPaymentService, PayUPaymentService, PaymentServiceFactory,
  and PaymentProviderType must remain UNMODIFIED by this work package.
```

---

## Prompt WP4 — Tax Documents Backend

> **Owner:** Backend Engineer D · **Depends on:** WP0 · **Parallel-safe:** Yes

```
GOAL
Implement tax profile management and GST/TDS document generation
(FR-05; endpoints 26–32 in TACTICAL-PLAN §4.4).

SCOPE
1. HomeCare.Infrastructure/Data/Repositories/VendorTaxRepository.cs
   Implements IVendorTaxRepository. All queries scoped by VendorId and !IsDeleted.

2. HomeCare.Application/Features/VendorTax/
   Commands: UpsertTaxProfileCommand, GenerateTaxDocumentCommand.
   Queries:  GetTaxProfileQuery, GetTaxDocumentsQuery, GetTaxDocumentByIdQuery,
             GetTaxDocumentDownloadUrlQuery, GetFinancialYearsQuery.
   DTOs:     VendorTaxProfileDto, VendorTaxDocumentDto, TaxDocumentDownloadDto.
   Validators per TACTICAL-PLAN §6.1, including GSTIN and PAN format + checksum for
   JurisdictionCode = 'IN'. Format rules MUST be selected by JurisdictionCode so a new
   jurisdiction adds a rule set, not a schema change (ADR 021 D-09).

3. Generation pipeline — Factory + Strategy
   HomeCare.Application/Services/Tax/ITaxDocumentGenerator.cs
   HomeCare.Application/Services/Tax/TaxDocumentGeneratorFactory.cs
   Strategies (one class each, single responsibility):
     - GstPlatformFeeInvoiceStrategy  (taxable value, CGST/SGST vs IGST split driven
       by PlaceOfSupplyCode, invoice number series)
     - TdsCertificateStrategy         (Form 16A, Sec 194-O, quarterly aggregation)
     - WithholdingSummaryStrategy
     - TaxReconciliationStrategy      (XLSX/CSV output)
   Each produces a document model; rendering goes through the EXISTING
   IPdfRenderingService (QuestPDF). Do not introduce a new PDF library.

4. Immutability and integrity
   Compute SHA-256 over the rendered bytes into ContentHash. Assign a deterministic
   DocumentNumber (e.g. GST-INV-{FY}-{sequence}). Archive to a private bucket via the
   existing IObjectStorageService. Documents are NEVER updated in place — a correction
   creates a new row with SupersedesDocumentId set and marks the original 'Superseded'.

5. Idempotent generation
   The unique index UX_VendorTaxDocuments_Vendor_Type_Period makes repeated generation
   safe. If an Available document already exists for the type+period, return 200 with
   the existing record instead of 202.

6. Precondition enforcement
   If the tax profile is incomplete (missing GSTIN/PAN for IN), return 422 with
   field-level ProblemDetails.errors so the UI can deep-link to the profile form.

7. HomeCare.API/Controllers/VendorTaxController.cs
   Route: api/v{version:apiVersion}/vendor/tax. VendorPolicy + IVendorIdentityResolver.
   Download endpoints verify ownership server-side BEFORE issuing a pre-signed URL
   (TTL <= 15 minutes, GET only, single object), and write a download audit entry.

ACCEPTANCE CRITERIA
- Unit tests per strategy asserting correct taxable value, tax split, and totals from
  a fixed transaction fixture.
- GSTIN and PAN validator tests including checksum-invalid cases.
- Integration test: generate twice for the same period -> one document, second call
  returns 200 not 202.
- Integration test: generation with an incomplete tax profile returns 422 with a
  populated errors dictionary.
- Integration test: download returns a URL whose expiry is <= 15 minutes out, and an
  audit entry is written.
- >= 85% line coverage on the new Application feature folder.
```

---

## Prompt WP5 — Statements, Exports & Reconciliation Backend

> **Owner:** Backend Engineer E · **Depends on:** WP0 · **Parallel-safe:** Yes

```
GOAL
Implement asynchronous multi-format statement export and ledger reconciliation
(FR-06; endpoints 33–38 in TACTICAL-PLAN §4.5).

SCOPE
1. HomeCare.Infrastructure/Data/Repositories/VendorStatementRepository.cs
   Implements IVendorStatementRepository. Ledger reads MUST use AsAsyncEnumerable and
   explicit Select projections — never materialise the full result set (NFR-15), and
   never project buyer/patient fields (ADR 020).

2. HomeCare.Application/Services/Statements/ — Factory + Strategy
   IStatementFormatWriter + StatementFormatWriterFactory, with three writers:
     - CsvStatementWriter  (reuse the existing CsvExportWriter)
     - XmlStatementWriter  (System.Xml.XmlWriter, streaming, DTD processing DISABLED,
                            no string concatenation)
     - PdfStatementWriter  (existing IPdfRenderingService, paginated)
   All three stream to the destination; peak memory must be independent of row count.

3. Published XSD
   Author `ledger-export-v1.xsd`, embed it as a resource, and serve it from
   GET /api/v1/vendor/statements/schema/ledger-export.xsd. The XML writer output MUST
   validate against it — assert this in a test. This is the frozen contract ERP
   integrators automate against (FR-06.8).

4. HomeCare.Application/Features/VendorStatements/
   Commands: RequestStatementExportCommand, CompleteStatementExportCommand.
   Queries:  GetStatementExportsQuery, GetStatementExportByIdQuery,
             GetStatementDownloadUrlQuery, GetReconciliationSummaryQuery.
   DTOs:     VendorStatementExportDto, ReconciliationSummaryDto, DiscrepancyDto.
   Validators per TACTICAL-PLAN §6.1 (range <= 24 months; max 5 outstanding jobs).

5. HomeCare.Application/Services/ReconciliationService.cs
   For a period, compare VendorTransactions against VendorPayoutLines and return
   { syncedLedgerMatches, unmatchedDiscrepancies, ledgerBalanceMatchRatePct,
     discrepancies[] }. A discrepancy is: a settled transaction with no payout line,
   a payout line whose amounts differ from its transaction, or a payout whose line sum
   differs from its header.

6. HomeCare.API/Controllers/VendorStatementController.cs
   Route: api/v{version:apiVersion}/vendor/statements. VendorPolicy +
   IVendorIdentityResolver. POST /export returns 202 with a job handle within 200 ms.
   Download returns 409 while Building and 410 once Expired, with a regenerate hint.

ACCEPTANCE CRITERIA
- Unit tests per writer against a fixed ledger fixture (golden-file comparison).
- XSD validation test: generated XML validates against the published schema.
- Memory test: exporting 250k synthetic rows keeps peak managed heap under a fixed
  ceiling (proves streaming, NFR-15).
- Integration tests: 202 on request; 409 while Building; 410 when Expired;
  422 when the range exceeds 24 months.
- Reconciliation test with deliberately injected discrepancies returns the exact
  expected match rate.
```

---

# WAVE 1 — PARALLEL FRONTEND

## Prompt WP7 — Center Shell, Navigation & Overview (start first in this track)

> **Owner:** Frontend Engineer A · **Depends on:** WP0 contracts · **Parallel-safe:** Yes (but WP8–WP12 depend on it)

```
GOAL
Build the Payout & Accounting Center shell and the Overview view, and DELETE all
existing mock data from the payouts feature (FR-01; ADR 021 D-11).

SCOPE
1. app/(protected)/vendor/payouts/layout.tsx  — React Server Component
   - Page header: "Payout & Accounting Center", sub-caption, and a primary
     "Download Statement" action linking to /vendor/payouts/statements.
   - Tab navigation across the six child routes. Active state derived from usePathname
     in a small 'use client' sub-component; the layout itself stays a server component.
   - Mobile: the tab strip becomes a horizontally scrollable pill row.

2. app/(protected)/vendor/payouts/page.tsx  — Overview, React Server Component
   - Fetch server-side with getAuthHeaders() + backendUrl() from lib/bff.
   - Balance & Payout Schedule Summary band: Total Earned, Available For Payout,
     In Escrow, Last Payout Amount (4-up desktop / 2-up tablet / 1-up mobile).
   - Next Scheduled Payout card (blue accent) with amount, date, cadence, destination.
   - Disbursed This Month with transfer count.
   - "Initiate Instant Payout" client component. It must be DISABLED with a visible,
     specific reason whenever the API reports canInitiateInstantPayout = false —
     surface blockedReason verbatim, never a generic message.
   - Upcoming Disbursements rail.

3. app/(protected)/vendor/payouts/error.tsx and loading.tsx
   error.tsx: role="alert", render ProblemDetails title/detail, "Retry Connection"
   button calling reset(). Follow the pattern already used by /vendor/orders.
   loading.tsx: skeletons matching the real layout (no spinner-only states).

4. MANDATORY DELETION — this is a correctness requirement, not cleanup
   - Remove INITIAL_SUMMARY, INITIAL_TRENDS, INITIAL_PAYOUTS and every other mock
     constant from app/(protected)/vendor/payouts/page.tsx.
   - Remove FALLBACK_PAYOUTS and all fabricated fallback objects from
     app/bff/vendor/payouts/route.ts and app/bff/vendor/payouts/summary/route.ts.
     BFF routes must proxy faithfully and propagate the backend status code and
     ProblemDetails body. A vendor must never be shown an invented balance.

5. app/(protected)/vendor/layout.tsx  (you are the sole owner of this file)
   Keep exactly one "Payouts" sidebar entry pointing at /vendor/payouts. Change the
   "Transactions" entry to point at /vendor/payouts/history?view=ledger.

6. types/vendor-payouts.ts
   Strict TypeScript interfaces for every DTO in TACTICAL-PLAN §4. No `any`.

7. features/vendor-payouts/api/vendorPayoutsApi.ts
   Typed client functions for all BFF routes, for use by WP8–WP12.

DESIGN
Match the reference screenshots and the token table in TACTICAL-PLAN §5.3 exactly:
white rounded-2xl cards with slate borders, blue-600 primary actions, blue-600 accent
card for Next Scheduled Payout, uppercase tracking-wider table headers, the specified
status badge colour families. Currency formatting goes through utils/currency using
the currencyCode from the API — never hard-code ₹ or $.

ACCEPTANCE CRITERIA
- `npm run build` and `npm run lint` clean; zero `any`.
- Verified at 320px, 768px, and 1280px with no horizontal scrolling.
- axe-core reports zero serious/critical issues.
- A repository-wide grep confirms no mock/fallback constants remain anywhere under
  app/(protected)/vendor/payouts/ or app/bff/vendor/payouts/.
- Vitest tests for the disabled-CTA reason rendering and currency formatting.
```

---

## Prompt WP8 — Bank Accounts UI

> **Owner:** Frontend Engineer B · **Depends on:** WP7 · **Parallel-safe:** Yes

```
GOAL
Build the Bank Accounts view matching Bank_Accounts.jpg (FR-02).

SCOPE
1. app/(protected)/vendor/payouts/bank-accounts/page.tsx — RSC shell fetching the
   account list server-side, composing client components below.

2. features/vendor-payouts/components/BankAccountForm.tsx  ('use client')
   "Add New Bank Account" card. Two-column grid on desktop, single column on mobile:
   Account Holder Name | Bank Name (with a green "Auto-Detected" chip once resolved),
   IFSC / Routing Code | Account Number / IBAN, then a full-width Account Type select.
   Debounced IFSC lookup against /bff/vendor/bank-accounts/bank-lookup populates Bank
   Name; on lookup failure the field silently stays manually editable.
   Dashed-border upload dropzone: "Click to upload canceled cheque or statement",
   sub-caption "Supported formats: PDF, PNG, JPEG (Max size: 5MB)", cloud-upload icon,
   drag-and-drop plus file browse, thumbnail/filename preview, remove action.
   Actions: "Cancel" (secondary) and "+ Save & Verify" (blue-600 primary).
   react-hook-form + zodResolver using features/vendor-payouts/schemas/bankAccountSchema.ts.

3. features/vendor-payouts/components/VerificationTimeline.tsx  ('use client')
   "Penny-Drop Verification" right-rail card. Vertical timeline with green check nodes
   for completed stages and a blue dot for the current stage, each showing stage name
   and timestamp ("Oct 24, 10:15 AM"). Blue info panel below stating the ~4 hour SLA
   and immediate-disbursement eligibility.
   Poll /bff/vendor/bank-accounts/{id}/verification with exponential backoff
   (2s -> 30s cap), stopping on a terminal stage. Use role="status" aria-live="polite".

4. features/vendor-payouts/components/LinkedAccountsTable.tsx
   Columns: BANK NAME (with bank icon) | ACCOUNT NUMBER (•••• 9874) | TYPE |
   STATUS (Verified green / Pending amber / Failed rose) | ACTIONS.
   Primary account shows a non-actionable "Primary Account" chip; others show
   "Set Primary" and "Remove". Below `md`, render as stacked cards instead of a table.
   Remove opens a confirmation dialog and surfaces the 409 message when the account is
   referenced by an in-flight payout.

5. BFF routes: app/bff/vendor/bank-accounts/{route.ts, [id]/route.ts,
   [id]/verification/route.ts, [id]/set-primary/route.ts, [id]/reverify/route.ts,
   bank-lookup/route.ts}. Faithful proxies — no fallback data, propagate status codes
   and ProblemDetails.

6. schemas/bankAccountSchema.ts — Zod mirror of the server validator: IFSC regex,
   IBAN mod-97, account number length, accepted MIME types, 5 MB cap.

ACCEPTANCE CRITERIA
- Visual parity with Bank_Accounts.jpg at 1280px.
- Fully usable at 320px: no horizontal scroll, table renders as cards.
- Field-level errors from ProblemDetails.errors render beside the correct input with
  aria-describedby.
- axe-core clean. Timeline updates announced to screen readers.
- Vitest: schema validation cases, timeline stage rendering, masked-number formatting.
```

---

## Prompt WP9 — Payout Schedule UI

> **Owner:** Frontend Engineer C · **Depends on:** WP7 · **Parallel-safe:** Yes

```
GOAL
Build the Payout Schedule view matching Payout_Schedule.jpg (FR-03).

SCOPE
1. app/(protected)/vendor/payouts/schedule/page.tsx — RSC shell fetching the current
   schedule and the vendor's verified bank accounts server-side.

2. features/vendor-payouts/components/ScheduleRulesForm.tsx  ('use client')
   "Disbursement Rules" card containing:
   - "Automatic Disbursements" row: bold label, grey helper text
     ("System triggers payouts automatically on meeting rules."), blue toggle switch
     on the right. Must be keyboard-operable with role="switch" and aria-checked.
   - "Disbursement Frequency": three-segment control (Weekly | Bi-weekly | Monthly),
     active segment blue-600 filled with a leading dot, inactive white with a slate
     border.
   - Two-column row: "Preferred Disbursal Day" select (day-of-week for Weekly/Bi-weekly,
     day-of-month plus "Last Day" for Monthly — the options must switch reactively) and
     "Minimum Payout Threshold" currency input with a leading currency symbol derived
     from currencyCode.
   - Actions right-aligned: "Discard Changes" (secondary, resets to the last persisted
     values with NO server round-trip) and "✓ Save Configuration" (blue-600 primary,
     disabled while pristine or submitting).
   - When Automatic Disbursements is off, visually de-emphasise and disable the
     dependent controls.
   react-hook-form + zodResolver with schemas/payoutScheduleSchema.ts. Send If-Match
   with the row version; on 409 show a "settings changed elsewhere — reload" notice.

3. features/vendor-payouts/components/NextPayoutCard.tsx
   Blue-600 filled card: "NEXT SCHEDULED PAYOUT" label with a calendar icon, large
   amount, "Estimated Date: <formatted>", divider, and "Disbursing to: <bank> (•••• 9874)"
   with a bank icon.

4. features/vendor-payouts/components/ActiveRulesSummary.tsx
   White card mirroring the PERSISTED configuration: Status (Enabled/Disabled badge),
   Frequency, Minimum Threshold, Default Recipient. This intentionally shows saved
   state, not form state, so the vendor can see exactly what is currently in force.

5. BFF: app/bff/vendor/payouts/schedule/route.ts (GET, PUT). Faithful proxy.

6. schemas/payoutScheduleSchema.ts — Zod mirror including the conditional requirement
   of dayOfWeek vs dayOfMonth based on frequency.

ACCEPTANCE CRITERIA
- Visual parity with Payout_Schedule.jpg at 1280px; right rail stacks below the form
  on tablet and mobile.
- Changing frequency swaps the day options without losing other field values.
- "Discard Changes" restores persisted values with no network call.
- Toggle and segmented control fully keyboard navigable; axe-core clean.
- Vitest: conditional schema branches, dirty-state gating of the save button.
```

---

## Prompt WP10 — Payout History & Breakdown UI

> **Owner:** Frontend Engineer D · **Depends on:** WP7 · **Parallel-safe:** Yes

```
GOAL
Build the Payout History & Disbursements view matching
Payout_History_Disbursements.jpg (FR-04).

SCOPE
1. app/(protected)/vendor/payouts/history/page.tsx — RSC. Read page, status, dateFrom,
   dateTo, and sort from searchParams and fetch server-side (URL-driven state per
   ADR 019). Support ?view=ledger to render the transaction ledger tab for the
   redirected /vendor/transactions route.

2. features/vendor-payouts/components/DisbursementMetricBand.tsx
   Four cards with corner icons: Total Earned (arrow), Pending Balance (clock),
   In Escrow (lock), Last Payout Amount (circle-x). Label in small grey caps, value in
   large bold.

3. features/vendor-payouts/components/DisbursementHistoryTable.tsx
   "All Disbursements" card. Columns: DATE | AMOUNT | STATUS | RECIPIENT BANK |
   REF NUMBER. Status pills: Completed (emerald), Processing (amber), Queued (blue),
   Failed (rose). For Processing rows the reference column shows "Pending Bank
   Clearance" in muted text; for Failed rows it shows the failure code (e.g.
   ERR-INSUFFICIENT-FUNDS). Footer: "Showing X-Y of N payouts" on the left with
   numbered pagination + "Next" on the right. Each row exposes "View Breakdown".
   Below `md`, render as stacked cards.

4. features/vendor-payouts/components/PayoutFilterBar.tsx ('use client')
   Status select, date-range inputs, and sort control. Changes push to the URL via
   router.replace(..., { scroll: false }) — never local-only state.

5. features/vendor-payouts/components/PayoutBreakdownDrawer.tsx ('use client')
   Slide-over (full-screen sheet on mobile) showing the settlement waterfall:
   Gross Sales -> Platform Fee (with rate %) -> Taxes Withheld (with TDS rate) ->
   Adjustments -> Net Payout, followed by the itemised contributing transactions and
   the UTR/ACH reference with a copy-to-clipboard action. Focus-trapped, Escape to
   close, focus restored to the invoking row on close.

6. features/vendor-payouts/components/UpcomingDisbursementsRail.tsx
   Right rail of cards: date, blue "QUEUED" badge, amount (append " (Est.)" when
   projected), destination bank line.

7. BFF: app/bff/vendor/payouts/{route.ts, [id]/breakdown/route.ts, upcoming/route.ts,
   export/route.ts}. Faithful proxies, no fallback data.

ACCEPTANCE CRITERIA
- Visual parity with Payout_History_Disbursements.jpg at 1280px.
- Filters and pagination are deep-linkable and survive a page refresh and browser back.
- Drawer is focus-trapped and axe-core clean.
- Table degrades to cards below `md` with no horizontal scroll.
- Vitest: status-pill mapping, reference-column fallback text, waterfall arithmetic
  display.
```

---

## Prompt WP11 — Tax Documents UI

> **Owner:** Frontend Engineer E · **Depends on:** WP7 · **Parallel-safe:** Yes

```
GOAL
Build the Tax Documents & Invoicing view matching Tax_Documents_Invoicing.jpg (FR-05).

SCOPE
1. app/(protected)/vendor/payouts/tax-documents/page.tsx — RSC. Read financialYear and
   documentType from searchParams; fetch the document list and tax profile server-side.

2. features/vendor-payouts/components/TaxDocumentFilterBar.tsx ('use client')
   White pill bar: "Filter By:" label, "Financial Year: 2026-27" select, and
   "Document Type: All" select. Both write to the URL.

3. features/vendor-payouts/components/TaxRecordsList.tsx
   "Available Tax Records" card. Each row: circular document-type icon, bold title
   (e.g. "Form 16A (Q1 TDS Certificate)"), sub-line "Apr - Jun FY 2026-27 • Generated:
   Jul 15, 2026", a type chip ("TDS Certificate" / "GST Invoice" /
   "Withholding Summary") in blue, and a right-aligned "Download" button with a
   download icon. Rows in Generating state show a spinner and a disabled button;
   GenerationFailed rows show the reason and a "Retry" action.

4. features/vendor-payouts/components/GenerateStatementPanel.tsx ('use client')
   Right-rail "Generate Statement" card: "Select Document Type" select, Start Date and
   End Date inputs side by side, and a blue-600 "✨ Compile & Generate" button.
   On 202 show an inline progress state and poll the document list until the record
   becomes Available. On 422 (incomplete tax profile) render the field-level errors
   plus a prominent link to the Tax Profile form.

5. features/vendor-payouts/components/TaxProfileCard.tsx ('use client')
   Displays and edits GSTIN, PAN, legal entity name, and place of supply. Renders
   inline in the header area as "Tax Identification Number: GSTIN: … | PAN: …".
   Validated with schemas/taxProfileSchema.ts (GSTIN + PAN format and checksum).

6. features/vendor-payouts/components/AutoTdsSyncNotice.tsx
   Green-tinted card with a shield icon: "Auto-TDS Certificate Sync" and the
   explanatory copy about quarterly Form 16A generation and TRACES filing.

7. Download flow: call the BFF, receive { downloadUrl, expiresAt, fileName }, trigger
   the download, and show a toast. Handle 409 (still generating) and 410 (expired) with
   distinct, actionable messages.

8. BFF: app/bff/vendor/tax/{profile/route.ts, documents/route.ts,
   documents/generate/route.ts, documents/[id]/download/route.ts}. Faithful proxies.

ACCEPTANCE CRITERIA
- Visual parity with Tax_Documents_Invoicing.jpg at 1280px; right rail stacks below on
  tablet/mobile.
- GSTIN/PAN validation rejects checksum-invalid values client-side before submit.
- Filters are deep-linkable.
- axe-core clean; download buttons have accessible names including the document title.
- Vitest: schema cases, chip/type mapping, generating and failed row states.
```

---

## Prompt WP12 — Statements & Reconciliation UI

> **Owner:** Frontend Engineer F · **Depends on:** WP7 · **Parallel-safe:** Yes

```
GOAL
Build the Statements & Reconciliation view matching Statement_Reconciliation.jpg (FR-06).

SCOPE
1. app/(protected)/vendor/payouts/statements/page.tsx — RSC fetching recent exports and
   the reconciliation summary server-side.

2. features/vendor-payouts/components/ExportLedgerForm.tsx ('use client')
   "Export Accounts Ledger" card:
   - "Select Period Timeline": four-segment control (Last 7 Days | Last Month |
     Last Quarter | Custom Range), active segment blue-600 filled. Selecting a preset
     auto-populates the date inputs; Custom Range enables manual editing.
   - Start Date and End Date inputs side by side.
   - "Accounting Type": three-segment control (Payout Statements | Fee Invoices |
     Accounting Ledger).
   - "File Extension Format": three stacked radio cards, each with a bold title,
     descriptive sub-line, and a right-aligned radio indicator. Selected card gets
     border-blue-600 and a blue-tinted background:
       PDF Document (.pdf)   — "Best for human-readable physical auditing."
       Excel Spreadsheet (.csv) — "Tabular representation suited for Excel/Numbers."
       XML Schema File (.xml)  — "Structured files direct for integration in Tally,
                                  SAP, or ERPs."
   - Full-width blue-600 "⬇ Compile & Export Document" button.
   react-hook-form + zodResolver with schemas/statementExportSchema.ts (endDate >=
   startDate, span <= 24 months).
   On 202 show an inline "Compiling…" state and poll the export until Ready.

3. features/vendor-payouts/components/ReconciliationCard.tsx
   "System Reconciliation" card: "Synced Ledger Matches" with a green count,
   "Unmatched Discrepancies" with an amber count on a tinted row, and a footer line
   "✓ 99.8% Ledger Balance Match Rate". Clicking the discrepancy count expands the
   discrepancy list.

4. features/vendor-payouts/components/RecentDownloadsRail.tsx
   "Recent Downloads" card. Each entry: filename in bold monospace-ish type,
   "Today, 10:45 AM • Expires in 24h" sub-line, and a blue icon download button.
   Expired entries render muted with a "Regenerate" action instead of download.

5. BFF: app/bff/vendor/statements/{export/route.ts, exports/route.ts,
   exports/[id]/download/route.ts, reconciliation/route.ts}. Faithful proxies.

6. schemas/statementExportSchema.ts — Zod mirror of the server validator.

ACCEPTANCE CRITERIA
- Visual parity with Statement_Reconciliation.jpg at 1280px.
- Period presets correctly compute date ranges relative to today.
- Radio cards are keyboard navigable as a proper radiogroup with arrow-key movement.
- 410 Gone on download renders the regenerate affordance, not a generic error.
- Fully usable at 320px; axe-core clean.
- Vitest: preset date arithmetic, schema branches, expiry countdown formatting.
```

---

# WAVE 2 — INTEGRATION (after Wave 1 backend merges)

## Prompt WP6 — Background Jobs

> **Owner:** Backend Engineer B or C · **Depends on:** WP2, WP3, WP4, WP5 · **Parallel-safe:** No

```
GOAL
Implement and register the seven Hangfire jobs that drive automation
(TACTICAL-PLAN §8).

SCOPE — HomeCare.Infrastructure/BackgroundJobs/
Follow the structure of the existing CheckContractExpirationsJob: constructor-injected
interfaces, [AutomaticRetry(Attempts = n)], structured logging, per-item try/catch so
one failure never aborts the batch.

1. PayoutScheduleScannerJob        (recurring, hourly)
   Query due schedules using the IX_VendorPayoutSchedules_DueRuns partial index. Per
   vendor: open a transaction, take pg_advisory_xact_lock(hashtext(vendorId::text)),
   evaluate PayoutEligibilityPolicy, and either record LastSkippedReason or create the
   payout plus lines and mark transactions Allocated. Always advance NextRunAtUtc via
   PayoutScheduleCalculator. Support a PLAN-ONLY mode controlled by
   `Payouts:ScannerMode` = Plan | Live: in Plan mode compute and log everything but
   write nothing. Plan mode is required for the 7-day production dry-run.

2. DispatchQueuedPayoutsJob        (recurring, every 5 minutes)
   Submit Queued payouts to IPayoutGatewayService with the stored IdempotencyKey.
   Honour the circuit breaker; on transient failure increment RetryCount and leave the
   payout Queued. After a configurable retry ceiling, transition to OnHold and alert.

3. InitiatePennyDropJob            (fire-and-forget)
4. GenerateTaxDocumentJob          (fire-and-forget + recurring: GST monthly on day 3,
                                    TDS quarterly on 15 Jul/Oct/Jan/Apr)
5. BuildStatementExportJob         (fire-and-forget)
6. PurgeExpiredExportsJob          (recurring, daily) — delete S3 objects past
   ExpiresAt and mark rows Expired; retain metadata for audit.
7. ReleaseEscrowJob                (recurring, every 15 minutes) — transition
   VendorTransaction.SettlementState from Escrow to Available once the linked order
   reaches a fulfilment-complete state.

REGISTRATION — HomeCare.API/Program.cs (you are the sole owner of this section)
Register all recurring jobs alongside the existing check-contract-expirations-daily
entry, using the same RecurringJob.AddOrUpdate<T> + try/catch pattern.

ACCEPTANCE CRITERIA
- Integration tests per job against the real test database.
- Scanner test: a vendor below threshold is skipped with LastSkippedReason =
  'BelowThreshold' and the balance rolls into the next cycle.
- Scanner test: Plan mode writes nothing but logs the computed amounts.
- Concurrency test: scanner and a simultaneous manual disburse produce exactly ONE
  payout.
- Dispatch test: a PSP circuit-open condition leaves the payout Queued with an
  incremented RetryCount and no duplicate provider call.
- Purge test: an expired export's S3 object is deleted and the row is marked Expired
  while metadata is preserved.
```

---

## Prompt WP13 — Security Hardening & Observability

> **Owner:** Security/Platform Engineer · **Depends on:** WP1–WP5 · **Parallel-safe:** Yes

```
GOAL
Close out the cross-cutting security and observability controls in TACTICAL-PLAN §7
and NFR-17.

SCOPE
1. Rate limiting — extend AddHomeCareRateLimiting() with a "payout-mutations" policy
   (10 req/min per resolved vendorId) applied to POST /vendor/payouts/disburse,
   POST /vendor/tax/documents/generate, POST /vendor/statements/export, and
   POST /vendor/bank-accounts/{id}/reverify. Reads get 60 req/min. Return 429 with
   ProblemDetails and a Retry-After header.

2. Serilog redaction — implement and register a destructuring policy redacting
   AccountNumber, AccountNumberCipher, IfscOrRoutingCode, TaxIdentificationNumber,
   SecondaryTaxIdentifier across all sinks. Add a test that exercises the full
   link-account and generate-tax-document flows with an in-memory sink and asserts no
   run of 6+ consecutive digits and no GSTIN/PAN-shaped token appears.

3. Health checks — add a PSP connectivity check and an object-storage reachability
   check to the existing /health endpoint, tagged so they can be excluded from
   liveness probes.

4. Metrics — emit counters and histograms for: payout success/failure rate,
   payout dispatch latency, bank verification latency, tax document generation
   duration, statement export duration and row count, and webhook signature failures.

5. Correlation — ensure CorrelationId flows from the BFF through the API into
   background jobs (propagate via job arguments) so a single vendor action is
   traceable end to end.

6. Secret validation — add IOptions ValidateOnStart() for PayoutGatewayOptions,
   FieldEncryptionOptions, and WebhookSigningOptions so a misconfigured production
   deployment fails at startup rather than at first payout.

7. Security test suite — HomeCare.Tests/Security/VendorPayoutSecurityTests.cs:
   - No endpoint response contains a full account number.
   - Cross-tenant access to every payout/bank/tax/statement resource returns 404.
   - Unsigned and replayed webhooks are rejected / no-op respectively.
   - Pre-signed URL expiry does not exceed 15 minutes.
   - Client-supplied VendorId, Status, NetPayoutCents, and PaymentReference in request
     bodies are ignored or rejected (mass-assignment guard).

ACCEPTANCE CRITERIA
- All security tests green.
- Startup fails fast with an actionable message when any required secret is absent
  outside Development.
- /health reports PSP and object-storage status.
```

---

# WAVE 3 — VERIFICATION

## Prompt WP14 — Test Suites, QA & Performance

> **Owner:** QA Engineer · **Depends on:** WP6–WP12 · **Parallel-safe:** No

```
GOAL
Prove the feature meets every acceptance gate in TACTICAL-PLAN §9 and §11.

SCOPE
1. Playwright E2E (tests/e2e/vendor-payouts.spec.ts) — full happy path:
   link bank account -> stub the verification webhook -> observe the timeline reach
   Verified -> set primary -> configure the schedule -> initiate an instant payout ->
   stub the settlement webhook -> view the breakdown with a UTR -> generate a tax
   document -> download it -> export a CSV statement -> re-download from Recent
   Downloads.

2. Accessibility — run axe-core against all six views at 320px, 768px, and 1280px.
   Zero serious or critical violations. Verify keyboard-only completion of the bank
   account form, the schedule form, and the export form.

3. Load tests (tests/load/vendor-payouts.js, k6):
   - GET /vendor/payouts with 10k payouts for one vendor: p95 < 300 ms.
   - GET /vendor/payouts/balance under 50 concurrent vendors: p95 < 300 ms.
   - POST /vendor/statements/export returns within 200 ms (202).
   - A 250k-row CSV export completes in under 60 s with bounded memory.

4. Coverage gates — enforce in CI: >= 85% line coverage on
   HomeCare.Application/Features/Vendor{BankAccounts,Finance,Tax,Statements}, and
   100% branch coverage on PayoutCalculationService, PayoutScheduleCalculator,
   PayoutEligibilityPolicy, and PayoutStateMachine.

5. Data-integrity verification against a staging database restored from production:
   - Apply both migrations plus the back-fill.
   - Assert zero ledger-invariant CHECK violations.
   - Assert every legacy completed transaction is SettlementState = 'Settled' (NOT
     'Available') — this is the guard against disbursing a vendor's entire revenue
     history on the first scheduled run.
   - Assert no vendor has more than one primary bank account.

6. Regression — confirm the full pre-existing suite passes, with particular attention
   to VendorFinanceApiTests, VendorDashboard tests, and the fulfilment suite.

7. Produce test-results/EVIDENCE-Vendor-Payouts.md recording coverage numbers, k6
   percentiles, axe results, and the staging data-integrity assertions.

ACCEPTANCE CRITERIA
- All suites green in CI.
- Evidence document committed.
- No P1/P2 defects open.
```

---

## Prompt WP15 — Admin Read-Only Payout Views

> **Owner:** Full-stack Engineer · **Depends on:** WP2 · **Parallel-safe:** Yes

```
GOAL
Give Finance Operations a cross-vendor payout register with compliance hold controls
(endpoints 41–44 in TACTICAL-PLAN §4.7).

SCOPE
1. HomeCare.API/Controllers/AdminPayoutController.cs
   Route: api/v{version:apiVersion}/admin/payouts, [Authorize(Policy = "AdminPolicy")].
   GET /                    cross-vendor register with vendor, status, and date filters
   GET /{id}/breakdown      settlement audit view
   POST /{id}/hold          place a compliance hold (Queued -> OnHold), reason required
   POST /{id}/release       release a hold (OnHold -> Queued)
   Hold and release MUST go through PayoutStateMachine and MUST write an AuditLog entry
   naming the administrator and the reason.

2. Application layer: GetAdminPayoutRegisterQuery, HoldPayoutCommand,
   ReleasePayoutCommand, with validators requiring a non-empty reason of 10–500 chars.

3. Frontend: app/(protected)/admin/payouts/page.tsx — RSC table with filters, a
   breakdown drawer reusing the WP10 component, and hold/release confirmation dialogs.
   Follow the existing admin portal styling.

4. BFF: app/bff/admin/payouts/** faithful proxies.

ACCEPTANCE CRITERIA
- Non-admin principals receive 403 on all four endpoints.
- Hold and release are rejected from invalid source states with 422.
- Every hold/release writes an audit entry containing the administrator id and reason.
- Integration and Vitest coverage for the new surface.
```

---

## Parallelisation Summary

| Wave | Prompts | Max Concurrent Owners | Gate to Next Wave |
|---|---|---|---|
| **0** | WP0 | 1 | Migrations apply cleanly; invariant and primary-account tests pass |
| **1** | WP1, WP2, WP3, WP4, WP5, WP7 → (WP8, WP9, WP10, WP11, WP12), WP15 | **7** | All backend controllers return live data; frontend builds with zero mock constants |
| **2** | WP6, WP13 | 2 | Jobs pass integration tests; security suite green |
| **3** | WP14 | 1 | Coverage gates met; evidence pack committed |
