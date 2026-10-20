class PcmDownsampleProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / 8000;
    this.acc = 0;
    this.accN = 0;
    this.frame = new Int16Array(512);
    this.filled = 0;
    this.frameSq = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;
    for (let i = 0; i < channel.length; i++) {
      this.acc += channel[i];
      this.accN += 1;
      if (this.accN + 0.0001 >= this.ratio) {
        const sample = Math.max(-1, Math.min(1, this.acc / this.accN));
        this.frame[this.filled] = (sample * 32767) | 0;
        this.frameSq += sample * sample;
        this.filled += 1;
        this.acc = 0;
        this.accN = 0;
        if (this.filled === 512) {
          const pcm = this.frame;
          const rms = Math.sqrt(this.frameSq / 512);
          this.frame = new Int16Array(512);
          this.filled = 0;
          this.frameSq = 0;
          this.port.postMessage({ type: "frame", pcm, rms }, [pcm.buffer]);
        }
      }
    }
    return true;
  }
}

registerProcessor("pcm-downsample", PcmDownsampleProcessor);
