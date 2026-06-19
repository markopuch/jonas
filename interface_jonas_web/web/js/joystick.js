class TouchJoystick {
  constructor(element, onChange) {
    this.element = element;
    this.knob = element.querySelector(".joystick-knob");
    this.onChange = onChange;
    this.pointerId = null;
    this.xAxis = 0.0;
    this.yAxis = 0.0;

    this.element.addEventListener("pointerdown", (event) => this.start(event));
    this.element.addEventListener("pointermove", (event) => this.move(event));
    this.element.addEventListener("pointerup", (event) => this.end(event));
    this.element.addEventListener("pointercancel", (event) => this.end(event));
  }

  start(event) {
    this.pointerId = event.pointerId;
    this.element.setPointerCapture(this.pointerId);
    this.updateFromEvent(event);
  }

  move(event) {
    if (event.pointerId !== this.pointerId) {
      return;
    }
    this.updateFromEvent(event);
  }

  end(event) {
    if (event.pointerId !== this.pointerId) {
      return;
    }
    this.pointerId = null;
    this.reset();
  }

  reset(emit = true) {
    this.xAxis = 0.0;
    this.yAxis = 0.0;
    this.render();
    if (emit) {
      this.onChange(this.xAxis, this.yAxis);
    }
  }

  updateFromEvent(event) {
    const rect = this.element.getBoundingClientRect();
    const centerX = rect.left + rect.width / 2.0;
    const centerY = rect.top + rect.height / 2.0;
    const radius = Math.max(Math.min(rect.width, rect.height) / 2.0 - 18.0, 1.0);
    let dx = event.clientX - centerX;
    let dy = event.clientY - centerY;
    const distance = Math.hypot(dx, dy);

    if (distance > radius) {
      const scale = radius / distance;
      dx *= scale;
      dy *= scale;
    }

    this.xAxis = clamp(-dy / radius, -1.0, 1.0);
    this.yAxis = clamp(-dx / radius, -1.0, 1.0);
    this.render();
    this.onChange(this.xAxis, this.yAxis);
  }

  render() {
    const rect = this.element.getBoundingClientRect();
    const radius = Math.max(Math.min(rect.width, rect.height) / 2.0 - 18.0, 1.0);
    const dx = -this.yAxis * radius;
    const dy = -this.xAxis * radius;
    this.knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
  }
}

function clamp(value, minimum, maximum) {
  return Math.max(minimum, Math.min(maximum, value));
}
