class PikarMicCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0];
    const channel = input && input[0];

    if (channel && channel.length > 0) {
      this.port.postMessage(new Float32Array(channel));
    }

    return true;
  }
}

registerProcessor('pikar-mic-capture', PikarMicCaptureProcessor);
