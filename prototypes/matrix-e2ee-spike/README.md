# Matrix E2EE Feasibility Spike

Phase 4.5 Step 0.1 only. This isolated Vite prototype is not imported by the
FebGrid application and must not be promoted to production code.

It validates that `matrix-js-sdk` and the official Matrix Rust/WASM crypto
package can bundle in Vite, initialize a named browser IndexedDB crypto store,
and reopen that store after a browser refresh. It constructs a Matrix client
against `matrix.invalid` but does not sync, register a device, export a key, or
make a homeserver call.

Run locally after installing the pinned prototype dependencies:

```powershell
npm.cmd run browser:build
npm.cmd run browser:serve
```

The server-backed tests are deliberately absent: creating rooms, adding two
users, E2EE send/decrypt, invitations, device registration, second-device key
sharing, member removal/rekey, and encrypted attachments need a supported
self-hosted Matrix environment. The complete design and conditional-go gates
are in `docs/FebGrid_Chat_Crypto_ADR.md`.
