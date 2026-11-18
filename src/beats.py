"""Estimate a stable beat grid from positive low-frequency onset changes."""
import subprocess
import numpy as np

def detect_peaks(energies, hop_seconds, min_spacing=0.3):
    """Compatibility helper: return isolated peaks from an energy envelope."""
    if len(energies)<3: return []
    values=np.asarray(energies,dtype=float)
    threshold=float(values.mean()+0.5*values.std())
    if threshold <= 0: return []
    peaks=[]
    for i in range(1,len(values)-1):
        time=i*hop_seconds
        if values[i]>threshold and values[i]>=values[i-1] and values[i]>values[i+1] and (not peaks or time-peaks[-1]>=min_spacing):
            peaks.append(round(time,3))
    return peaks

def estimate_beat_grid(onset_strength, hop_seconds, duration):
    # 对起音强度做自相关，估计大致节拍周期和相位，再贴近实际起音。
    values=np.asarray(onset_strength,dtype=float)
    if len(values)<16 or duration<=0: return []
    values=np.maximum(values-np.mean(values),0)
    if np.max(values)<1e-8: return []
    values/=np.linalg.norm(values)+1e-12
    # Search a practical music pulse range of roughly 60–160 BPM.
    low=max(2,round(60/160/hop_seconds))
    high=min(len(values)//3,round(60/60/hop_seconds))
    scores=[]
    # 不依赖音频模型；比较不同延迟的起音相似度，估计重复节拍周期。
    for lag in range(low,high+1):
        scores.append(float(np.dot(values[:-lag],values[lag:])))
    if not scores or max(scores)<0.03: return []
    period=(low+int(np.argmax(scores)))*hop_seconds
    # Pick the phase with the strongest repeated attacks, then refine locally.
    bins=max(1,round(period/hop_seconds))
    phase_scores=[sum(values[k] for k in range(phase,len(values),bins)) for phase in range(bins)]
    # 选周期内累计起音最强的相位，减少鼓点落在拍格之间的偏差。
    phase=int(np.argmax(phase_scores))*hop_seconds
    beats=[]
    t=phase
    while t<duration:
        center=round(t/hop_seconds)
        radius=max(1,round(0.10/hop_seconds))
        a=max(0,center-radius); b=min(len(values),center+radius+1)
        if a<b:
            peak=a+int(np.argmax(values[a:b]))
            refined=peak*hop_seconds
            if not beats or refined-beats[-1]>=period*0.75:
                beats.append(round(refined,3))
        t+=period
    return beats

def analyze_music(path, max_seconds=90):
    # FFmpeg 解码本地歌曲；只分析低频能量的正向变化，以近似鼓点攻击。
    sample_rate=11025
    cmd=['ffmpeg','-v','error','-i',str(path),'-t',str(max_seconds),'-f','s16le','-ac','1','-ar',str(sample_rate),'pipe:1']
    result=subprocess.run(cmd,capture_output=True,check=True)
    samples=np.frombuffer(result.stdout,dtype='<i2').astype(float)/32768.0
    duration=len(samples)/sample_rate
    size=2048; hop=1102; window=np.hanning(size)
    frequencies=np.fft.rfftfreq(size,1/sample_rate)
    low_band=(frequencies>=35)&(frequencies<=180)
    energy=[]
    for start in range(0,max(0,len(samples)-size),hop):
        spectrum=np.abs(np.fft.rfft(samples[start:start+size]*window))
        energy.append(float(np.sqrt(np.mean(spectrum[low_band]**2))))
    if len(energy)<2: return []
    log_energy=np.log1p(np.asarray(energy)*1000)
    # Positive change emphasizes attacks and reduces the effect of sustained bass.
    novelty=np.maximum(np.diff(log_energy,prepend=log_energy[0]),0)
    smooth=np.convolve(novelty,np.ones(3)/3,mode='same')
    return estimate_beat_grid(smooth,hop/sample_rate,duration)
