"""Estimate low-frequency musical accents to suggest scene boundaries."""
import subprocess
import numpy as np

def detect_peaks(energies, hop_seconds, min_spacing=0.3):
    if len(energies)<3: return []
    values=np.asarray(energies,dtype=float)
    threshold=float(values.mean()+0.5*values.std())
    if threshold <= 0: return []
    peaks=[]
    for i in range(1,len(values)-1):
        time=i*hop_seconds
        if values[i] > threshold and values[i] >= values[i-1] and values[i] > values[i+1] and (not peaks or time-peaks[-1] >= min_spacing):
            peaks.append(round(time,3))
    return peaks

def analyze_music(path, max_seconds=90):
    sample_rate=11025
    cmd=['ffmpeg','-v','error','-i',str(path),'-t',str(max_seconds),'-f','s16le','-ac','1','-ar',str(sample_rate),'pipe:1']
    p=subprocess.run(cmd,capture_output=True,check=True)
    samples=np.frombuffer(p.stdout,dtype='<i2').astype(float)/32768.0
    size=2048; hop=1102
    window=np.hanning(size)
    freq=np.fft.rfftfreq(size,1/sample_rate)
    mask=(freq>=35)&(freq<=180)
    energy=[]
    for start in range(0,max(0,len(samples)-size),hop):
        spectrum=np.abs(np.fft.rfft(samples[start:start+size]*window))
        energy.append(float(np.mean(spectrum[mask])))
    return detect_peaks(energy,hop/sample_rate)
