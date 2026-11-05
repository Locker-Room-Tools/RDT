# Tasks

## 1. Execution boundary

- [ ] 1.1 Add capture and timeout execution policy plus structured results in core; verify mocked subprocess cases cover success, nonzero exit, missing executable, invalid timeout, and cleanup on timeout.
- [ ] 1.2 Bound returned diagnostic tails and indicate truncation; verify large and invalidly encoded output yields valid bounded text results.

## 2. MCP and CLI integration

- [ ] 2.1 Adapt MCP up/check to captured execution with positive timeout_seconds defaulting to 120; verify the tool schemas and stable error codes with client calls.
- [ ] 2.2 Preserve CLI streaming and foreground lifetime; verify CLI subprocess options do not receive the MCP deadline or capture policy.
- [ ] 2.3 Document result fields, timeout overrides, and possible partial stack effects in both MCP guides; verify all new translated message keys exist in both locales.

## 3. Protocol integration

- [ ] 3.1 Add a stdio MCP client test using a fake Docker executable that writes to both streams; verify up returns structured output and a subsequent list call works without a real Docker daemon.
- [ ] 3.2 Run the full pytest suite and verify the server remains usable after each simulated execution failure.
