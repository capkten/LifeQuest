# LifeQuest MCP OAuth design

Approved in conversation on 2026-10-26. Work is isolated to feat/mcp-oauth; no production operations or real user data.

## Protocol and trust
Add OAuth 2.1 authorization code with mandatory S256 PKCE, RFC8414 discovery, RFC9728 protected resource metadata, RFC8707 resource binding, RFC7591 registration, RFC7009 revocation, and rotating refresh tokens. Support public and confidential clients (none/client_secret_post/client_secret_basic). Do not claim OIDC or advertise client metadata URL fetching. Exact registered redirects use HTTPS; loopback HTTP is development only. Clients always need explicit consent. Do not derive public URLs from Host or forwarded headers.

## Login and consent
Reuse existing LifeQuest browser login and its ordinary API bearer credential. GET /api/oauth/authorize validates all OAuth parameters, creates a 10-minute request, and redirects to /oauth/authorize?request_id=... . The Vue page retrieves details and posts approval/denial with the current ordinary user bearer. First authenticated retrieval binds the request to that user. Approval yields a 2-minute single-use authorization code and preserves state on the exact registered callback. No passwords or access/refresh tokens in URLs. The consent page displays actual redirect host and current user. Separate login redirects remain local paths only.

## Persistence
Separate OAuth clients, pending authorization requests, codes, grants, and token pairs from PAT and ordinary JWT sessions. Persist hashes of client secrets, request handles, codes, access and refresh tokens. Each grant binds client/user/resource/scope and can be revoked by its owner. Access tokens expire after 900 seconds; refresh tokens after 30 days; refresh rotates atomically and replay revokes the grant. Both application and MCP process share persistence. Additive tables via existing create_all convention, no rewrites to existing user rows.

## HTTP API
- GET /.well-known/oauth-authorization-server
- GET /.well-known/oauth-protected-resource and /.well-known/oauth-protected-resource/mcp/http
- GET /api/oauth/authorize
- POST /api/oauth/register, /api/oauth/token, /api/oauth/revoke
- GET /api/oauth/requests/{request_id}; POST /api/oauth/consent with {request_id, approve}
- GET /api/oauth/grants; DELETE /api/oauth/grants/{grant_id}
Discovery and challenges use explicit MCP_OAUTH_ISSUER_URL and MCP_OAUTH_RESOURCE_URL. MCP_OAUTH_ENABLED defaults false. OAuth protocol errors use error/error_description and no-store. Resource metadata is also exposed by standalone MCP transport for its canonical resource path. Nginx passes /.well-known/ to API without SPA fallback.

## MCP compatibility
A shared bearer verifier accepts existing PAT or MCP-specific OAuth access tokens and resolves the user on every request and business call. OAuth refresh tokens, ordinary JWTs and authorization codes are never accepted as MCP access tokens. Token audience/resource and mcp scope must match configuration. Existing session owner binding remains; refresh can continue the same user's session. Revoked grants immediately deny initialization, tools/list and tools/call. No tool login credentials are needed in ChatGPT conversations.

## Verification and delivery
Use isolated SQLite/temp files and real MCP protocol exchanges. Test metadata, registration, login/consent denial, callback/state, PKCE/code replay, exact redirects, resource/scope binding, access expiry, refresh rotation/replay, revocation, cross-client/cross-user ownership and PAT/SSE/stdio regression. Verify Vue consent behavior, frontend tests/build/version. Root version advances from 1.16.1 to 1.17.0; no Android package release. Push feature branch and create PR only.

Official MCP authorization specification fetched successfully: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization . OpenAI official Apps SDK auth pages returned HTTP403 from this environment; actual ChatGPT account connection must be separately verified after review/deployment. No assumed callback URL is hardcoded: use the exact URI provided by the client registration.
