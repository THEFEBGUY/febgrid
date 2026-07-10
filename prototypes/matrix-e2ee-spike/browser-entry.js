// Phase 4.5 Step 0.1 only. This file never contacts a homeserver, uses no
// FebGrid credentials, and never registers or transmits an actual device key.
import { DeviceId, initAsync, OlmMachine, UserId } from "@matrix-org/matrix-sdk-crypto-wasm";
import { createClient } from "matrix-js-sdk";

const output = document.querySelector("#result");

async function run() {
  await initAsync();
  const userId = new UserId("@spike-user:matrix.invalid");
  const deviceId = new DeviceId("SPIKEDEVICE");
  const storeName = "febgrid-matrix-e2ee-spike-store";
  const client = createClient({
    baseUrl: "https://matrix.invalid",
    accessToken: "spike-token-not-used",
    userId: "@spike-user:matrix.invalid",
    deviceId: "SPIKEDEVICE",
  });

  // OlmMachine uses the official Matrix Rust/WASM crypto store. An explicit
  // store name makes this a browser IndexedDB store instead of memory-only.
  // Production must use MatrixClient.initRustCrypto against a real homeserver;
  // that client path checks server key-backup state and is not a no-network
  // feasibility check.
  const firstMachine = await OlmMachine.initialize(userId, deviceId, storeName);
  firstMachine.close();
  const recoveredMachine = await OlmMachine.initialize(userId, deviceId, storeName);
  recoveredMachine.close();
  const databases = typeof indexedDB.databases === "function"
    ? await indexedDB.databases()
    : [];

  output.textContent = JSON.stringify({
    rustWasmInitialized: true,
    matrixClientConstructed: Boolean(client),
    indexedDbAvailable: Boolean(window.indexedDB),
    indexedDbDatabaseCount: databases.length,
    indexedDbReopenSucceeded: true,
    homeserverCalls: 0,
    deviceRegistrationAttempted: false,
    privateKeyExported: false,
  }, null, 2);
}

run().catch((error) => {
  output.textContent = JSON.stringify({
    wasmInitialized: false,
    errorName: error instanceof Error ? error.name : "UnknownError",
    errorMessage: error instanceof Error ? error.message : "Matrix spike failed",
  }, null, 2);
});
