# Security Policy

## Supported versions

Ragforge is pre-1.0 and under active development. Only the latest code on `main` gets security fixes. There are no backports to earlier releases yet.

| Version | Supported |
|---|---|
| `main` (latest) | Yes |
| Anything older | No |

## Reporting a vulnerability

**Please do not report security vulnerabilities in public issues, pull requests or Discussions.**

You can report one privately in either of these ways:

1. **GitHub private vulnerability reporting (preferred).** Open the [Security tab](https://github.com/KrushanPatel/ragforge/security) and choose **Report a vulnerability**. The report stays private between you and the maintainers.
2. **Email.** Send the details to [krushanpatel2@gmail.com](mailto:krushanpatel2@gmail.com) with `[ragforge security]` in the subject.

Please include:

- A description of the issue and its impact.
- Steps to reproduce it, or a proof of concept.
- The commit or version you tested.
- Any suggested fix or mitigation.

## What to expect

- We'll acknowledge your report within **3 business days**.
- We'll give you an initial assessment and next steps within **10 business days**.
- We'll keep you updated until the issue is fixed, then publish a GitHub Security Advisory. You'll be credited unless you ask us not to credit you.

Please give us a reasonable amount of time to release a fix before you disclose the issue publicly.

## Scope

In scope: code in this repository, and the configuration and deployment manifests it ships.

Out of scope: vulnerabilities in third-party dependencies (report those upstream; Dependabot tracks them here), and issues that require an already-compromised host.
