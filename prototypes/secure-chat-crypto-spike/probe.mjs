/**
 * Phase 4.5 Step 0 only. This intentionally does not implement encryption,
 * connect to a backend, register a device, or generate production keys.
 * It records whether pinned upstream candidates can be loaded in an isolated
 * Node environment and whether that says anything honest about browser use.
 */
import { createRequire } from "node:module";
import { statSync } from "node:fs";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);

function packageMetadata(packageName) {
  const packageJsonPath = require.resolve(`${packageName}/package.json`);
  const metadata = require(packageJsonPath);
  return {
    packageName,
    version: metadata.version,
    license: metadata.license ?? null,
    packageJsonPath,
    packageRoot: dirname(packageJsonPath),
  };
}

async function inspectCandidate(packageName) {
  const metadata = packageMetadata(packageName);
  const startedAt = performance.now();
  try {
    const imported = await import(packageName);
    const importElapsedMs = Number((performance.now() - startedAt).toFixed(2));
    return {
      ...metadata,
      importableInNode: true,
      importElapsedMs,
      exportNames: Object.keys(imported).sort().slice(0, 40),
      mainFileBytes: statSync(require.resolve(packageName)).size,
    };
  } catch (error) {
    return {
      ...metadata,
      importableInNode: false,
      importElapsedMs: Number((performance.now() - startedAt).toFixed(2)),
      errorName: error instanceof Error ? error.name : "UnknownError",
      errorMessage: error instanceof Error ? error.message.slice(0, 240) : "Candidate failed to import",
    };
  }
}

const candidates = await Promise.all([
  inspectCandidate("@signalapp/libsignal-client"),
  inspectCandidate("openmls-wasm"),
]);

// This probe deliberately has no HTTP client or FebGrid import. A passing run
// demonstrates that no prototype private key material can reach FebGrid's API.
const result = {
  phase: "4.5-step-0",
  isolated: true,
  backendNetworkCalls: 0,
  privateKeyRegistrationAttempted: false,
  candidates,
};

console.log(JSON.stringify(result, null, 2));
