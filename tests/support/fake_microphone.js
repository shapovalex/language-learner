// Browser-boundary double for 7.2. The screen still calls getUserMedia and MediaRecorder;
// no screen state is injected. stop() emits a recorded native-codec fixture. A real
// AudioContext MediaStream lets the screen build its own source/analyser/level meter.
(() => {
  const bytes = Uint8Array.from(atob(__PAYLOAD__), c => c.charCodeAt(0));
  const mime = __MIME__;
  const probe = window.__attemptMic = {
    denied: __DENIED__, gets: 0, starts: 0, stops: 0, tracks: 0, trackStops: 0,
    level: 0.25, meterReads: 0, createdUrls: [], revokedUrls: [],
    holdPermission: false, payloadSize: 0,
  };
  const Context = window.AudioContext || window.webkitAudioContext;
  const getByte = AnalyserNode.prototype.getByteTimeDomainData;
  AnalyserNode.prototype.getByteTimeDomainData = function (data) {
    getByte.call(this, data);
    probe.meterReads++;
    for (let i = 0; i < data.length; i++) data[i] = 128 + (i % 2 ? 1 : -1) * probe.level * 100;
  };
  const getFloat = AnalyserNode.prototype.getFloatTimeDomainData;
  AnalyserNode.prototype.getFloatTimeDomainData = function (data) {
    getFloat.call(this, data);
    probe.meterReads++;
    for (let i = 0; i < data.length; i++) data[i] = (i % 2 ? 1 : -1) * probe.level;
  };
  const getFrequency = AnalyserNode.prototype.getByteFrequencyData;
  AnalyserNode.prototype.getByteFrequencyData = function (data) {
    getFrequency.call(this, data);
    probe.meterReads++;
    data.fill(probe.level * 255);
  };
  // WebKit may recreate the MediaDevices wrapper; patch its stable prototype.
  Object.defineProperty(Object.getPrototypeOf(navigator.mediaDevices), 'getUserMedia', {
    configurable: true,
    value: async () => {
      probe.gets++;
      if (probe.denied) throw new DOMException('Test permission denied', 'NotAllowedError');
      const context = new Context();
      const oscillator = context.createOscillator();
      const destination = context.createMediaStreamDestination();
      const stream = destination.stream;
      const tracks = stream.getTracks();
      // Keep native wrappers stable so WebKit retains each track's stop observer.
      Object.defineProperty(stream, 'getTracks', {value: () => tracks});
      oscillator.connect(destination);
      oscillator.start();
      await context.resume();
      for (const track of tracks) {
        probe.tracks++;
        const stop = track.stop.bind(track);
        let stopped = false;
        track.stop = () => {
          if (!stopped) {
            stopped = true;
            probe.trackStops++;
            oscillator.stop();
            context.close();
          }
          stop();
        };
      }
      if (probe.holdPermission) {
        await new Promise(resolve => {
          window.__releaseAttemptPermission = () => {
            window.__releaseAttemptPermission = null;
            resolve();
          };
        });
      }
      return stream;
    },
  });
  class Recorder extends EventTarget {
    static isTypeSupported(type) { return type.split(';')[0] === mime.split(';')[0]; }
    constructor(stream, options = {}) {
      super();
      if (options.mimeType && !Recorder.isTypeSupported(options.mimeType)) {
        throw new DOMException('Unsupported test encoding', 'NotSupportedError');
      }
      this.stream = stream;
      this.mimeType = options.mimeType || mime;
      this.state = 'inactive';
    }
    start() {
      this.state = 'recording';
      probe.starts++;
      this.emit('start', new Event('start'));
    }
    requestData() {
      const event = new Event('dataavailable');
      Object.defineProperty(event, 'data', {value: new Blob([
        probe.payloadSize ? new Uint8Array(probe.payloadSize) : bytes,
      ], {type: this.mimeType})});
      this.emit('dataavailable', event);
    }
    stop() {
      if (this.state === 'inactive') throw new DOMException('Inactive', 'InvalidStateError');
      this.state = 'inactive';
      probe.stops++;
      queueMicrotask(() => {
        this.requestData();
        this.emit('stop', new Event('stop'));
      });
    }
    emit(name, event) {
      this.dispatchEvent(event);
      this['on' + name]?.(event);
    }
  }
  Object.defineProperty(window, 'MediaRecorder', {configurable: true, value: Recorder});
  const create = URL.createObjectURL.bind(URL);
  const revoke = URL.revokeObjectURL.bind(URL);
  URL.createObjectURL = blob => {
    const url = create(blob);
    probe.createdUrls.push(url);
    return url;
  };
  URL.revokeObjectURL = url => { probe.revokedUrls.push(url); revoke(url); };
})();
