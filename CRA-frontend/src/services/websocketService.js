import { tokenStorage } from "../utils/tokenStorage";

const DEFAULT_RECONNECT_MS = 1600;
const HEARTBEAT_MS = 25000;

function getWsBaseUrl() {
  const apiBase = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";
  const base = apiBase.replace(/\/api\/v1\/?$/, "");
  return base.replace(/^http/, "ws");
}

export class AssessmentWebSocket {
  constructor(path, handlers = {}) {
    this.path = path;
    this.handlers = handlers;
    this.socket = null;
    this.reconnectTimer = null;
    this.heartbeatTimer = null;
    this.closedByUser = false;
    this.reconnectAttempts = 0;
  }

  connect() {
    this.closedByUser = false;
    const token = tokenStorage.getAccessToken();
    const separator = this.path.includes("?") ? "&" : "?";
    const tokenQuery = token ? `${separator}token=${encodeURIComponent(token)}` : "";
    this.socket = new WebSocket(`${getWsBaseUrl()}${this.path}${tokenQuery}`);

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.handlers.onStatus?.("connected");
      this.startHeartbeat();
    };

    this.socket.onmessage = (message) => {
      let payload = message.data;
      try {
        payload = JSON.parse(message.data);
      } catch {
        payload = { type: "message", detail: message.data };
      }
      this.handlers.onEvent?.(payload);
    };

    this.socket.onerror = () => {
      this.handlers.onStatus?.("error");
    };

    this.socket.onclose = () => {
      this.stopHeartbeat();
      if (this.closedByUser) {
        this.handlers.onStatus?.("disconnected");
        return;
      }
      this.handlers.onStatus?.("reconnecting");
      this.scheduleReconnect();
    };
  }

  scheduleReconnect() {
    window.clearTimeout(this.reconnectTimer);
    const delay = Math.min(DEFAULT_RECONNECT_MS * 2 ** this.reconnectAttempts, 15000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = window.setTimeout(() => this.connect(), delay);
  }

  startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = window.setInterval(() => {
      if (this.socket?.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: "heartbeat", timestamp: Date.now() }));
      }
    }, HEARTBEAT_MS);
  }

  stopHeartbeat() {
    window.clearInterval(this.heartbeatTimer);
  }

  disconnect() {
    this.closedByUser = true;
    window.clearTimeout(this.reconnectTimer);
    this.stopHeartbeat();
    this.socket?.close();
  }
}

export function subscribeToAssessment(assessmentId, handlers) {
  const client = new AssessmentWebSocket(`/ws/assessment/${assessmentId}`, handlers);
  client.connect();
  return () => client.disconnect();
}

export function subscribeToTenantJob(jobId, handlers) {
  const client = new AssessmentWebSocket(`/ws/tenant/${jobId}`, handlers);
  client.connect();
  return () => client.disconnect();
}
