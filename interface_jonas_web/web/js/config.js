const ROSBRIDGE_URL = `ws://${window.location.hostname}:9090`;

const TOPICS = {
  cmdVelRaw: "/jonas/web/cmd_vel_raw",
  webEnable: "/jonas/web/enable",
  baseStatus: "/jonas/web/base_status",
  faceCommand: "/face_coms_topic",
  faceStatus: "/jonas/web/face_status",
  armCommand: "/servos_coms_topic",
  sequenceStatus: "/jonas/web/sequence_status",
  dynamixelStatus: "/jonas/web/dynamixel_status",
  motorsStatus: "/motors_status"
};

const RECONNECT_MS = 2000;
const DEFAULT_SPEED_LIMIT = 0.30;
const MAX_LINEAR_SPEED = 0.30;
const MAX_LATERAL_SPEED = 0.30;
const MAX_ANGULAR_SPEED = 0.80;
const JOYSTICK_DEADZONE = 0.12;
const COMMAND_RATE_HZ = 10;
