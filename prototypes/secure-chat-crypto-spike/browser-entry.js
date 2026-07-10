// Build-only browser compatibility probe. It creates no keys and sends no data.
import { Provider } from "openmls-wasm";

window.__febgridChatCryptoSpike = {
  openmlsWasmExportLoaded: typeof Provider === "function",
  backendNetworkCalls: 0,
  privateKeyRegistrationAttempted: false,
};
