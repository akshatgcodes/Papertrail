# Security Policy

## Supported versions

Only the latest version on `main` receives security fixes. There is no public deployment yet.

| Version | Supported |
|---|---|
| Latest (`main`) | ✅ |
| Older releases | ❌ |

---

## Reporting a vulnerability

**Please don't open a public issue for security problems.**

Report privately through either channel:

1. **GitHub:** go to the [Security tab → Report a vulnerability](../../security/advisories/new) (preferred)
2. **Email:** [akshatgcodes@gmail.com](mailto:akshatgcodes@gmail.com) with the subject `Security: Papertrail`

Please include:

- What the issue is and where it lives (URL, endpoint, file)
- Steps to reproduce, or a minimal proof of concept
- The impact you think it has
- Any suggested fix (optional)

---

## What to expect

| Step | Timeline |
|---|---|
| Acknowledgement of your report | within **72 hours** |
| Initial assessment and severity | within **7 days** |
| Fix released for confirmed issues | as soon as possible, based on severity |

You'll be kept updated throughout, and credited in the release notes once it's fixed (unless you'd rather stay anonymous).

---

## Scope

**In scope**

- This repository's source code
- Login and session cookies (`backend/app/auth.py`)
- Reading, changing or deleting documents or history without the session
- Making the server fetch an internal address through URL import (`check_public_url` and `fetch` in `backend/app/ingest/web.py`, including redirects)
- Files that escape the data directory, or a PDF that crashes or hangs the server during indexing
- Model or document text reaching the page as HTML or script
- Provider error details (account ids, keys) shown in the app

**Out of scope**

- Vulnerabilities in third-party services (e.g. hosting providers, Groq). Report those to the vendor.
- Denial-of-service, spam or volumetric attacks
- Prompt injection from a document you added yourself that only changes the wording of an answer (the model has no tools and can't act)
- A wrong answer or a missed or false conflict: answers cite their passages so they can be checked
- Social engineering
- Findings from automated scanners with no demonstrated impact

---

Please act in good faith: don't access or modify other users' data, and don't degrade the service while testing.

---

<div align="center">

<h3>Akshat Gupta</h3>

<a href="https://akshatgcodes.in"><img src="https://img.shields.io/badge/Website-akshatgcodes.in-111111?style=flat-square&logo=googlechrome&logoColor=white" alt="Website"></a>
<a href="https://linkedin.com/in/akshatgcodes"><img src="https://img.shields.io/badge/LinkedIn-akshatgcodes-0A66C2?style=flat-square" alt="LinkedIn"></a>
<a href="https://github.com/akshatgcodes"><img src="https://img.shields.io/badge/GitHub-akshatgcodes-181717?style=flat-square&logo=github&logoColor=white" alt="GitHub"></a>
<a href="mailto:akshatgcodes@gmail.com"><img src="https://img.shields.io/badge/Email-akshatgcodes%40gmail.com-EA4335?style=flat-square&logo=gmail&logoColor=white" alt="Email"></a>

</div>
