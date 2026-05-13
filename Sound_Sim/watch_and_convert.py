from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pathlib import Path
import time

import numpy as np
import wave
import re

def parse_csv_like(path: Path):
    t_list, x_list = [], []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or not re.search(r"\d", s):
                continue

            parts_ws = s.split()
            if len(parts_ws) >= 2:
                a, b = parts_ws[0], parts_ws[1]
            else:
                nums = re.findall(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?", s)
                if len(nums) < 2:
                    continue
                a, b = nums[0], nums[1]

            a = a.replace(",", ".")
            b = b.replace(",", ".")
            try:
                t = float(a); x = float(b)
            except ValueError:
                continue
            t_list.append(t); x_list.append(x)

    if len(t_list) < 2:
        raise ValueError("Not enough points parsed.")

    t = np.array(t_list, float)
    x = np.array(x_list, float)
    idx = np.argsort(t)
    return t[idx], x[idx]

def resample_to_fs(t, x, fs=44100):
    t0, t1 = t[0], t[-1]
    n = int(np.floor((t1 - t0) * fs)) + 1
    tu = t0 + np.arange(n) / fs
    xu = np.interp(tu, t, x)
    return xu

def to_int16(x, peak=0.98):
    x = np.nan_to_num(x)
    m = np.max(np.abs(x)) if x.size else 0.0
    if m < 1e-12:
        y = np.zeros_like(x)
    else:
        y = (x / m) * peak
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767).astype(np.int16)

def write_wav(path: Path, samples: np.ndarray, fs=44100):
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(fs)
        wf.writeframes(samples.tobytes())

def convert(csv_path: Path, fs=44100):
    # 等文件写完（避免 AD 还在导出）
    for _ in range(20):
        try:
            size1 = csv_path.stat().st_size
            time.sleep(0.2)
            size2 = csv_path.stat().st_size
            if size1 == size2 and size2 > 0:
                break
        except FileNotFoundError:
            time.sleep(0.2)

    t, x = parse_csv_like(csv_path)
    y = resample_to_fs(t, x, fs=fs)
    s16 = to_int16(y)
    wav_path = csv_path.with_suffix(".wav")
    write_wav(wav_path, s16, fs=fs)
    print(f"Converted: {csv_path.name} -> {wav_path.name}")

class Handler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        p = Path(event.src_path)
        if p.suffix.lower() in [".csv", ".txt", ".pwl"]:
            try:
                convert(p, fs=44100)
            except Exception as e:
                print("Convert failed:", p.name, e)

if __name__ == "__main__":
    watch_dir = Path(r"C:\Users\陈大志\Desktop\效果器仿真代码\AD_sim_out")  # 改成你的导出目录
    watch_dir.mkdir(parents=True, exist_ok=True)

    observer = Observer()
    observer.schedule(Handler(), str(watch_dir), recursive=False)
    observer.start()
    print("Watching:", watch_dir)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()