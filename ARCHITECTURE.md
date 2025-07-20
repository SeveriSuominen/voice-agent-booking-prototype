# Cloud Architechture Plan

## Table of Contents
- [Intro](#intro)
- [Diagram](#diagram)
- [Requirements Traceability](#requirements-traceability)
- [System Overview](#system-overview)
- [Proposed Technology Stack](#proposed-technology-stack)
- [Key Components](#key-components)
  - [Telephony (Azure Communication Services)](#telephony-azure-communication-services)
  - [Azure Functions (Business Logic)](#azure-functions-business-logic)
  - [AI/NLP & Speech Services](#ainlp--speech-services)
  - [Azure Cache for Redis](#azure-cache-for-redis)
  - [Data Storage & FHIR API Integration](#data-storage--fhir-api-integration)
  - [Application Gateway with SSL/TLS & WAF](#application-gateway-with-ssl-tls-and-waf)
  - [Networking (VNets, Subnets, NSGs)](#networking-vnets-subnets-nsgs)
  - [Monitoring & Telemetry](#monitoring--telemetry)
- [Security & Privacy](#security--privacy)
  - [Encryption](#encryption)
  - [Network Defense](#network-defense)
  - [Application Security](#application-security)
  - [GDPR Compliance](#gdpr-compliance)
- [Performance & Scalability](#performance--scalability)
- [Author](#author)

## Intro 

This is a cloud architecture plan for creating a cost‑efficient, robust, and secure voice‑agent service that communicates with various healthcare clinics to safely make appointments and request sensitive patient data, while conforming to GDPR and other relevant regulations.

As the sole purpose of this document is to demonstrate my architectural design skills, it is intentionally kept minimal and focused on highlighting the most important points and requirements.

## Diagram

<img src="docs/architecture.svg"
     alt="Diagram description"
     style="display: block; width: 100%; height: auto;" />

## Requirements Traceability
| Requirement                  | Implementation Summary                                                                 |
|------------------------------|----------------------------------------------------------------------------------------|
| 10,000 calls/month           | Serverless pricing and auto-scaling of Azure Functions and ACS cover this volume.      |
| 100 concurrent calls         | Functions handle 20–40 sessions/instance; scaling to 5 instances meets peak demand.    |
| Low latency (<1.6s)          | Real-time STT/TTS streaming, Redis caching, and regional deployment minimize latency.  |
| Finnish language support     | Azure Cognitive Speech STT/TTS supports Finnish; LLM handles Finnish text.             |
| Secure PHI handling (GDPR)   | Encryption, private subnets, AuthN/Z, audit logs, and data retention policies.         |
| OWASP Top 10 protection      | Application Gateway WAF inspects traffic; NSGs enforce network-layer restrictions.     |
| FHIR/REST clinic integration | Secure HTTPS, OAuth/Managed Identity, and standardized FHIR messages.                  |

## System Overview

Incoming appointment-booking calls enter via Azure Communication Services (ACS) PSTN telephony. ACS’s Call Automation workflow answers the call and streams audio to our backend. An Azure Function handles the call logic in a loop: it transcribes the caller’s Finnish speech using Azure Speech-to-Text, processes it with an AI/NLP agent (e.g., Azure OpenAI), and invokes booking actions as needed.

The agent can call external clinic scheduling APIs (FHIR/REST) to query availability and create appointments. The response is synthesized back to speech using Text-to-Speech and played to the caller via ACS. All steps (call events, transcripts, decisions, bookings) are logged to databases for audit and analytics. This real-time “hear → think → act → respond” loop ensures natural dialog with sub-1.6s turnaround per exchange.

## Proposed Technology Stack

- **Backend Languages:**  
  Python for rapid prototyping and service orchestration; Go and Rust for performance‑critical microservices (e.g. speech processing, concurrency); For special occasions Zig as a future candidate once it reaches production maturity.

- **Azure Services (Infra & Platform):**  
  - Azure Communication Services (PSTN calling)  
  - Azure Functions (business logic)  
  - Azure Cache for Redis (low‑latency caching)  
  - Azure SQL Database (structured data)  
  - Azure Blob Storage / Cosmos DB (unstructured logs)  
  - Application Gateway with SSL/TLS termination and Web Application Firewall  
  - Virtual Networks & Subnets with NSGs  
  - Azure Monitor & Application Insights  

- **Front‑End:**  
  SvelteJS for admin and monitoring dashboards, as well as potential user‑facing interfaces, chosen for its lightweight bundle size and developer productivity.

These choices are driven by their rich and modern ecosystems, cost-effectiveness, proven security and battle‑tested stability, and vibrant talent markets—ensuring maintainability and ease of future hiring.

## Key Components

### Telephony (Azure Communication Services)
We use ACS with PSTN calling to handle incoming phone calls without on-prem hardware. The Call Automation SDK lets us answer calls, play prompts, capture speech/DTMF, and control call flow programmatically. ACS provides a complete voice pipeline: receiving the call and routing audio bi-directionally to our application.

### Azure Functions (Business Logic)
Core call control and booking logic run in Azure Functions. Each function instance can handle approximately 20–40 concurrent sessions and auto-scales based on load. At peak demand of 100 concurrent calls, 3–5 instances suffice. Functions connect to Cognitive Services and external APIs, managing conversation state with durable storage or Redis cache.

### AI/NLP & Speech Services
Azure Cognitive Speech supports Finnish speech-to-text and neural text-to-speech voices. Incoming audio streams to STT for real-time transcription, and bot responses synthesize back to speech. The AI layer (Azure OpenAI or Bot Framework with LUIS) interprets intents and slots, invoking booking plugins as needed.

### Azure Cache for Redis
Redis cache accelerates session state and frequently accessed data with sub-millisecond retrieval. Caching reduces latency and database load, helping maintain overall response times below 1.6s.

### Data Storage & FHIR API Integration
Structured data (booking metadata, transcripts) lives in Azure SQL Database with Transparent Data Encryption. Unstructured logs and recordings use Blob Storage or Cosmos DB. External clinic integration leverages FHIR/REST APIs over HTTPS with OAuth or Managed Identity for secure access to electronic health records.

### Application Gateway with SSL/TLS & WAF
An Azure Application Gateway terminates TLS, enforcing TLS1.2+/1.3 policies and retrieving certificates from Key Vault. The integrated Web Application Firewall inspects HTTP(S) traffic against [OWASP Top 10 rules](https://owasp.org/www-project-top-ten/), blocking SQL injection, XSS, and other common web attacks.

### Networking (VNets, Subnets, NSGs)
Resources reside in a Virtual Network segmented into subnets (Gateway, App, Data, Management). Network Security Groups restrict traffic: only necessary ports and protocols are allowed. Databases and caches are in private subnets without public IPs, and all external access goes through the Application Gateway or VPN.

### Monitoring & Telemetry
Azure Monitor and Application Insights collect logs and metrics from Functions, AI services, and databases. Alerts on latency or errors help maintain SLAs. Audit logs track all personal data access for compliance.

## Security & Privacy

### Encryption

All data in transit is protected by TLS. Data at rest is encrypted by default in Azure SQL, Blob Storage, and Cosmos DB. Secrets and certificates are stored in Azure Key Vault with HSM-backed protection.

### Network Defense
Layered defenses include the Application Gateway WAF, NSGs on subnets, and optional Azure DDoS Protection. Only proven traffic flows are permitted, preventing lateral movement and common attacks.

### Application Security
APIs require authentication via Azure AD or OAuth. Input is validated, parameterized queries prevent injection, and functions run with minimal privileges. Managed Identities handle service-to-service authentication.

### GDPR Compliance
We minimize stored personal data, retain recordings only as necessary, and implement automated retention policies. Patients are informed of processing, and the system supports data subject requests for access, erasure, and portability. Audit trails document all data operations.

## Performance & Scalability

The serverless Azure Functions model auto-scales to meet demand. With each instance handling 20–40 (conservative estimation) concurrent sessions, scaling to 100 calls requires only a handful of instances. Real-time STT/TTS streaming and Redis caching keep processing times low, ensuring each user-agent exchange remains under 1.6 seconds.

## Author

Severi Suominen - 2025
