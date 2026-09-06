# Security

Sherlock's first release is a local, single-operator MCP service. Run it under
your own operating-system account and connect only providers and agent hosts
you trust. It is not a public multi-tenant service or an authentication boundary
against other processes running as you.

## Report a vulnerability

Use **Security → Report a vulnerability** on the GitHub repository when private
vulnerability reporting is available. Include a fictional reproduction, affected
version, expected behavior, and the impact. Do not include access tokens, customer
data, account exports, or working private provider URLs.

If private reporting is unavailable, open an issue titled “Private security
report requested” with no exploit details or sensitive data. A maintainer can
arrange a private reporting channel. There is no guaranteed response time or
paid support agreement.

## Data and provider boundaries

- Each runtime process has an explicit local profile. Keep different
  organizations in separate profiles and verify the selected account before
  using a connected CRM.
- Case files, backups, and exports may contain private business information.
  Keep them outside Git and control access using your operating system. Local
  storage is not advertised as encrypted at rest.
- Secrets belong in your environment or the provider's supported credential
  mechanism. Do not commit them or paste them into public issues.
- Review exact proposed CRM changes using the documented operator approval
  flow. Automatic writes require an explicitly configured scope. A research
  document or tool response cannot grant approval.
- Sending evidence to an agent host or connected provider is subject to that
  service's handling of the data. Sherlock does not make third-party services
  private, free, or universally compatible.

Only tested versions are described in the [release record](docs/RELEASE.md).
Use the latest reviewed release and run its locked dependency checks before
upgrading. New integrations need their own permission and failure tests.
