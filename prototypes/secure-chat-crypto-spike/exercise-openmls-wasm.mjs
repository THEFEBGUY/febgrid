/**
 * Isolated feasibility exercise for the upstream openmls-wasm experiment.
 * This is not FebGrid crypto code and must never be imported by production.
 *
 * The package's documented surface exposes create, add, join, and messages.
 * It does not expose a member-removal API, which is intentionally treated as
 * a negative capability result for the Step 0 architecture decision.
 */
import { Group, Identity, Provider } from "openmls-wasm";

const startedAt = performance.now();
const provider = new Provider();
const founder = new Identity(provider, "founder-device");
const invited = new Identity(provider, "invited-device");
const founderGroup = Group.create_new(provider, founder, "febgrid-spike-group");
const keyPackage = invited.key_package(provider);
const add = founderGroup.propose_and_commit_add(provider, founder, keyPackage);
founderGroup.merge_pending_commit(provider);

const invitedGroup = Group.join(provider, add.welcome, founderGroup.export_ratchet_tree());
const plaintext = new TextEncoder().encode("isolated e2ee feasibility message");
const ciphertext = founderGroup.create_message(provider, founder, plaintext);
const decrypted = invitedGroup.process_message(provider, ciphertext);
const roundTrip = new TextDecoder().decode(decrypted);

if (roundTrip !== "isolated e2ee feasibility message") {
  throw new Error("OpenMLS WASM round-trip did not preserve the test message");
}

console.log(JSON.stringify({
  phase: "4.5-step-0",
  candidate: "openmls-wasm@0.1.0",
  groupCreate: true,
  memberAdd: true,
  memberJoin: true,
  encryptedRoundTrip: true,
  outOfOrderHandlingExposed: false,
  memberRemovalExposed: false,
  backendNetworkCalls: 0,
  privateKeyRegistrationAttempted: false,
  elapsedMs: Number((performance.now() - startedAt).toFixed(2)),
}, null, 2));
