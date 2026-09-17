# Strategy: Device Maintenance & Calibration Workflow

**Document type:** Strategy plan  
**Author:** Enterprise Solution Architecture  
**Date:** 2024-12-19  
**Status:** Revised (Addressing Review Findings F-001 through F-020)  

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)
2. [Current-State Assessment](#2-current-state-assessment)
3. [Functional Requirements](#3-functional-requirements)
4. [Non-Functional Requirements](#4-non-functional-requirements)
5. [Constraints](#5-constraints)
6. [Assumptions](#6-assumptions)
7. [Strategic Position & Architecture](#7-strategic-position--architecture)
8. [Domain Model & Entity Relationships](#8-domain-model--entity-relationships)
9. [Application Layer Design](#9-application-layer-design)
10. [Security & Authorization Framework](#10-security--authorization-framework)
11. [API Design & Implementation](#11-api-design--implementation)
12. [Frontend Architecture](#12-frontend-architecture)
13. [Testing Strategy Implementation](#13-testing-strategy-implementation)
14. [Observability & Monitoring](#14-observability--monitoring)
15. [Performance & Scalability](#15-performance--scalability)
16. [Risk Register & Mitigations](#16-risk-register--mitigations)
17. [Execution Gate](#17-execution-gate)

---

## 1. Purpose and Scope

### 1.1 Business Objective
Enable healthcare vendors to perform comprehensive maintenance and calibration workflows for IoMT devices within the Curetor Marketplace platform, ensuring regulatory compliance, device readiness, and seamless inventory synchronization. This capability directly supports revenue generation by maintaining device availability and compliance with FDA 21 CFR Part 820 and ISO 13485 quality management requirements.

### 1.2 In Scope
- Device selection for maintenance from returned rentals or scheduled calibration
- Mandatory sanitization checklist with technician authentication and audit trails
- Sensor calibration testing (O2 purity, ECG baseline, flow rate validation)
- Live telemetry and battery health diagnostics
- Calibration certificate upload and document management with comprehensive security validation
- Device status lifecycle management and inventory synchronization
- Multi-tenant maintenance workflow isolation with granular role-based access control
- HIPAA-compliant audit logging with tamper-evident cryptographic protection
- Integration with existing Curetor Marketplace authentication and authorization
- Comprehensive observability and monitoring for compliance violations
- Complete testing strategy with concrete implementation and architecture fitness functions
- **NEW:** Explicit authorization policies for all maintenance operations
- **NEW:** Comprehensive file security validation pipeline with virus scanning and PHI detection
- **NEW:** Audit trail tamper detection using cryptographic hashing
- **NEW:** Multi-layered testing implementation with specific test suites
- **NEW:** Complete frontend architecture with React component hierarchy
- **NEW:** Concrete API contracts with DTOs and validation
- **NEW:** Performance monitoring and distributed tracing

### 1.3 Out of Scope
- Physical device repair workflows beyond standard maintenance
- Vendor technician certification and training management
- Patient data handling during device returns (assumes pre-sanitized devices)
- Procurement and inventory management of maintenance supplies
- Direct integration with external calibration equipment APIs
- Real-time IoMT device telemetry streaming during normal operation
- Warranty claim processing and vendor reimbursement workflows

---

## 2. Current-State Assessment

### 2.1 Existing Solution Context
The Curetor Marketplace platform provides a solid foundation with established patterns:

**Reusable Infrastructure (src/Infrastructure/):**
- `TenantDbContext.cs` - Multi-tenant data isolation with global query filters
- `AuditableEntity.cs` - Base entity with audit trail support
- `SoftDeleteEntity.cs` - Soft delete pattern for data retention
- `EncryptedFieldAttribute.cs` - Field-level encryption for sensitive data

**Established Domain Patterns (src/Domain/):**
- `BaseEntity.cs` with `xmin` concurrency tokens
- `DomainEvent.cs` infrastructure for event-driven workflows
- `ValueObject.cs` pattern for complex business rules

**Application Layer Patterns (src/Application/):**
- MediatR CQRS implementation with `IRequest<T>` and `IRequestHandler<T>`
- FluentValidation pipeline behaviors
- `ICurrentUserService` for tenant-scoped operations

**API Layer Patterns (src/Api/):**
- JWT Bearer authentication with role-based authorization
- RFC 7807 error handling with `ProblemDetails`
- Structured logging with Serilog and correlation IDs

### 2.2 Infrastructure Abstractions (Addressing F-002)

**Hardware Integration Abstractions:**
```csharp
namespace Curetor.Infrastructure.DeviceIntegration
{
    public interface IDeviceConnector
    {
        Task<bool> EstablishConnectionAsync(string deviceId, ConnectionType type, CancellationToken cancellationToken);
        Task<TelemetryReading> ReadTelemetryAsync(string deviceId, TelemetryType type, CancellationToken cancellationToken);
        Task<bool> SendCommandAsync(string deviceId, DeviceCommand command, CancellationToken cancellationToken);
    }

    public class BluetoothDeviceConnector : IDeviceConnector
    {
        // Bluetooth-specific implementation
    }

    public class WiFiDeviceConnector : IDeviceConnector
    {
        // WiFi-specific implementation
    }

    public class CellularDeviceConnector : IDeviceConnector
    {
        // Cellular-specific implementation
    }
}
```

**Domain Service Interfaces (Business Logic Only):**
```csharp
namespace Curetor.Domain.Maintenance.Services
{
    public interface ITelemetryService
    {
        Task<ConnectivityTestResult> ValidateConnectivityAsync(string deviceId, ConnectivityTestParameters parameters);
        Task<BatteryHealthResult> AnalyzeBatteryHealthAsync(string deviceId, BatteryTestParameters parameters);
        Task<DataTransmissionResult> ValidateDataProtocolsAsync(string deviceId, ProtocolTestParameters parameters);
    }

    public interface ISanitizationService
    {
        Task<SanitizationResult> ValidateCleaningProtocolAsync(string deviceId, SanitizationParameters parameters);
        Task<FilterReplacementResult> ValidateFilterReplacementAsync(string deviceId, string partNumber);
        Task<InspectionResult> ValidateComponentInspectionAsync(string deviceId, InspectionChecklist checklist);
    }

    public interface ICalibrationService
    {
        Task<CalibrationResult> ValidateCalibrationResultsAsync(string deviceId, CalibrationTestData testData);
        Task<CalibrationSummary> GenerateCalibrationReportAsync(string deviceId, IEnumerable<CalibrationResult> results);
        bool IsCalibrationWithinTolerance(CalibrationResult result, CalibrationStandards standards);
    }
}
```

---

## 3. Functional Requirements

**FR-01: Device Selection for Maintenance**
- System shall display filterable device fleet with status badges (Needs Maintenance, Calibration Due, Ready for Deployment)
- Support search by serial number, device name, and model ID
- Display summary statistics (total devices, devices needing service, ready devices)
- Allow selection of devices flagged as 'Needs Maintenance' from returned rentals
- Allow selection of active devices due for periodic calibration based on schedule
- **SECURITY:** Enforce tenant isolation and MaintenanceTechnician role authorization via `SameTenant` and `MaintenanceAccess` policies

**FR-02: Sanitization Checklist Management**
- System shall provide configurable sanitization checklist templates by device type
- Enforce mandatory completion of medical-grade chemical cleaning verification
- Track HEPA filter replacement with part numbers and dates
- Log outer casing and component inspection results with pass/fail status
- Capture technician ID with authentication verification and timestamp
- Support photo upload for inspection documentation with comprehensive security validation
- **AUDIT:** All sanitization activities logged with cryptographic tamper detection using SHA-256 hash chains

**FR-03: Sensor Calibration Testing**
- System shall support O2 purity concentration test recording with target ranges
- Enable ECG signal baseline test with 1.0 mV test signal validation
- Track flow rate validation with acceptable tolerance ranges
- Record calibration results with pass/fail determination
- Support custom calibration protocols by device manufacturer
- Generate calibration summary reports with statistical analysis
- **COMPLIANCE:** Enforce FDA 21 CFR Part 820 calibration requirements with audit trail

**FR-04: Telemetry and Battery Diagnostics**
- System shall execute live cellular connectivity tests with signal strength reporting
- Perform Wi-Fi connectivity validation with network quality metrics
- Test battery health capacity with percentage and cycle count
- Validate data transmission protocols (HL7 FHIR, proprietary formats)
- Record diagnostic results with timestamp and test parameters
- Generate connectivity and power management reports
- **MONITORING:** Alert on diagnostic test failures and compliance violations

**FR-05: Calibration Certificate Management**
- System shall support drag-and-drop upload for PDF and PNG calibration certificates
- Implement comprehensive file security validation including virus scanning, PHI detection, and digital signature validation
- Store technician sign-off reports with authentication verification
- Maintain version control for certificate updates with audit trail
- Generate certificate expiration alerts and compliance reports
- **FILE SECURITY:** Quarantine uploaded files until security validation completes

**FR-06: Device Status Lifecycle Management**
- System shall update device status through maintenance workflow states
- Trigger inventory synchronization events with tenant-scoped publishing
- Generate maintenance completion certificates with digital signatures
- Support bulk device status updates with optimistic concurrency control
- Maintain device maintenance history with searchable audit logs
- **INTEGRATION:** Publish domain events for inventory system synchronization

---

## 4. Non-Functional Requirements

**NFR-01: Performance**
- Device list loading: < 2 seconds for 10,000 devices with filtering
- Maintenance workflow creation: < 500ms response time
- File upload processing: < 30 seconds for 10MB calibration certificates
- Database queries: < 100ms for single-tenant maintenance data retrieval
- Concurrent users: Support 100 simultaneous maintenance technicians per tenant

**NFR-02: Security & Compliance**
- HIPAA compliance for all PHI handling with field-level encryption
- FDA 21 CFR Part 820 audit trail requirements with tamper detection
- ISO 13485 quality management system integration
- Multi-tenant data isolation with zero cross-tenant data leakage
- Role-based access control with principle of least privilege

**NFR-03: Availability & Reliability**
- 99.9% uptime during business hours (6 AM - 10 PM local time)
- Graceful degradation when external device connectivity fails
- Automatic retry mechanisms for transient failures
- Data backup and recovery with 4-hour RPO, 1-hour RTO

**NFR-04: Scalability**
- Horizontal scaling support for application tier
- Database partitioning strategy for multi-tenant data growth
- Asynchronous processing for long-running maintenance operations
- CDN integration for calibration certificate storage and retrieval

**NFR-05: Observability**
- Comprehensive logging with correlation IDs for request tracing
- Performance metrics collection with alerting thresholds
- Compliance violation monitoring with real-time notifications
- Distributed tracing for complex maintenance workflow operations

---

## 5. Constraints

**C-01: Technical Constraints**
- Must integrate with existing Curetor Marketplace authentication and authorization
- Database schema changes require backward compatibility
- File storage must use existing Azure Blob Storage infrastructure
- API versioning required for breaking changes

**C-02: Regulatory Constraints**
- FDA 21 CFR Part 820 compliance for medical device quality systems
- HIPAA compliance for any patient-related data handling
- ISO 13485 quality management system requirements
- State medical device regulations where applicable

**C-03: Business Constraints**
- Implementation timeline: 12 weeks from approval to production deployment
- Budget allocation: $150,000 for development and infrastructure
- Resource availability: 2 senior developers, 1 QA engineer, 1 DevOps engineer
- Go-live dependency: Must align with Q2 2025 marketplace expansion

**C-04: Integration Constraints**
- Existing inventory management system API limitations
- Device manufacturer API rate limits and authentication requirements
- Third-party calibration equipment integration complexity
- Legacy device support for older IoMT models

---

## 6. Assumptions

**A-01: Infrastructure Assumptions**
- Azure cloud infrastructure remains primary deployment target
- PostgreSQL database performance adequate for projected data volumes
- Existing Redis cache infrastructure available for session management
- Azure Service Bus available for asynchronous message processing

**A-02: Business Process Assumptions**
- Maintenance technicians have basic computer literacy and training
- Device manufacturers provide standardized calibration protocols
- Regulatory compliance requirements remain stable during implementation
- Customer demand justifies development investment and ongoing maintenance costs

**A-03: Technical Assumptions**
- .NET 8 and Entity Framework Core 8 remain supported platforms
- React 18 and TypeScript provide adequate frontend capabilities
- MediatR pattern continues to meet CQRS requirements
- FluentValidation sufficient for complex business rule validation

**A-04: Integration Assumptions**
- Device connectivity protocols remain stable (Bluetooth, WiFi, Cellular)
- Third-party virus scanning services available via API
- Digital signature validation libraries compatible with common certificate formats
- Existing audit logging infrastructure scales to maintenance workflow volume

---

## 7. Strategic Position & Architecture

### 7.1 Clean Architecture Compliance

**Domain Layer (Core Business Logic):**
- `Device` aggregate with maintenance state management
- `MaintenanceWorkflow` aggregate with workflow orchestration
- `CalibrationTest`, `SanitizationTask`, `TelemetryTest` value objects
- Domain services for business rule validation and calculations
- Domain events for cross-aggregate communication

**Application Layer (Use Cases):**
- MediatR commands and queries for all maintenance operations
- FluentValidation for input validation and business rules
- Application services for workflow orchestration
- DTOs for data transfer and API contracts

**Infrastructure Layer (External Concerns):**
- Entity Framework Core for data persistence
- Azure Blob Storage for file management
- External device integration adapters
- Logging, monitoring, and observability implementations

**Presentation Layer (User Interface):**
- ASP.NET Core Web API for backend services
- React SPA for maintenance technician interface
- SignalR for real-time workflow status updates

### 7.2 SOLID Principles Application

**Single Responsibility Principle:**
- Each aggregate handles one business concept (Device, MaintenanceWorkflow)
- Separate command handlers for each maintenance operation
- Dedicated services for telemetry, sanitization, and calibration concerns

**Open/Closed Principle:**
- Abstract `TestResultBase` enables new test types without modification
- Strategy pattern for different device calibration protocols
- Plugin architecture for device manufacturer integrations

**Liskov Substitution Principle:**
- All test result implementations properly substitute base abstractions
- Device connector implementations interchangeable based on connectivity type
- Repository pattern implementations substitutable for testing

**Interface Segregation Principle:**
- Focused domain service interfaces (ITelemetryService, ISanitizationService, ICalibrationService)
- Separate read and write operations through CQRS pattern
- Granular authorization policies for specific operations

**Dependency Inversion Principle:**
- Domain layer depends only on abstractions, not concrete implementations
- Infrastructure implementations injected through dependency injection
- External service integrations abstracted behind domain interfaces

---

## 8. Domain Model & Entity Relationships

### 8.1 Core Aggregates

**Device Aggregate Root:**
```csharp
namespace Curetor.Domain.Maintenance.Entities
{
    public class Device : AuditableEntity, ISoftDelete, ITenantEntity
    {
        public string DeviceId { get; private set; }
        public string SerialNumber { get; private set; }
        public string ModelId { get; private set; }
        public string ManufacturerName { get; private set; }
        public DeviceStatus Status { get; private set; }
        public DateTime? LastMaintenanceDate { get; private set; }
        public DateTime? NextCalibrationDue { get; private set; }
        public string TenantId { get; private set; }
        public bool IsDeleted { get; private set; }

        private readonly List<MaintenanceWorkflow> _maintenanceHistory = new();
        public IReadOnlyCollection<MaintenanceWorkflow> MaintenanceHistory => _maintenanceHistory.AsReadOnly();

        public void StartMaintenance(string technicianId, MaintenanceType type)
        {
            if (Status == DeviceStatus.InMaintenance)
                throw new InvalidOperationException("Device is already in maintenance");

            Status = DeviceStatus.InMaintenance;
            var workflow = MaintenanceWorkflow.Create(DeviceId, technicianId, type, TenantId);
            _maintenanceHistory.Add(workflow);
            
            AddDomainEvent(new MaintenanceWorkflowStartedEvent(DeviceId, workflow.WorkflowId, TenantId));
        }

        public void CompleteMaintenance(string workflowId)
        {
            var workflow = _maintenanceHistory.FirstOrDefault(w => w.WorkflowId == workflowId);
            if (workflow == null)
                throw new InvalidOperationException("Maintenance workflow not found");

            workflow.Complete();
            Status = DeviceStatus.Ready;
            LastMaintenanceDate = DateTime.UtcNow;
            
            if (workflow.Type == MaintenanceType.Calibration)
                NextCalibrationDue = CalculateNextCalibrationDate();

            AddDomainEvent(new MaintenanceWorkflowCompletedEvent(DeviceId, workflowId, TenantId));
        }

        private DateTime CalculateNextCalibrationDate()
        {
            // Business logic for calibration scheduling
            return DateTime.UtcNow.AddMonths(6);
        }
    }
}
```

**MaintenanceWorkflow Aggregate Root (Addressing F-003):**
```csharp
namespace Curetor.Domain.Maintenance.Entities
{
    public class MaintenanceWorkflow : AuditableEntity, ITenantEntity
    {
        public string WorkflowId { get; private set; }
        public string DeviceId { get; private set; }
        public string TechnicianId { get; private set; }
        public MaintenanceType Type { get; private set; }
        public WorkflowStatus Status { get; private set; }
        public DateTime StartedAt { get; private set; }
        public DateTime? CompletedAt { get; private set; }
        public string TenantId { get; private set; }

        private readonly List<SanitizationTask> _sanitizationTasks = new();
        private readonly List<CalibrationTest> _calibrationTests = new();
        private readonly List<TelemetryTest> _telemetryTests = new();
        private readonly List<WorkflowDocument> _documents = new();

        public IReadOnlyCollection<SanitizationTask> SanitizationTasks => _sanitizationTasks.AsReadOnly();
        public IReadOnlyCollection<CalibrationTest> CalibrationTests => _calibrationTests.AsReadOnly();
        public IReadOnlyCollection<TelemetryTest> TelemetryTests => _telemetryTests.AsReadOnly();
        public IReadOnlyCollection<WorkflowDocument> Documents => _documents.AsReadOnly();

        public static MaintenanceWorkflow Create(string deviceId, string technicianId, MaintenanceType type, string tenantId)
        {
            return new MaintenanceWorkflow
            {
                WorkflowId = Guid.NewGuid().ToString(),
                DeviceId = deviceId,
                TechnicianId = technicianId,
                Type = type,
                Status = WorkflowStatus.InProgress,
                StartedAt = DateTime.UtcNow,
                TenantId = tenantId
            };
        }

        public void AddSanitizationTask(SanitizationTaskType taskType, string description)
        {
            if (Status != WorkflowStatus.InProgress)
                throw new InvalidOperationException("Cannot add tasks to completed workflow");

            var task = SanitizationTask.Create(WorkflowId, taskType, description, TechnicianId);
            _sanitizationTasks.Add(task);
        }

        public void CompleteSanitizationTask(string taskId, SanitizationResult result)
        {
            var task = _sanitizationTasks.FirstOrDefault(t => t.TaskId == taskId);
            if (task == null)
                throw new InvalidOperationException("Sanitization task not found");

            task.Complete(result);
            AddDomainEvent(new SanitizationTaskCompletedEvent(WorkflowId, taskId, result, TenantId));
        }

        public void AddCalibrationTest(CalibrationTestType testType, CalibrationTestParameters parameters)
        {
            if (Status != WorkflowStatus.InProgress)
                throw new InvalidOperationException("Cannot add tests to completed workflow");

            var test = CalibrationTest.Create(WorkflowId, testType, parameters, TechnicianId);
            _calibrationTests.Add(test);
        }

        public void CompleteCalibrationTest(string testId, CalibrationTestResult result)
        {
            var test = _calibrationTests.FirstOrDefault(t => t.TestId == testId);
            if (test == null)
                throw new InvalidOperationException("Calibration test not found");

            test.Complete(result);
            AddDomainEvent(new CalibrationTestCompletedEvent(WorkflowId, testId, result, TenantId));
        }

        public void AddTelemetryTest(TelemetryTestType testType, TelemetryTestParameters parameters)
        {
            if (Status != WorkflowStatus.InProgress)
                throw new InvalidOperationException("Cannot add tests to completed workflow");

            var test = TelemetryTest.Create(WorkflowId, testType, parameters, TechnicianId);
            _telemetryTests.Add(test);
        }

        public void CompleteTelemetryTest(string testId, TelemetryTestResult result)
        {
            var test = _telemetryTests.FirstOrDefault(t => t.TestId == testId);
            if (test == null)
                throw new InvalidOperationException("Telemetry test not found");

            test.Complete(result);
            AddDomainEvent(new TelemetryTestCompletedEvent(WorkflowId, testId, result, TenantId));
        }

        public void AttachDocument(string fileName, string fileUrl, DocumentType documentType)
        {
            var document = WorkflowDocument.Create(WorkflowId, fileName, fileUrl, documentType, TenantId);
            _documents.Add(document);
            AddDomainEvent(new DocumentAttachedEvent(WorkflowId, document.DocumentId, TenantId));
        }

        public void Complete()
        {
            if (!CanComplete())
                throw new InvalidOperationException("Workflow cannot be completed - missing required tasks");

            Status = WorkflowStatus.Completed;
            CompletedAt = DateTime.UtcNow;
        }

        private bool CanComplete()
        {
            // Business rules for workflow completion
            var requiredSanitizationComplete = Type == MaintenanceType.FullMaintenance 
                ? _sanitizationTasks.All(t => t.Status == TaskStatus.Completed)
                : true;

            var requiredCalibrationComplete = Type == MaintenanceType.Calibration || Type == MaintenanceType.FullMaintenance
                ? _calibrationTests.All(t => t.Status == TestStatus.Completed)
                : true;

            return requiredSanitizationComplete && requiredCalibrationComplete;
        }
    }
}
```

### 8.2 Value Objects and Test Results

**Abstract Test Result Base (Addressing F-005):**
```csharp
namespace Curetor.Domain.Maintenance.ValueObjects
{
    public abstract class TestResultBase : ValueObject
    {
        public abstract string TestType { get; }
        public TestStatus Status { get; protected set; }
        public DateTime CompletedAt { get; protected set; }
        public string TechnicianId { get; protected set; }
        public string Notes { get; protected set; }
        
        public abstract bool IsWithinTolerance();
        public abstract IDictionary<string, object> GetTestParameters();
        public abstract IDictionary<string, object> GetTestResults();
        
        protected override IEnumerable<object> GetEqualityComponents()
        {
            yield return TestType;
            yield return Status;
            yield return CompletedAt;
            yield return TechnicianId;
        }
    }

    public class O2PurityTestResult : TestResultBase
    {
        public override string TestType => "O2_PURITY";
        public decimal MeasuredPurity { get; private set; }
        public decimal TargetPurity { get; private set; }
        public decimal TolerancePercentage { get; private set; }

        public static O2PurityTestResult Create(decimal measuredPurity, decimal targetPurity, decimal tolerance, string technicianId, string notes = null)
        {
            return new O2PurityTestResult
            {
                MeasuredPurity = measuredPurity,
                TargetPurity = targetPurity,
                TolerancePercentage = tolerance,
                Status = DetermineStatus(measuredPurity, targetPurity, tolerance),
                CompletedAt = DateTime.UtcNow,
                TechnicianId = technicianId,
                Notes = notes
            };
        }

        public override bool IsWithinTolerance()
        {
            var deviation = Math.Abs(MeasuredPurity - TargetPurity);
            var allowedDeviation = TargetPurity * (TolerancePercentage / 100);
            return deviation <= allowedDeviation;
        }

        public override IDictionary<string, object> GetTestParameters()
        {
            return new Dictionary<string, object>
            {
                { "TargetPurity", TargetPurity },
                { "TolerancePercentage", TolerancePercentage }
            };
        }

        public override IDictionary<string, object> GetTestResults()
        {
            return new Dictionary<string, object>
            {
                { "MeasuredPurity", MeasuredPurity },
                { "WithinTolerance", IsWithinTolerance() },
                { "Deviation", Math.Abs(MeasuredPurity - TargetPurity) }
            };
        }

        private static TestStatus DetermineStatus(decimal measured, decimal target, decimal tolerance)
        {
            var deviation = Math.Abs(measured - target);
            var allowedDeviation = target * (tolerance / 100);
            return deviation <= allowedDeviation ? TestStatus.Passed : TestStatus.Failed;
        }
    }

    public class ECGBaselineTestResult : TestResultBase
    {
        public override string TestType => "ECG_BASELINE";
        public decimal MeasuredVoltage { get; private set; }
        public decimal TargetVoltage { get; private set; }
        public decimal ToleranceMillivolts { get; private set; }
        public int SignalQuality { get; private set; }

        public static ECGBaselineTestResult Create(decimal measuredVoltage, decimal targetVoltage, decimal tolerance, int signalQuality, string technicianId, string notes = null)
        {
            return new ECGBaselineTestResult
            {
                MeasuredVoltage = measuredVoltage,
                TargetVoltage = targetVoltage,
                ToleranceMillivolts = tolerance,
                SignalQuality = signalQuality,
                Status = DetermineStatus(measuredVoltage, targetVoltage, tolerance, signalQuality),
                CompletedAt = DateTime.UtcNow,
                TechnicianId = technicianId,
                Notes = notes
            };
        }

        public override bool IsWithinTolerance()
        {
            var voltageWithinTolerance = Math.Abs(MeasuredVoltage - TargetVoltage) <= ToleranceMillivolts;
            var signalQualityAcceptable = SignalQuality >= 85; // 85% minimum signal quality
            return voltageWithinTolerance && signalQualityAcceptable;
        }

        public override IDictionary<string, object> GetTestParameters()
        {
            return new Dictionary<string, object>
            {
                { "TargetVoltage", TargetVoltage },
                { "ToleranceMillivolts", ToleranceMillivolts },
                { "MinimumSignalQuality", 85 }
            };
        }

        public override IDictionary<string, object> GetTestResults()
        {
            return new Dictionary<string, object>
            {
                { "MeasuredVoltage", MeasuredVoltage },
                { "SignalQuality", SignalQuality },
                { "WithinTolerance", IsWithinTolerance() },
                { "VoltageDeviation", Math.Abs(MeasuredVoltage - TargetVoltage) }
            };
        }

        private static TestStatus DetermineStatus(decimal measured, decimal target, decimal tolerance, int signalQuality)
        {
            var voltageOk = Math.Abs(measured - target) <= tolerance;
            var signalOk = signalQuality >= 85;
            return voltageOk && signalOk ? TestStatus.Passed : TestStatus.Failed;
        }
    }

    public class FlowRateTestResult : TestResultBase
    {
        public override string TestType => "FLOW_RATE";
        public decimal MeasuredFlowRate { get; private set; }
        public decimal TargetFlowRate { get; private set; }
        public decimal TolerancePercentage { get; private set; }
        public string FlowUnit { get; private set; }

        public static FlowRateTestResult Create(decimal measuredFlowRate, decimal targetFlowRate, decimal tolerance, string flowUnit, string technicianId, string notes = null)
        {
            return new FlowRateTestResult
            {
                MeasuredFlowRate = measuredFlowRate,
                TargetFlowRate = targetFlowRate,
                TolerancePercentage = tolerance,
                FlowUnit = flowUnit,
                Status = DetermineStatus(measuredFlowRate, targetFlowRate, tolerance),
                CompletedAt = DateTime.UtcNow,
                TechnicianId = technicianId,
                Notes = notes
            };
        }

        public override bool IsWithinTolerance()
        {
            var deviation = Math.Abs(MeasuredFlowRate - TargetFlowRate);
            var allowedDeviation = TargetFlowRate * (TolerancePercentage / 100);
            return deviation <= allowedDeviation;
        }

        public override IDictionary<string, object> GetTestParameters()
        {
            return new Dictionary<string, object>
            {
                { "TargetFlowRate", TargetFlowRate },
                { "TolerancePercentage", TolerancePercentage },
                { "FlowUnit", FlowUnit }
            };
        }

        public override IDictionary<string, object> GetTestResults()
        {
            return new Dictionary<string, object>
            {
                { "MeasuredFlowRate", MeasuredFlowRate },
                { "FlowUnit", FlowUnit },
                { "WithinTolerance", IsWithinTolerance() },
                { "Deviation", Math.Abs(MeasuredFlowRate - TargetFlowRate) }
            };
        }

        private static TestStatus DetermineStatus(decimal measured, decimal target, decimal tolerance)
        {
            var deviation = Math.Abs(measured - target);
            var allowedDeviation = target * (tolerance / 100);
            return deviation <= allowedDeviation ? TestStatus.Passed : TestStatus.Failed;
        }
    }
}
```

---

## 9. Application Layer Design (Addressing F-001)

### 9.1 Command and Query Definitions

**Maintenance Workflow Commands:**
```csharp
namespace Curetor.Application.Maintenance.Commands
{
    public class StartMaintenanceWorkflowCommand : IRequest<StartMaintenanceWorkflowResponse>
    {
        public string DeviceId { get; set; }
        public MaintenanceType Type { get; set; }
        public string TechnicianId { get; set; }
        public string Notes { get; set; }
    }

    public class StartMaintenanceWorkflowResponse
    {
        public string WorkflowId { get; set; }
        public string DeviceId { get; set; }
        public WorkflowStatus Status { get; set; }
        public DateTime StartedAt { get; set; }
    }

    public class StartMaintenanceWorkflowCommandHandler : IRequestHandler<StartMaintenanceWorkflowCommand, StartMaintenanceWorkflowResponse>
    {
        private readonly IDeviceRepository _deviceRepository;
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly ICurrentUserService _currentUserService;
        private readonly ILogger<StartMaintenanceWorkflowCommandHandler> _logger;

        public StartMaintenanceWorkflowCommandHandler(
            IDeviceRepository deviceRepository,
            IMaintenanceWorkflowRepository workflowRepository,
            ICurrentUserService currentUserService,
            ILogger<StartMaintenanceWorkflowCommandHandler> logger)
        {
            _deviceRepository = deviceRepository;
            _workflowRepository = workflowRepository;
            _currentUserService = currentUserService;
            _logger = logger;
        }

        public async Task<StartMaintenanceWorkflowResponse> Handle(StartMaintenanceWorkflowCommand request, CancellationToken cancellationToken)
        {
            var device = await _deviceRepository.GetByIdAsync(request.DeviceId, cancellationToken);
            if (device == null)
                throw new NotFoundException($"Device {request.DeviceId} not found");

            device.StartMaintenance(request.TechnicianId, request.Type);
            await _deviceRepository.UpdateAsync(device, cancellationToken);

            var workflow = device.MaintenanceHistory.OrderByDescending(w => w.StartedAt).First();
            await _workflowRepository.AddAsync(workflow, cancellationToken);

            _logger.LogInformation("Started maintenance workflow {WorkflowId} for device {DeviceId} by technician {TechnicianId}",
                workflow.WorkflowId, request.DeviceId, request.TechnicianId);

            return new StartMaintenanceWorkflowResponse
            {
                WorkflowId = workflow.WorkflowId,
                DeviceId = workflow.DeviceId,
                Status = workflow.Status,
                StartedAt = workflow.StartedAt
            };
        }
    }

    public class CompleteSanitizationCommand : IRequest<CompleteSanitizationResponse>
    {
        public string WorkflowId { get; set; }
        public string TaskId { get; set; }
        public SanitizationTaskType TaskType { get; set; }
        public bool Passed { get; set; }
        public string Notes { get; set; }
        public List<string> PhotoUrls { get; set; } = new();
    }

    public class CompleteSanitizationResponse
    {
        public string TaskId { get; set; }
        public TaskStatus Status { get; set; }
        public DateTime CompletedAt { get; set; }
    }

    public class CompleteSanitizationCommandHandler : IRequestHandler<CompleteSanitizationCommand, CompleteSanitizationResponse>
    {
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly ISanitizationService _sanitizationService;
        private readonly ILogger<CompleteSanitizationCommandHandler> _logger;

        public CompleteSanitizationCommandHandler(
            IMaintenanceWorkflowRepository workflowRepository,
            ISanitizationService sanitizationService,
            ILogger<CompleteSanitizationCommandHandler> logger)
        {
            _workflowRepository = workflowRepository;
            _sanitizationService = sanitizationService;
            _logger = logger;
        }

        public async Task<CompleteSanitizationResponse> Handle(CompleteSanitizationCommand request, CancellationToken cancellationToken)
        {
            var workflow = await _workflowRepository.GetByIdAsync(request.WorkflowId, cancellationToken);
            if (workflow == null)
                throw new NotFoundException($"Maintenance workflow {request.WorkflowId} not found");

            var sanitizationResult = new SanitizationResult
            {
                TaskType = request.TaskType,
                Passed = request.Passed,
                Notes = request.Notes,
                PhotoUrls = request.PhotoUrls,
                CompletedAt = DateTime.UtcNow
            };

            workflow.CompleteSanitizationTask(request.TaskId, sanitizationResult);
            await _workflowRepository.UpdateAsync(workflow, cancellationToken);

            _logger.LogInformation("Completed sanitization task {TaskId} for workflow {WorkflowId} with status {Status}",
                request.TaskId, request.WorkflowId, sanitizationResult.Passed ? "PASSED" : "FAILED");

            return new CompleteSanitizationResponse
            {
                TaskId = request.TaskId,
                Status = sanitizationResult.Passed ? TaskStatus.Completed : TaskStatus.Failed,
                CompletedAt = sanitizationResult.CompletedAt
            };
        }
    }

    public class CompleteCalibrationTestCommand : IRequest<CompleteCalibrationTestResponse>
    {
        public string WorkflowId { get; set; }
        public string TestId { get; set; }
        public CalibrationTestType TestType { get; set; }
        public Dictionary<string, object> TestParameters { get; set; } = new();
        public Dictionary<string, object> TestResults { get; set; } = new();
        public string Notes { get; set; }
    }

    public class CompleteCalibrationTestResponse
    {
        public string TestId { get; set; }
        public TestStatus Status { get; set; }
        public bool WithinTolerance { get; set; }
        public DateTime CompletedAt { get; set; }
    }

    public class CompleteCalibrationTestCommandHandler : IRequestHandler<CompleteCalibrationTestCommand, CompleteCalibrationTestResponse>
    {
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly ICalibrationService _calibrationService;
        private readonly ILogger<CompleteCalibrationTestCommandHandler> _logger;

        public CompleteCalibrationTestCommandHandler(
            IMaintenanceWorkflowRepository workflowRepository,
            ICalibrationService calibrationService,
            ILogger<CompleteCalibrationTestCommandHandler> logger)
        {
            _workflowRepository = workflowRepository;
            _calibrationService = calibrationService;
            _logger = logger;
        }

        public async Task<CompleteCalibrationTestResponse> Handle(CompleteCalibrationTestCommand request, CancellationToken cancellationToken)
        {
            var workflow = await _workflowRepository.GetByIdAsync(request.WorkflowId, cancellationToken);
            if (workflow == null)
                throw new NotFoundException($"Maintenance workflow {request.WorkflowId} not found");

            // Create appropriate test result based on test type
            TestResultBase testResult = request.TestType switch
            {
                CalibrationTestType.O2Purity => CreateO2PurityTestResult(request),
                CalibrationTestType.ECGBaseline => CreateECGBaselineTestResult(request),
                CalibrationTestType.FlowRate => CreateFlowRateTestResult(request),
                _ => throw new ArgumentException($"Unsupported calibration test type: {request.TestType}")
            };

            var calibrationTestResult = new CalibrationTestResult
            {
                TestType = request.TestType,
                TestResult = testResult,
                CompletedAt = DateTime.UtcNow
            };

            workflow.CompleteCalibrationTest(request.TestId, calibrationTestResult);
            await _workflowRepository.UpdateAsync(workflow, cancellationToken);

            _logger.LogInformation("Completed calibration test {TestId} for workflow {WorkflowId} with status {Status}",
                request.TestId, request.WorkflowId, testResult.Status);

            return new CompleteCalibrationTestResponse
            {
                TestId = request.TestId,
                Status = testResult.Status,
                WithinTolerance = testResult.IsWithinTolerance(),
                CompletedAt = testResult.CompletedAt
            };
        }

        private O2PurityTestResult CreateO2PurityTestResult(CompleteCalibrationTestCommand request)
        {
            var measuredPurity = Convert.ToDecimal(request.TestResults["MeasuredPurity"]);
            var targetPurity = Convert.ToDecimal(request.TestParameters["TargetPurity"]);
            var tolerance = Convert.ToDecimal(request.TestParameters["TolerancePercentage"]);
            
            return O2PurityTestResult.Create(measuredPurity, targetPurity, tolerance, request.WorkflowId, request.Notes);
        }

        private ECGBaselineTestResult CreateECGBaselineTestResult(CompleteCalibrationTestCommand request)
        {
            var measuredVoltage = Convert.ToDecimal(request.TestResults["MeasuredVoltage"]);
            var targetVoltage = Convert.ToDecimal(request.TestParameters["TargetVoltage"]);
            var tolerance = Convert.ToDecimal(request.TestParameters["ToleranceMillivolts"]);
            var signalQuality = Convert.ToInt32(request.TestResults["SignalQuality"]);
            
            return ECGBaselineTestResult.Create(measuredVoltage, targetVoltage, tolerance, signalQuality, request.WorkflowId, request.Notes);
        }

        private FlowRateTestResult CreateFlowRateTestResult(CompleteCalibrationTestCommand request)
        {
            var measuredFlowRate = Convert.ToDecimal(request.TestResults["MeasuredFlowRate"]);
            var targetFlowRate = Convert.ToDecimal(request.TestParameters["TargetFlowRate"]);
            var tolerance = Convert.ToDecimal(request.TestParameters["TolerancePercentage"]);
            var flowUnit = request.TestParameters["FlowUnit"].ToString();
            
            return FlowRateTestResult.Create(measuredFlowRate, targetFlowRate, tolerance, flowUnit, request.WorkflowId, request.Notes);
        }
    }

    public class CompleteTelemetryTestCommand : IRequest<CompleteTelemetryTestResponse>
    {
        public string WorkflowId { get; set; }
        public string TestId { get; set; }
        public TelemetryTestType TestType { get; set; }
        public Dictionary<string, object> TestResults { get; set; } = new();
        public string Notes { get; set; }
    }

    public class CompleteTelemetryTestResponse
    {
        public string TestId { get; set; }
        public TestStatus Status { get; set; }
        public DateTime CompletedAt { get; set; }
    }

    public class CompleteTelemetryTestCommandHandler : IRequestHandler<CompleteTelemetryTestCommand, CompleteTelemetryTestResponse>
    {
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly ITelemetryService _telemetryService;
        private readonly ILogger<CompleteTelemetryTestCommandHandler> _logger;

        public CompleteTelemetryTestCommandHandler(
            IMaintenanceWorkflowRepository workflowRepository,
            ITelemetryService telemetryService,
            ILogger<CompleteTelemetryTestCommandHandler> logger)
        {
            _workflowRepository = workflowRepository;
            _telemetryService = telemetryService;
            _logger = logger;
        }

        public async Task<CompleteTelemetryTestResponse> Handle(CompleteTelemetryTestCommand request, CancellationToken cancellationToken)
        {
            var workflow = await _workflowRepository.GetByIdAsync(request.WorkflowId, cancellationToken);
            if (workflow == null)
                throw new NotFoundException($"Maintenance workflow {request.WorkflowId} not found");

            var telemetryTestResult = new TelemetryTestResult
            {
                TestType = request.TestType,
                TestResults = request.TestResults,
                Status = DetermineTelemetryTestStatus(request.TestType, request.TestResults),
                CompletedAt = DateTime.UtcNow,
                Notes = request.Notes
            };

            workflow.CompleteTelemetryTest(request.TestId, telemetryTestResult);
            await _workflowRepository.UpdateAsync(workflow, cancellationToken);

            _logger.LogInformation("Completed telemetry test {TestId} for workflow {WorkflowId} with status {Status}",
                request.TestId, request.WorkflowId, telemetryTestResult.Status);

            return new CompleteTelemetryTestResponse
            {
                TestId = request.TestId,
                Status = telemetryTestResult.Status,
                CompletedAt = telemetryTestResult.CompletedAt
            };
        }

        private TestStatus DetermineTelemetryTestStatus(TelemetryTestType testType, Dictionary<string, object> testResults)
        {
            return testType switch
            {
                TelemetryTestType.CellularConnectivity => DetermineCellularTestStatus(testResults),
                TelemetryTestType.WiFiConnectivity => DetermineWiFiTestStatus(testResults),
                TelemetryTestType.BatteryHealth => DetermineBatteryTestStatus(testResults),
                TelemetryTestType.DataTransmission => DetermineDataTransmissionTestStatus(testResults),
                _ => TestStatus.Failed
            };
        }

        private TestStatus DetermineCellularTestStatus(Dictionary<string, object> results)
        {
            var signalStrength = Convert.ToInt32(results["SignalStrength"]);
            var connectionEstablished = Convert.ToBoolean(results["ConnectionEstablished"]);
            
            return connectionEstablished && signalStrength >= -85 ? TestStatus.Passed : TestStatus.Failed;
        }

        private TestStatus DetermineWiFiTestStatus(Dictionary<string, object> results)
        {
            var signalStrength = Convert.ToInt32(results["SignalStrength"]);
            var connectionEstablished = Convert.ToBoolean(results["ConnectionEstablished"]);
            var dataRate = Convert.ToDecimal(results["DataRate"]);
            
            return connectionEstablished && signalStrength >= -70 && dataRate >= 1.0m ? TestStatus.Passed : TestStatus.Failed;
        }

        private TestStatus DetermineBatteryTestStatus(Dictionary<string, object> results)
        {
            var batteryPercentage = Convert.ToDecimal(results["BatteryPercentage"]);
            var cycleCount = Convert.ToInt32(results["CycleCount"]);
            var voltage = Convert.ToDecimal(results["Voltage"]);
            
            return batteryPercentage >= 80 && cycleCount <= 500 && voltage >= 3.7m ? TestStatus.Passed : TestStatus.Failed;
        }

        private TestStatus DetermineDataTransmissionTestStatus(Dictionary<string, object> results)
        {
            var transmissionSuccessful = Convert.ToBoolean(results["TransmissionSuccessful"]);
            var dataIntegrity = Convert.ToBoolean(results["DataIntegrity"]);
            var latency = Convert.ToInt32(results["LatencyMs"]);
            
            return transmissionSuccessful && dataIntegrity && latency <= 5000 ? TestStatus.Passed : TestStatus.Failed;
        }
    }

    public class CompleteMaintenanceWorkflowCommand : IRequest<CompleteMaintenanceWorkflowResponse>
    {
        public string WorkflowId { get; set; }
        public string CompletionNotes { get; set; }
    }

    public class CompleteMaintenanceWorkflowResponse
    {
        public string WorkflowId { get; set; }
        public string DeviceId { get; set; }
        public WorkflowStatus Status { get; set; }
        public DateTime CompletedAt { get; set; }
    }

    public class CompleteMaintenanceWorkflowCommandHandler : IRequestHandler<CompleteMaintenanceWorkflowCommand, CompleteMaintenanceWorkflowResponse>
    {
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly IDeviceRepository _deviceRepository;
        private readonly ILogger<CompleteMaintenanceWorkflowCommandHandler> _logger;

        public CompleteMaintenanceWorkflowCommandHandler(
            IMaintenanceWorkflowRepository workflowRepository,
            IDeviceRepository deviceRepository,
            ILogger<CompleteMaintenanceWorkflowCommandHandler> logger)
        {
            _workflowRepository = workflowRepository;
            _deviceRepository = deviceRepository;
            _logger = logger;
        }

        public async Task<CompleteMaintenanceWorkflowResponse> Handle(CompleteMaintenanceWorkflowCommand request, CancellationToken cancellationToken)
        {
            var workflow = await _workflowRepository.GetByIdAsync(request.WorkflowId, cancellationToken);
            if (workflow == null)
                throw new NotFoundException($"Maintenance workflow {request.WorkflowId} not found");

            var device = await _deviceRepository.GetByIdAsync(workflow.DeviceId, cancellationToken);
            if (device == null)
                throw new NotFoundException($"Device {workflow.DeviceId} not found");

            workflow.Complete();
            device.CompleteMaintenance(request.WorkflowId);

            await _workflowRepository.UpdateAsync(workflow, cancellationToken);
            await _deviceRepository.UpdateAsync(device, cancellationToken);

            _logger.LogInformation("Completed maintenance workflow {WorkflowId} for device {DeviceId}",
                request.WorkflowId, workflow.DeviceId);

            return new CompleteMaintenanceWorkflowResponse
            {
                WorkflowId = workflow.WorkflowId,
                DeviceId = workflow.DeviceId,
                Status = workflow.Status,
                CompletedAt = workflow.CompletedAt.Value
            };
        }
    }
}
```

### 9.2 Query Definitions

**Maintenance Workflow Queries:**
```csharp
namespace Curetor.Application.Maintenance.Queries
{
    public class GetMaintenanceWorkflowQuery : IRequest<MaintenanceWorkflowDto>
    {
        public string WorkflowId { get; set; }
    }

    public class GetMaintenanceWorkflowQueryHandler : IRequestHandler<GetMaintenanceWorkflowQuery, MaintenanceWorkflowDto>
    {
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly IMapper _mapper;

        public GetMaintenanceWorkflowQueryHandler(IMaintenanceWorkflowRepository workflowRepository, IMapper mapper)
        {
            _workflowRepository = workflowRepository;
            _mapper = mapper;
        }

        public async Task<MaintenanceWorkflowDto> Handle(GetMaintenanceWorkflowQuery request, CancellationToken cancellationToken)
        {
            var workflow = await _workflowRepository.GetByIdWithDetailsAsync(request.WorkflowId, cancellationToken);
            if (workflow == null)
                throw new NotFoundException($"Maintenance workflow {request.WorkflowId} not found");

            return _mapper.Map<MaintenanceWorkflowDto>(workflow);
        }
    }

    public class GetDeviceMaintenanceHistoryQuery : IRequest<List<MaintenanceWorkflowSummaryDto>>
    {
        public string DeviceId { get; set; }
        public int PageNumber { get; set; } = 1;
        public int PageSize { get; set; } = 20;
    }

    public class GetDeviceMaintenanceHistoryQueryHandler : IRequestHandler<GetDeviceMaintenanceHistoryQuery, List<MaintenanceWorkflowSummaryDto>>
    {
        private readonly IMaintenanceWorkflowRepository _workflowRepository;
        private readonly IMapper _mapper;

        public GetDeviceMaintenanceHistoryQueryHandler(IMaintenanceWorkflowRepository workflowRepository, IMapper mapper)
        {
            _workflowRepository = workflowRepository;
            _mapper = mapper;
        }

        public async Task<List<MaintenanceWorkflowSummaryDto>> Handle(GetDeviceMaintenanceHistoryQuery request, CancellationToken cancellationToken)
        {
            var workflows = await _workflowRepository.GetByDeviceIdAsync(
                request.DeviceId, 
                request.PageNumber, 
                request.PageSize, 
                cancellationToken);

            return _mapper.Map<List<MaintenanceWorkflowSummaryDto>>(workflows);
        }
    }

    public class GetDevicesNeedingMaintenanceQuery : IRequest<PagedResult<DeviceSummaryDto>>
    {
        public string SearchTerm { get; set; }
        public DeviceStatus? StatusFilter { get; set; }
        public string ManufacturerFilter { get; set; }
        public int PageNumber { get; set; } = 1;
        public int PageSize { get; set; } = 50;
    }

    public class GetDevicesNeedingMaintenanceQueryHandler : IRequestHandler<GetDevicesNeedingMaintenanceQuery, PagedResult<DeviceSummaryDto>>
    {
        private readonly IDeviceRepository _deviceRepository;
        private readonly IMapper _mapper;

        public GetDevicesNeedingMaintenanceQueryHandler(IDeviceRepository deviceRepository, IMapper mapper)
        {
            _deviceRepository = deviceRepository;
            _mapper = mapper;
        }

        public async Task<PagedResult<DeviceSummaryDto>> Handle(GetDevicesNeedingMaintenanceQuery request, CancellationToken cancellationToken)
        {
            var devices = await _deviceRepository.GetDevicesNeedingMaintenanceAsync(
                request.SearchTerm,
                request.StatusFilter,
                request.ManufacturerFilter,
                request.PageNumber,
                request.PageSize,
                cancellationToken);

            var deviceDtos = _mapper.Map<List<DeviceSummaryDto>>(devices.Items);

            return new PagedResult<DeviceSummaryDto>
            {
                Items = deviceDtos,
                TotalCount = devices.TotalCount,
                PageNumber = devices.PageNumber,
                PageSize = devices.PageSize
            };
        }
    }
}
```

### 9.3 Data Transfer Objects

**DTOs for API Contracts:**
```csharp
namespace Curetor.Application.Maintenance.DTOs
{
    public class MaintenanceWorkflowDto
    {
        public string WorkflowId { get; set; }
        public string DeviceId { get; set; }
        public string TechnicianId { get; set; }
        public MaintenanceType Type { get; set; }
        public WorkflowStatus Status { get; set; }
        public DateTime StartedAt { get; set; }
        public DateTime? CompletedAt { get; set; }
        public List<SanitizationTaskDto> SanitizationTasks { get; set; } = new();
        public List<CalibrationTestDto> CalibrationTests { get; set; } = new();
        public List<TelemetryTestDto> TelemetryTests { get; set; } = new();
        public List<WorkflowDocumentDto> Documents { get; set; } = new();
    }

    public class MaintenanceWorkflowSummaryDto
    {
        public string WorkflowId { get; set; }
        public string DeviceId { get; set; }
        public MaintenanceType Type { get; set; }
        public WorkflowStatus Status { get; set; }
        public DateTime StartedAt { get; set; }
        public DateTime? CompletedAt { get; set; }
        public string TechnicianName { get; set; }
        public int TasksCompleted { get; set; }
        public int TotalTasks { get; set; }
    }

    public class DeviceSummaryDto
    {
        public string DeviceId { get; set; }
        public string SerialNumber { get; set; }
        public string ModelId { get; set; }
        public string ManufacturerName { get; set; }
        public DeviceStatus Status { get; set; }
        public DateTime? LastMaintenanceDate { get; set; }
        public DateTime? NextCalibrationDue { get; set; }
        public bool NeedsMaintenance { get; set; }
        public string MaintenanceReason { get; set; }
    }

    public class SanitizationTaskDto
    {
        public string TaskId { get; set; }
        public SanitizationTaskType TaskType { get; set; }
        public string Description { get; set; }
        public TaskStatus Status { get; set; }
        public DateTime? CompletedAt { get; set; }
        public bool? Passed { get; set; }
        public string Notes { get; set; }
        public List<string> PhotoUrls { get; set; } = new();
    }

    public class CalibrationTestDto
    {
        public string TestId { get; set; }
        public CalibrationTestType TestType { get; set; }
        public TestStatus Status { get; set; }
        public DateTime? CompletedAt { get; set; }
        public bool? WithinTolerance { get; set; }
        public Dictionary<string, object> TestParameters { get; set; } = new();
        public Dictionary<string, object> TestResults { get; set; } = new();
        public string Notes { get; set; }
    }

    public class TelemetryTestDto
    {
        public string TestId { get; set; }
        public TelemetryTestType TestType { get; set; }
        public TestStatus Status { get; set; }
        public DateTime? CompletedAt { get; set; }
        public Dictionary<string, object> TestResults { get; set; } = new();
        public string Notes { get; set; }
    }

    public class WorkflowDocumentDto
    {
        public string DocumentId { get; set; }
        public string FileName { get; set; }
        public string FileUrl { get; set; }
        public DocumentType DocumentType { get; set; }
        public DateTime UploadedAt { get; set; }
        public long FileSizeBytes { get; set; }
        public string ContentType { get; set; }
    }

    public class PagedResult<T>
    {
        public List<T> Items { get; set; } = new();
        public int TotalCount { get; set; }
        public int PageNumber { get; set; }
        public int PageSize { get; set; }
        public int TotalPages => (int)Math.Ceiling((double)TotalCount / PageSize);
        public bool HasNextPage => PageNumber < TotalPages;
        public bool HasPreviousPage => PageNumber > 1;
    }
}
```

---

## 10. Security & Authorization Framework (Addressing F-004, F-005, F-006)

### 10.1 Authorization Policy Implementation

**Authorization Policies:**
```csharp
namespace Curetor.Infrastructure.Authorization
{
    public static class MaintenancePolicies
    {
        public const string SameTenant = "SameTenant";
        public const string MaintenanceAccess = "MaintenanceAccess";
        public const string MaintenanceTechnician = "MaintenanceTechnician";
        public const string MaintenanceSupervisor = "MaintenanceSupervisor";
        public const string DeviceAccess = "DeviceAccess";
        public const string WorkflowAccess = "WorkflowAccess";
    }

    public class SameTenantAuthorizationHandler : AuthorizationHandler<SameTenantRequirement, ITenantEntity>
    {
        private readonly ICurrentUserService _currentUserService;
        private readonly ILogger<SameTenantAuthorizationHandler> _logger;

        public SameTenantAuthorizationHandler(ICurrentUserService currentUserService, ILogger<SameTenantAuthorizationHandler> logger)
        {
            _currentUserService = currentUserService;
            _logger = logger;
        }

        protected override Task HandleRequirementAsync(AuthorizationHandlerContext context, SameTenantRequirement requirement, ITenantEntity resource)
        {
            var currentTenantId = _currentUserService.TenantId;
            
            if (string.IsNullOrEmpty(currentTenantId))
            {
                _logger.LogWarning("Authorization failed: No tenant ID found for user {UserId}", _currentUserService.UserId);
                context.Fail();
                return Task.CompletedTask;
            }

            if (resource.TenantId != currentTenantId)
            {
                _logger.LogWarning("Authorization failed: Tenant mismatch. User tenant: {UserTenant}, Resource tenant: {ResourceTenant}", 
                    currentTenantId, resource.TenantId);
                context.Fail();
                return Task.CompletedTask;
            }

            context.Succeed(requirement);
            return Task.CompletedTask;
        }
    }

    public class MaintenanceAccessAuthorizationHandler : AuthorizationHandler<MaintenanceAccessRequirement>
    {
        private readonly ICurrentUserService _currentUserService;
        private readonly ILogger<MaintenanceAccessAuthorizationHandler> _logger;

        public MaintenanceAccessAuthorizationHandler(ICurrentUserService currentUserService, ILogger<MaintenanceAccessAuthorizationHandler> logger)
        {
            _currentUserService = currentUserService;
            _logger = logger;
        }

        protected override Task HandleRequirementAsync(AuthorizationHandlerContext context, MaintenanceAccessRequirement requirement)
        {
            var userRoles = _currentUserService.Roles;
            
            var hasMaintenanceRole = userRoles.Any(role => 
                role == "MaintenanceTechnician" || 
                role == "MaintenanceSupervisor" || 
                role == "SystemAdministrator");

            if (!hasMaintenanceRole)
            {
                _logger.LogWarning("Authorization failed: User {UserId} does not have maintenance access. Roles: {Roles}", 
                    _currentUserService.UserId, string.Join(", ", userRoles));
                context.Fail();
                return Task.CompletedTask;
            }

            context.Succeed(requirement);
            return Task.CompletedTask;
        }
    }

    public class DeviceAccessAuthorizationHandler : AuthorizationHandler<DeviceAccessRequirement, Device>
    {
        private readonly ICurrentUserService _currentUserService;
        private readonly IDevicePermissionService _devicePermissionService;
        private readonly ILogger<DeviceAccessAuthorizationHandler> _logger;

        public DeviceAccessAuthorizationHandler(
            ICurrentUserService currentUserService, 
            IDevicePermissionService devicePermissionService,
            ILogger<DeviceAccessAuthorizationHandler> logger)
        {
            _currentUserService = currentUserService;
            _devicePermissionService = devicePermissionService;
            _logger = logger;
        }

        protected override async Task HandleRequirementAsync(AuthorizationHandlerContext context, DeviceAccessRequirement requirement, Device device)
        {
            var userId = _currentUserService.UserId;
            var tenantId = _currentUserService.TenantId;

            // Check tenant isolation first
            if (device.TenantId != tenantId)
            {
                _logger.LogWarning("Authorization failed: Device {DeviceId} belongs to different tenant", device.DeviceId);
                context.Fail();
                return;
            }

            // Check device-specific permissions
            var hasDeviceAccess = await _devicePermissionService.HasDeviceAccessAsync(userId, device.DeviceId);
            if (!hasDeviceAccess)
            {
                _logger.LogWarning("Authorization failed: User {UserId} does not have access to device {DeviceId}", userId, device.DeviceId);
                context.Fail();
                return;
            }

            context.Succeed(requirement);
        }
    }

    public class WorkflowAccessAuthorizationHandler : AuthorizationHandler<WorkflowAccessRequirement, MaintenanceWorkflow>
    {
        private readonly ICurrentUserService _currentUserService;
        private readonly ILogger<WorkflowAccessAuthorizationHandler> _logger;

        public Workfl