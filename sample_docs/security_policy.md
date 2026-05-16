---
title: Security & Compliance Policy
category: Security
author: Security Team
last_updated: 2024-03-15
---

# Security & Compliance Policy

This document outlines the organization's security requirements and compliance obligations.

## Access Control

### Principle of Least Privilege
All employees are granted the minimum access required to perform their job functions. Access is reviewed quarterly and revoked immediately upon role change or termination.

### Authentication Requirements
- All company accounts must use strong passwords (minimum 16 characters)
- Multi-factor authentication (MFA) is mandatory for all systems
- Password managers (1Password) are provided to all employees at no cost
- Shared credentials are strictly prohibited

### VPN Policy
Remote access to internal systems requires VPN. The company uses WireGuard VPN:
- Install the client from IT portal
- Connect before accessing any internal resources
- VPN logs are retained for 90 days for security monitoring

## Data Classification

| Level | Description | Examples | Handling |
|-------|-------------|----------|----------|
| Public | Approved for external use | Marketing materials, public docs | No restrictions |
| Internal | Internal use only | Policies, org charts | Internal systems only |
| Confidential | Sensitive business data | Customer data, financials | Encrypted, need-to-know |
| Restricted | Highest sensitivity | PII, source code, secrets | Strict controls, logged access |

## Incident Response

### Reporting a Security Incident
Report immediately via:
1. **Slack**: `#security-incidents` channel (24/7 monitored)
2. **Email**: security@company.com
3. **Phone**: Security hotline ext. 911 (business hours)

**Never** attempt to investigate or remediate a security incident on your own.

### What Constitutes an Incident
- Suspected phishing or social engineering
- Unauthorized access to systems or data
- Lost or stolen company devices
- Malware detection
- Data exposure or breach

### Response Timeline
- Initial acknowledgment: 1 hour
- Preliminary assessment: 4 hours
- Escalation (if needed): 8 hours
- Post-incident report: 5 business days

## Acceptable Use Policy

### Company Devices
Company devices are for business use. Limited personal use is acceptable provided it:
- Does not compromise security
- Does not involve illegal content
- Does not significantly impact productivity

**Prohibited**: Installing unauthorized software, disabling security tools, using P2P/torrents.

### Data Handling
- Customer PII must never be stored locally — use approved cloud storage only
- Confidential data must be encrypted at rest and in transit
- Do not share confidential data via personal email or unsanctioned tools
- Cloud storage: only Google Drive (company account) or approved alternatives

## Compliance Requirements

The organization is subject to:
- **SOC 2 Type II**: Annual audit, all employees must complete security training
- **GDPR**: Applies to EU customer data; Data Protection Officer contact: dpo@company.com
- **CCPA**: California consumer privacy rights compliance required
- **PCI DSS**: For any systems handling payment card data (Level 3 merchant)

### Annual Security Training
All employees must complete:
1. Security awareness training (2 hours, online)
2. Phishing simulation exercises (quarterly)
3. Role-specific training (engineers: OWASP Top 10; finance: fraud prevention)

Deadline: Training must be completed within 30 days of hire and annually thereafter.

## Physical Security

### Office Access
- Badge required for all office entry
- Tailgating is prohibited — do not hold doors
- Visitors must be escorted at all times
- Report lost badges to security@company.com immediately

### Clean Desk Policy
When leaving your desk:
- Lock your computer screen (Windows: Win+L, Mac: Cmd+Ctrl+Q)
- Secure confidential documents in locked drawers
- Do not leave sensitive information visible on whiteboards

## Vendor & Third-Party Security

All vendors with access to company data must:
- Complete a security questionnaire before engagement
- Sign a Data Processing Agreement (DPA)
- Provide evidence of SOC 2 or equivalent certification
- Notify us within 24 hours of any breach affecting our data

Contact procurement@company.com before granting any third-party system access.
