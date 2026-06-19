const state = {
  socket: null,
  connected: false,
  reconnectTimer: null,
  advertised: new Set(),
  subscribed: new Set(),
  enabled: false,
  joystickX: 0.0,
  joystickY: 0.0,
  angularZ: 0.0,
  speedLimit: DEFAULT_SPEED_LIMIT,
  lastTwistJson: "",
  lastMovementText: "mov_coms_topic: waiting",
  commandTimer: null
};

const elements = {};

window.addEventListener("DOMContentLoaded", () => {
  bindElements();
  bindControls();
  connectRosbridge();
  state.commandTimer = window.setInterval(publishCurrentMotion, 1000 / COMMAND_RATE_HZ);
  updateMotionReadout();
});

window.addEventListener("beforeunload", () => {
  publishStop();
});

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    publishStop();
  }
});

window.addEventListener("blur", () => {
  publishStop();
});

function bindElements() {
  const ids = [
    "rosStatus",
    "enableMotion",
    "speedSlider",
    "speedLabel",
    "limitLabel",
    "inputLabel",
    "motionTopicLabel",
    "faceTopicLabel",
    "servoTopicLabel",
    "motorsTopicLabel",
    "baseBadge",
    "faceBadge",
    "sequenceBadge",
    "dynamixelBadge",
    "logPanel"
  ];

  for (const id of ids) {
    elements[id] = document.getElementById(id);
  }
}

function bindControls() {
  elements.speedSlider.value = Math.round(DEFAULT_SPEED_LIMIT * 100);
  updateSpeedLabel();
  elements.speedSlider.addEventListener("input", () => {
    state.speedLimit = Number(elements.speedSlider.value) / 100.0;
    updateSpeedLabel();
    updateMotionReadout();
  });

  elements.enableMotion.addEventListener("change", () => {
    state.enabled = elements.enableMotion.checked;
    publishEnable(state.enabled);
    if (!state.enabled) {
      publishStop();
    }
    logLine(`Movimiento web: ${state.enabled ? "habilitado" : "deshabilitado"}`);
  });

  state.joystick = new TouchJoystick(document.getElementById("joystick"), (xAxis, yAxis) => {
    state.joystickX = applyDeadzone(xAxis);
    state.joystickY = applyDeadzone(yAxis);
    updateMotionReadout();
    if (state.joystickX === 0.0 && state.joystickY === 0.0) {
      publishStop();
    }
  });

  bindHoldButton("rotateLeft", () => {
    state.angularZ = 1.0;
    updateMotionReadout();
  });
  bindHoldButton("rotateRight", () => {
    state.angularZ = -1.0;
    updateMotionReadout();
  });

  document.getElementById("stopButton").addEventListener("click", () => {
    publishStop();
  });

  document.querySelectorAll("[data-sequence]").forEach((button) => {
    button.addEventListener("click", () => publishSequence(button.dataset.sequence));
  });
}

function bindHoldButton(id, onPress) {
  const button = document.getElementById(id);
  const release = () => {
    state.angularZ = 0.0;
    updateMotionReadout();
    publishStop();
  };

  button.addEventListener("pointerdown", (event) => {
    button.setPointerCapture(event.pointerId);
    onPress();
  });
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("pointerleave", release);
}

function connectRosbridge() {
  clearTimeout(state.reconnectTimer);
  updateConnection(false, "CONNECTING");

  const socket = new WebSocket(ROSBRIDGE_URL);
  state.socket = socket;

  socket.addEventListener("open", () => {
    state.connected = true;
    state.advertised.clear();
    state.subscribed.clear();
    updateConnection(true, "CONNECTED");
    setupRosTopics();
    publishEnable(state.enabled);
    logLine(`Conectado a ${ROSBRIDGE_URL}`);
  });

  socket.addEventListener("message", (event) => {
    handleRosbridgeMessage(JSON.parse(event.data));
  });

  socket.addEventListener("close", () => {
    updateConnection(false, "DISCONNECTED");
    state.connected = false;
    state.reconnectTimer = window.setTimeout(connectRosbridge, RECONNECT_MS);
  });

  socket.addEventListener("error", () => {
    updateConnection(false, "ERROR");
  });
}

function setupRosTopics() {
  advertise(TOPICS.cmdVelRaw, "geometry_msgs/msg/Twist");
  advertise(TOPICS.webEnable, "std_msgs/msg/Bool");
  advertise(TOPICS.faceCommand, "std_msgs/msg/String");
  advertise(TOPICS.armCommand, "std_msgs/msg/String");

  subscribe(TOPICS.baseStatus);
  subscribe(TOPICS.faceStatus);
  subscribe(TOPICS.sequenceStatus);
  subscribe(TOPICS.dynamixelStatus);
  subscribe(TOPICS.motorsStatus);
}

function advertise(topic, type) {
  if (state.advertised.has(topic)) {
    return;
  }
  sendRos({ op: "advertise", topic, type });
  state.advertised.add(topic);
}

function subscribe(topic) {
  if (state.subscribed.has(topic)) {
    return;
  }
  sendRos({ op: "subscribe", topic });
  state.subscribed.add(topic);
}

function publish(topic, msg) {
  sendRos({ op: "publish", topic, msg });
}

function sendRos(payload) {
  if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
    return;
  }
  state.socket.send(JSON.stringify(payload));
}

function handleRosbridgeMessage(message) {
  if (message.op !== "publish") {
    return;
  }

  const value = normalizeMessageValue(message.msg);

  if (message.topic === TOPICS.baseStatus) {
    setBadge(elements.baseBadge, value, value.includes("MOVING") ? "warn" : "ok");
    elements.motionTopicLabel.textContent = `mov_coms_topic: ${value}`;
  } else if (message.topic === TOPICS.faceStatus) {
    setBadge(elements.faceBadge, value, "ok");
  } else if (message.topic === TOPICS.sequenceStatus) {
    setBadge(elements.sequenceBadge, value, value === "RUNNING" ? "warn" : "ok");
  } else if (message.topic === TOPICS.dynamixelStatus) {
    setBadge(elements.dynamixelBadge, value, value === "ERROR" ? "error" : "ok");
  } else if (message.topic === TOPICS.motorsStatus) {
    const moving = Boolean(message.msg.data);
    elements.motorsTopicLabel.textContent = `motors_status: ${moving ? "moving" : "idle"}`;
    setBadge(elements.dynamixelBadge, moving ? "MOVING" : "IDLE", moving ? "warn" : "ok");
  }
}

function publishCurrentMotion() {
  if (!state.enabled) {
    return;
  }

  const twist = currentTwist();
  const twistJson = JSON.stringify(twist);
  if (twistJson === state.lastTwistJson && isZeroTwist(twist)) {
    return;
  }

  publish(TOPICS.cmdVelRaw, twist);
  state.lastTwistJson = twistJson;
}

function publishStop() {
  state.joystickX = 0.0;
  state.joystickY = 0.0;
  state.angularZ = 0.0;
  if (state.joystick) {
    state.joystick.reset(false);
  }
  updateMotionReadout();
  const twist = zeroTwist();
  publish(TOPICS.cmdVelRaw, twist);
  state.lastTwistJson = JSON.stringify(twist);
  logLine("STOP enviado");
}

function publishEnable(enabled) {
  publish(TOPICS.webEnable, { data: Boolean(enabled) });
}

function publishSequence(name) {
  const faceExpression = {
    Salute: "blink",
    Curl: "fire",
    Hug: "heart",
    Dance: "music",
    Serve: "smile",
    Walking: "blink",
    Rest: "blink"
  }[name] || "blink";

  publish(TOPICS.faceCommand, { data: faceExpression });
  publish(TOPICS.armCommand, { data: name });
  elements.faceTopicLabel.textContent = `face_coms_topic: ${faceExpression}`;
  elements.servoTopicLabel.textContent = `servos_coms_topic: ${name}`;
  setBadge(elements.faceBadge, "SENT", "ok");
  setBadge(elements.sequenceBadge, "SENT", "ok");
  logLine(`Secuencia ${name}: cara=${faceExpression}, brazo=${name}`);
}

function currentTwist() {
  if (!state.enabled) {
    return zeroTwist();
  }

  return {
    linear: {
      x: round4(state.joystickX * MAX_LINEAR_SPEED * state.speedLimit),
      y: round4(state.joystickY * MAX_LATERAL_SPEED * state.speedLimit),
      z: 0.0
    },
    angular: {
      x: 0.0,
      y: 0.0,
      z: round4(state.angularZ * MAX_ANGULAR_SPEED * state.speedLimit)
    }
  };
}

function zeroTwist() {
  return {
    linear: { x: 0.0, y: 0.0, z: 0.0 },
    angular: { x: 0.0, y: 0.0, z: 0.0 }
  };
}

function isZeroTwist(twist) {
  return (
    twist.linear.x === 0.0 &&
    twist.linear.y === 0.0 &&
    twist.angular.z === 0.0
  );
}

function updateMotionReadout() {
  elements.inputLabel.textContent =
    `Entrada: x=${formatSigned(state.joystickX)}, y=${formatSigned(state.joystickY)}`;
  const label = legacyLabelForCurrentMotion();
  const speedPercent = Math.round(state.speedLimit * 100 * motionLevel());
  elements.motionTopicLabel.textContent =
    `mov_coms_topic: ${label}, speed=${speedPercent}%`;
}

function updateSpeedLabel() {
  const percent = Math.round(state.speedLimit * 100);
  elements.speedLabel.textContent = `Limite de velocidad: ${percent}%`;
  elements.limitLabel.textContent = `max legado=${percent}%`;
}

function legacyLabelForCurrentMotion() {
  if (Math.abs(state.angularZ) >= Math.max(linearLevel(), JOYSTICK_DEADZONE)) {
    return state.angularZ > 0.0 ? "ROT-LEFT (9)" : "ROT-RIGHT (10)";
  }

  if (linearLevel() <= JOYSTICK_DEADZONE) {
    return "STOP (1)";
  }

  const angle = Math.atan2(state.joystickY, state.joystickX) * 180.0 / Math.PI;
  if (angle >= -22.5 && angle < 22.5) return "UP (1)";
  if (angle >= 22.5 && angle < 67.5) return "UP-LEFT (8)";
  if (angle >= 67.5 && angle < 112.5) return "LEFT (3)";
  if (angle >= 112.5 && angle < 157.5) return "DOWN-LEFT (7)";
  if (angle >= 157.5 || angle < -157.5) return "DOWN (2)";
  if (angle >= -157.5 && angle < -112.5) return "DOWN-RIGHT (6)";
  if (angle >= -112.5 && angle < -67.5) return "RIGHT (4)";
  if (angle >= -67.5 && angle < -22.5) return "UP-RIGHT (5)";
  return "STOP (1)";
}

function linearLevel() {
  return Math.min(1.0, Math.hypot(state.joystickX, state.joystickY));
}

function motionLevel() {
  return Math.min(1.0, Math.max(linearLevel(), Math.abs(state.angularZ)));
}

function applyDeadzone(value) {
  return Math.abs(value) <= JOYSTICK_DEADZONE ? 0.0 : value;
}

function updateConnection(connected, text) {
  elements.rosStatus.textContent = text;
  elements.rosStatus.className = connected ? "badge ok" : "badge error";
}

function setBadge(element, text, stateName) {
  element.textContent = text;
  element.className = `badge ${stateName}`;
}

function normalizeMessageValue(msg) {
  if (msg && Object.prototype.hasOwnProperty.call(msg, "data")) {
    return String(msg.data);
  }
  return JSON.stringify(msg);
}

function logLine(text) {
  const line = document.createElement("div");
  line.textContent = `[${new Date().toLocaleTimeString()}] ${text}`;
  elements.logPanel.prepend(line);
  while (elements.logPanel.children.length > 40) {
    elements.logPanel.removeChild(elements.logPanel.lastChild);
  }
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

function formatSigned(value) {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}
