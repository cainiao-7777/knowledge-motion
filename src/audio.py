"""Generate a quiet original transition accent without external sound assets."""
import wave
import numpy as np

def create_effects_track(path,duration,positions):
    rate=22050
    count=round(duration*rate)
    signal=np.zeros(count,dtype=np.float32)
    length=round(0.15*rate)
    t=np.arange(length)/rate
    envelope=np.exp(-t*35)
    pulse=0.08*np.sin(2*np.pi*(640*t+120*t*t))*envelope
    for position in positions:
        start=round(position*rate)
        if 0 <= start < count:
            n=min(length,count-start)
            signal[start:start+n]+=pulse[:n]
    pcm=(np.clip(signal,-1,1)*32767).astype('<i2')
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(rate)
        stream.writeframes(pcm.tobytes())
