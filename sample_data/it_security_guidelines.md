# Global Information Security Standards and Acceptable Use Policy

## 1. Authentication and Access Control
- **Multi-Factor Authentication (MFA)**: Mandatory for all corporate systems (Okta, AWS, GitHub Enterprise, Google Workspace). Hardware security keys (FIDO2 WebAuthn / YubiKey) or Okta Verify push notifications are required. SMS-based 2FA is strictly prohibited.
- **Password Complexity**: Passwords must contain a minimum of 16 characters with at least one uppercase letter, one number, and one special character.
- **Password Rotation**: Passwords must be updated every 90 days. Password reuse across personal and corporate accounts is a critical violation.

## 2. Device Security & Endpoint Protection
- **Full Disk Encryption**: FileVault (macOS) or BitLocker (Windows) must remain enabled at all times.
- **Endpoint Agent**: CrowdStrike Falcon and Jamf Pro / Microsoft Intune management agents must remain active. Disabling or tampering with security agents will trigger automated network isolation.
- **Screen Lock Timeout**: Inactivity lock screen timeout must be set to no more than 5 minutes.

## 3. Data Classification and S3 Storage Rules
- **Confidential / Restricted Data**: Customer PII, source code, financial ledger records, and cryptographic credentials must be encrypted at rest (AES-256 or AWS KMS CMK) and in transit (TLS 1.3).
- **Public S3 Buckets**: Public read/write permissions on any AWS S3 bucket are strictly forbidden. AWS S3 Block Public Access must be enabled account-wide.
- **Removable Media**: USB storage drives and external hard drives must be hardware-encrypted with approved BitLocker/APFS encryption.

## 4. Security Incident Reporting
- Any suspected security incident, phishing attempt, lost laptop, or compromised credential must be reported immediately to the Security Operations Center (SOC) at `security-incident@company.com` or via Slack channel `#soc-alert`.
