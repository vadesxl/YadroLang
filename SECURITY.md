# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.4.x   | Yes       |
| < 1.4   | No        |

## Reporting a Vulnerability

If you discover a security vulnerability in YadroLang, please report it responsibly:

1. **Do NOT open a public issue**
2. Email: [security contact - add your email]
3. Include: description, steps to reproduce, potential impact
4. Expected response time: 48 hours

## Security Model

YadroLang's Ethical Analyzer provides compile-time security guarantees:

- **Capability Mandates** - functions must declare side-effect permissions
- **Taint Analysis** - tracks sensitive data flow (PII, Financial, Health, Credentials, Location)
- **Implicit Flow Detection** - blocks side-channel leaks through control flow
- **UB Prevention** - division by zero and integer overflow caught at compile time

These guarantees are enforced at compile time. If the code compiles, it is compliant.
