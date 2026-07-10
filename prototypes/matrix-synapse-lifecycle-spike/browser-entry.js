import { ClientEvent, createClient, SyncState } from "matrix-js-sdk";

const BASE_URL = "http://127.0.0.1:18008";
const STORE_PREFIX = "febgrid-step02-browser-bob";
const stateKey = "febgrid-step02-browser-recovery";
const output = document.querySelector("#result");
const quietLogger = {
  trace() {}, debug() {}, info() {}, warn() {}, error() {}, log() {},
  getChild() { return this; },
};

function report(value) {
  output.textContent = JSON.stringify(value, null, 2);
}

async function request(path, body) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.errcode || "Matrix test request failed");
  return payload;
}

async function waitFor(label, predicate, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`${label} timed out`);
}

async function start(login, storePrefix) {
  const client = createClient({
    baseUrl: BASE_URL,
    accessToken: login.access_token,
    userId: login.user_id,
    deviceId: login.device_id,
    logger: quietLogger,
  });
  await client.initRustCrypto({ useIndexedDB: true, cryptoDatabasePrefix: storePrefix });
  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("Matrix sync timed out")), 30000);
    client.once(ClientEvent.Sync, (syncState) => {
      clearTimeout(timeout);
      syncState === SyncState.Prepared ? resolve() : reject(new Error("Initial sync failed"));
    });
    client.startClient({ initialSyncLimit: 20, pollTimeout: 5000 });
  });
  return client;
}

function hasBody(client, roomId, body) {
  return client.getRoom(roomId)?.getLiveTimeline().getEvents().some((event) => (
    event.getType() === "m.room.message" && event.getContent().body === body
  ));
}

async function register(username, deviceId, password) {
  return request("/_matrix/client/v3/register", {
    auth: { type: "m.login.dummy" },
    username,
    password,
    device_id: deviceId,
  });
}

async function initialRun() {
  const run = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const password = `synthetic-browser-${run}`;
  const aliceLogin = await register(`browseralice${run}`, "BROWALICE", password);
  const bobLogin = await register(`browserbob${run}`, "BROWBOB", password);
  const alice = await start(aliceLogin, `febgrid-step02-browser-alice-${run}`);
  const bob = await start(bobLogin, STORE_PREFIX);
  const room = await alice.createRoom({
    visibility: "private",
    preset: "private_chat",
    invite: [bobLogin.user_id],
    initial_state: [{
      type: "m.room.encryption",
      state_key: "",
      content: { algorithm: "m.megolm.v1.aes-sha2" },
    }],
  });
  await waitFor("browser invitation", () => bob.getRoom(room.room_id));
  await bob.joinRoom(room.room_id);
  const expected = `browser-recovery-${run}`;
  await alice.sendTextMessage(room.room_id, expected);
  await waitFor("browser initial decrypt", () => hasBody(bob, room.room_id, expected));
  alice.stopClient();
  bob.stopClient();
  sessionStorage.setItem(stateKey, JSON.stringify({ bobLogin, roomId: room.room_id, expected }));
  location.reload();
}

async function recoveryRun(saved) {
  const bob = await start(saved.bobLogin, STORE_PREFIX);
  await waitFor("browser IndexedDB recovery decrypt", () => hasBody(bob, saved.roomId, saved.expected));
  bob.stopClient();
  report({
    browserIndexedDbRecovery: true,
    homeserver: "local-isolated-synapse",
    tokenDisplayed: false,
    plaintextDisplayed: false,
  });
}

async function main() {
  if (location.search === "?cleanup") {
    sessionStorage.removeItem(stateKey);
    const databases = typeof indexedDB.databases === "function" ? await indexedDB.databases() : [];
    await Promise.all(databases
      .filter((database) => database.name?.includes("febgrid-step02-browser"))
      .map((database) => new Promise((resolve) => {
        const request = indexedDB.deleteDatabase(database.name);
        request.onsuccess = request.onerror = request.onblocked = () => resolve();
      })));
    report({ browserStateCleaned: true });
    return;
  }
  const saved = sessionStorage.getItem(stateKey);
  if (saved) await recoveryRun(JSON.parse(saved));
  else await initialRun();
}

main().catch((error) => report({ browserIndexedDbRecovery: false, error: error.message }));
