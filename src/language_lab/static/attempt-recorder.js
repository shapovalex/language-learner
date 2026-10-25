// Native, ephemeral microphone capture. dispose() also invalidates pending permission replies.
export const MAX_ATTEMPT_BYTES = 5 * 1024 * 1024;

export class AttemptRecorder {
  constructor(callbacks) {
    this.callbacks = callbacks;
    this.disposed = false;
    this.chunks = [];
    this.bytes = 0;
    this.stream = null;
    this.recorder = null;
    this.context = null;
    this.source = null;
    this.analyser = null;
    this.timer = null;
    this.animation = null;
  }

  async start() {
    try {
      if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) throw new Error();
      // Safari requires AudioContext activation within the tap, before permission awaits.
      const Context = window.AudioContext || window.webkitAudioContext;
      this.context = new Context();
      const resumed = this.context.resume();
      resumed.catch(() => {}); // handled below, including when permission stays pending
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (this.disposed) {
        stream.getTracks().forEach(track => track.stop());
        return;
      }
      this.stream = stream;
      const mimeType = ["audio/mp4", "audio/webm;codecs=opus", "audio/webm"]
        .find(type => MediaRecorder.isTypeSupported(type));
      this.recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
      this.recorder.ondataavailable = event => {
        if (this.disposed) return;
        this.bytes += event.data.size;
        if (this.bytes > MAX_ATTEMPT_BYTES) {
          this.fail("size");
          return;
        }
        if (event.data.size) this.chunks.push(event.data);
      };
      this.recorder.onerror = () => this.fail("capture");
      this.recorder.onstop = () => {
        if (this.disposed) return;
        const type = this.recorder.mimeType.split(";")[0];
        const blob = new Blob(this.chunks, { type });
        const complete = this.callbacks?.complete;
        const error = this.callbacks?.error;
        this.dispose();
        if (blob.size) complete?.(blob);
        else error?.("capture");
      };
      this.source = this.context.createMediaStreamSource(stream);
      this.analyser = this.context.createAnalyser();
      this.analyser.fftSize = 256;
      this.source.connect(this.analyser);
      await resumed;
      if (this.disposed) return;
      const values = new Uint8Array(this.analyser.fftSize);
      const meter = () => {
        if (this.disposed || !this.analyser) return;
        this.analyser.getByteTimeDomainData(values);
        const energy = values.reduce((sum, value) => sum + ((value - 128) / 128) ** 2, 0);
        this.callbacks?.level(Math.min(1, Math.sqrt(energy / values.length)));
        this.animation = requestAnimationFrame(meter);
      };
      this.recorder.start(250);
      this.timer = setTimeout(() => this.stop(), 30_000);
      this.callbacks?.recording();
      meter();
    } catch {
      this.fail("capture");
    }
  }

  releaseInput() {
    clearTimeout(this.timer);
    cancelAnimationFrame(this.animation);
    this.timer = this.animation = null;
    this.source?.disconnect();
    this.analyser?.disconnect();
    this.source = this.analyser = null;
    this.stream?.getTracks().forEach(track => track.stop());
    this.stream = null;
    this.context?.close().catch(() => {});
    this.context = null;
  }

  stop() {
    if (this.disposed || this.recorder?.state !== "recording") return;
    this.callbacks?.stopping();
    this.recorder.stop();
    this.releaseInput();
  }

  fail(reason) {
    if (this.disposed) return;
    const error = this.callbacks?.error;
    this.dispose();
    error?.(reason);
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    this.callbacks = null;
    if (this.recorder) {
      this.recorder.ondataavailable = this.recorder.onstop = this.recorder.onerror = null;
      if (this.recorder.state !== "inactive") this.recorder.stop();
    }
    this.recorder = null;
    this.releaseInput();
    this.chunks.length = 0;
  }
}
