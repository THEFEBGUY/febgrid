import {
  ClientEvent,
  createClient,
  SyncState,
} from "matrix-js-sdk";
import {
  Attachment,
  EncryptedAttachment,
} from "@matrix-org/matrix-sdk-crypto-wasm";

const COMPANY_A = "http://127.0.0.1:18008";
const COMPANY_B = "http://127.0.0.1:18009";
const RUN = `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`;
const PASSWORD = `step02-${RUN}-synthetic-only`;
const results = [];
const clients = [];
for (const method of ["debug", "info", "log", "warn"]) {
  console[method] = () => {};
}
const quietLogger = {
  trace() {},
  debug() {},
  info() {},
  warn() {},
  error() {},
  log() {},
  getChild() { return this; },
};

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function record(name, detail) {
  results.push({ name, detail });
}

async function request(baseUrl, path, body, token, method = body === undefined ? "GET" : "POST") {
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      ...(body === undefined ? {} : { "content-type": "application/json" }),
      ...(token ? { authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.error || `Matrix request failed with ${response.status}`);
    error.status = response.status;
    error.errcode = payload.errcode;
    throw error;
  }
  return payload;
}

async function register(baseUrl, username, deviceId) {
  return request(baseUrl, "/_matrix/client/v3/register", {
    auth: { type: "m.login.dummy" },
    username,
    password: PASSWORD,
    device_id: deviceId,
    initial_device_display_name: "Step 0.2 synthetic device",
  });
}

async function login(baseUrl, username, deviceId) {
  return request(baseUrl, "/_matrix/client/v3/login", {
    type: "m.login.password",
    identifier: { type: "m.id.user", user: username },
    password: PASSWORD,
    device_id: deviceId,
    initial_device_display_name: "Step 0.2 synthetic second device",
  });
}

async function waitFor(label, predicate, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let lastError;
  while (Date.now() < deadline) {
    try {
      const value = await predicate();
      if (value) return value;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  throw new Error(`${label} timed out${lastError ? `: ${lastError.message}` : ""}`);
}

async function startClient(baseUrl, loginResponse, storePrefix) {
  const client = createClient({
    baseUrl,
    accessToken: loginResponse.access_token,
    userId: loginResponse.user_id,
    deviceId: loginResponse.device_id,
    logger: quietLogger,
  });
  clients.push(client);

  await client.initRustCrypto({
    useIndexedDB: false,
    cryptoDatabasePrefix: storePrefix,
  });

  await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("Matrix initial sync timed out")), 30000);
    client.once(ClientEvent.Sync, (state) => {
      clearTimeout(timeout);
      if (state === SyncState.Prepared) resolve();
      else reject(new Error(`Unexpected Matrix sync state: ${state}`));
    });
    client.startClient({ initialSyncLimit: 20, pollTimeout: 5000 });
  });
  return client;
}

function roomContainsBody(client, roomId, body) {
  const room = client.getRoom(roomId);
  return room?.getLiveTimeline().getEvents().some((event) => (
    event.getType() === "m.room.message" && event.getContent().body === body
  ));
}

function roomEvent(client, roomId, predicate) {
  const room = client.getRoom(roomId);
  return room?.getLiveTimeline().getEvents().find(predicate);
}

function mediaDownloadUrl(baseUrl, mxcUrl) {
  const [, serverAndMedia] = mxcUrl.split("mxc://");
  return `${baseUrl}/_matrix/client/v1/media/download/${serverAndMedia}`;
}

async function expectForbidden(action, label) {
  try {
    await action();
  } catch (error) {
    assert(error.errcode === "M_FORBIDDEN" || error.status === 403, `${label} returned an unexpected error`);
    return;
  }
  throw new Error(`${label} unexpectedly succeeded`);
}

async function main() {
  try {
    const aliceLogin = await register(COMPANY_A, `alice${RUN}`, "ALICEONE");
    const bobLogin = await register(COMPANY_A, `bob${RUN}`, "BOBONE");
    const charlieLogin = await register(COMPANY_B, `charlie${RUN}`, "CHARLIEONE");
    const aliceSecondLogin = await login(COMPANY_A, `alice${RUN}`, "ALICETWO");
    record("synthetic identities", "two Company A users, a second Alice device, and one isolated Company B user registered");

    const alice = await startClient(COMPANY_A, aliceLogin, `step02-${RUN}-alice-one`);
    const bob = await startClient(COMPANY_A, bobLogin, `step02-${RUN}-bob-one`);
    const aliceSecond = await startClient(COMPANY_A, aliceSecondLogin, `step02-${RUN}-alice-two`);
    assert(alice.getDeviceId() !== aliceSecond.getDeviceId(), "second device was not registered as distinct");
    record("device registration", "two distinct Alice devices initialized the official Rust crypto client");

    const roomResponse = await alice.createRoom({
      visibility: "private",
      preset: "private_chat",
      invite: [bobLogin.user_id],
      initial_state: [{
        type: "m.room.encryption",
        state_key: "",
        content: { algorithm: "m.megolm.v1.aes-sha2" },
      }],
    });
    const roomId = roomResponse.room_id;
    await waitFor("Bob invitation", () => bob.getRoom(roomId));
    await bob.joinRoom(roomId);
    await waitFor("Bob joined room", () => alice.getRoom(roomId)?.getMember(bobLogin.user_id)?.membership === "join");
    record("encrypted room invite/join", "private room created with m.megolm.v1.aes-sha2 and Bob joined");

    const firstMessage = `step02 encrypted message ${RUN}`;
    await alice.sendTextMessage(roomId, firstMessage);
    await waitFor("Bob decrypted first message", () => roomContainsBody(bob, roomId, firstMessage));
    await waitFor("Alice second device decrypted first message", () => roomContainsBody(aliceSecond, roomId, firstMessage));
    record("encrypted send/decrypt", "Bob and Alice's second device received the E2EE plaintext through Matrix Rust crypto");

    const attachmentPlaintext = new TextEncoder().encode(`step02 encrypted attachment ${RUN}`);
    const encryptedAttachment = Attachment.encrypt(attachmentPlaintext);
    const encryptionInfo = JSON.parse(encryptedAttachment.mediaEncryptionInfo);
    const encryptedBytes = encryptedAttachment.encryptedData;
    assert(!Buffer.from(encryptedBytes).equals(Buffer.from(attachmentPlaintext)), "attachment was not encrypted before upload");
    const upload = await alice.uploadContent(encryptedBytes, {
      type: "application/octet-stream",
      name: "step02.bin",
      includeFilename: false,
    });
    encryptionInfo.url = upload.content_uri;
    await alice.sendEvent(roomId, "m.room.message", {
      msgtype: "m.file",
      body: "step02.bin",
      filename: "step02.bin",
      file: encryptionInfo,
    });
    const fileEvent = await waitFor("Bob received encrypted attachment event", () => roomEvent(
      bob,
      roomId,
      (event) => event.getType() === "m.room.message" && event.getContent().file?.url === upload.content_uri,
    ));
    const rawMedia = new Uint8Array(await (await fetch(mediaDownloadUrl(COMPANY_A, upload.content_uri), {
      headers: { authorization: `Bearer ${bobLogin.access_token}` },
    })).arrayBuffer());
    assert(!Buffer.from(rawMedia).equals(Buffer.from(attachmentPlaintext)), "homeserver returned attachment plaintext");
    const receivedAttachment = new EncryptedAttachment(rawMedia, JSON.stringify(fileEvent.getContent().file));
    const decryptedAttachment = Attachment.decrypt(receivedAttachment);
    assert(Buffer.from(decryptedAttachment).equals(Buffer.from(attachmentPlaintext)), "attachment did not decrypt on recipient device");
    record("encrypted attachment", "ciphertext media uploaded; recipient decrypted it using Matrix Rust/WASM attachment support");

    await alice.kick(roomId, bobLogin.user_id, "Step 0.2 removal test");
    await waitFor("Bob removed", () => alice.getRoom(roomId)?.getMember(bobLogin.user_id)?.membership === "leave");
    await expectForbidden(() => request(
      COMPANY_A,
      `/_matrix/client/v3/rooms/${encodeURIComponent(roomId)}/send/m.room.message/removed-${RUN}`,
      { msgtype: "m.text", body: `removed sender ${RUN}` },
      bobLogin.access_token,
      "PUT",
    ), "removed member send");
    await alice.getCrypto()?.forceDiscardSession(roomId);
    const postRemovalMessage = `post removal message ${RUN}`;
    await alice.sendTextMessage(roomId, postRemovalMessage);
    await new Promise((resolve) => setTimeout(resolve, 1500));
    assert(!roomContainsBody(bob, roomId, postRemovalMessage), "removed member decrypted a post-removal message");
    record("member removal and rekey", "removed member cannot send; a forced new outbound session did not expose the next plaintext to that device");

    const federationResponse = await fetch(`${COMPANY_A}/_matrix/federation/v1/version`);
    assert(federationResponse.status === 404, "federation endpoint was unexpectedly exposed on the client listener");
    const foreignTokenResponse = await fetch(`${COMPANY_A}/_matrix/client/v3/account/whoami`, {
      headers: { authorization: `Bearer ${charlieLogin.access_token}` },
    });
    assert(foreignTokenResponse.status === 401, "Company B token was accepted by Company A homeserver");
    record("federation and company isolation", "client-only listener rejects federation endpoint; Company B token is rejected by Company A");

    process.stdout.write(`${JSON.stringify({ status: "passed", checks: results }, null, 2)}\n`);
  } finally {
    for (const client of clients) client.stopClient();
  }
}

main().catch((error) => {
  process.stderr.write(`${JSON.stringify({ status: "failed", error: error.message, checks: results }, null, 2)}\n`);
  process.exitCode = 1;
});
