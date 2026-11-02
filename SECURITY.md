# Security policy

GraphForge V0.1 is an experimental local-first prototype, **not** a multi-user or internet-facing service.

- Docker Compose binds the frontend and API to 127.0.0.1 only.
- No user authentication or authorization is implemented. Any process or local user able to reach the API can upload data and review proposals.
- Do not expose port 8000/5173 through a reverse proxy, port forward, tunnel or public interface.
- Do not import confidential or regulated datasets into a publicly accessible deployment.
- Uploaded records and original files are stored in PostgreSQL; protect the local Docker volume and backups.
- Configure a unique password in an ignored root `.env` file.
- Ollama output is untrusted; proposals require human approval.
- Do not use this repository as a production service without authentication, rate limits, file-size limits, hardened secrets management, and a full security review.

## Reporting vulnerabilities

Please report vulnerabilities privately to the repository maintainer via GitHub's private vulnerability reporting feature if enabled. Otherwise open a GitHub issue **without** exploit details or sensitive data to request a private reporting channel. Do not publish active exploit instructions.
