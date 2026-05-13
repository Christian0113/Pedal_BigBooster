import re
import wave
import numpy as np
from pathlib import Path

def parse_csv_like(path: Path):
    """
    Read a 'csv' that may actually be:
      - space/tab separated
      - comma separated
      - semicolon separated
    and may use comma as decimal separator.
    Returns: t (seconds), x (float)
    """
    t_list = []
    x_list = []

    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue

            # Skip header lines like: "S VOUT" or anything without a digit
            if not re.search(r"\d", s):
                continue

            # Many files use decimal comma, e.g. 0,0001 ; -0,01
            # Also sometimes the delimiter is whitespace, sometimes comma/semicolon.
            # Strategy:
            # 1) If there are at least 2 whitespace-separated tokens -> use that.
            parts_ws = s.split()
            if len(parts_ws) >= 2:
                a, b = parts_ws[0], parts_ws[1]
            else:
                # 2) Otherwise try split by semicolon first
                if ";" in s:
                    parts = s.split(";")
                else:
                    # 3) Otherwise split by comma
                    parts = s.split(",")

                if len(parts) < 2:
                    continue

                # If decimal comma is used, splitting by comma breaks numbers.
                # Detect scientific notation token like "1,234E-06" split into ["1", "234E-06", ...]
                # We'll reconstruct first two numbers by regex.
                nums = re.findall(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?", s)
                if len(nums) < 2:
                    continue
                a, b = nums[0], nums[1]

            # Convert decimal comma to dot
            a = a.replace(",", ".")
            b = b.replace(",", ".")

            try:
                t = float(a)
                x = float(b)
            except ValueError:
                continue

            t_list.append(t)
            x_list.append(x)

    if len(t_list) < 2:
        raise ValueError("无法从文件中解析出足够的数据点，请检查 CSV 内容/分隔符/表头。")

    t_arr = np.array(t_list, dtype=float)
    x_arr = np.array(x_list, dtype=float)

    # Ensure sorted by time
    idx = np.argsort(t_arr)
    return t_arr[idx], x_arr[idx]

def resample_to_fs(t, x, fs=44100):
    """
    Resample arbitrary time/value pairs to uniform sampling rate fs.
    """
    t0 = t[0]
    t1 = t[-1]
    n = int(np.floor((t1 - t0) * fs)) + 1
    tu = t0 + np.arange(n) / fs
    xu = np.interp(tu, t, x)
    return tu, xu

def normalize_to_int16(x, peak=0.98):
    """
    Normalize float signal to int16 PCM.
    """
    x = np.nan_to_num(x, nan=0.0, posinf=0.0, neginf=0.0)
    m = np.max(np.abs(x)) if x.size else 0.0
    if m < 1e-12:
        y = np.zeros_like(x)
    else:
        y = (x / m) * peak
    y = np.clip(y, -1.0, 1.0)
    return (y * 32767.0).astype(np.int16)

def write_wav(path: Path, samples_int16: np.ndarray, fs=44100):
    """
    Write mono 16-bit PCM wav.
    """
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(fs)
        wf.writeframes(samples_int16.tobytes())

def main():
    import argparse
    ap = argparse.ArgumentParser(description="Convert Altium-export-like CSV (time,value) to WAV.")
    ap.add_argument("csv", type=str, help="Input CSV file path (e.g. VOUT.csv)")
    ap.add_argument("-o", "--out", type=str, default=None, help="Output wav path (default: same name .wav)")
    ap.add_argument("--fs", type=int, default=44100, help="Target sample rate, default 44100")
    ap.add_argument("--no-resample", action="store_true", help="Do not resample, use inferred fs (only if uniform)")
    args = ap.parse_args()

    in_path = Path(args.csv)
    out_path = Path(args.out) if args.out else in_path.with_suffix(".wav")

    t, x = parse_csv_like(in_path)

    if args.no_resample:
        # Infer fs from median dt if uniform enough
        dt = np.diff(t)
        dt_med = np.median(dt)
        if dt_med <= 0:
            raise ValueError("时间列不递增，无法推断采样率。")
        fs = int(round(1.0 / dt_med))
        # Check uniformity (optional)
        if np.max(np.abs(dt - dt_med)) > 1e-6 * max(dt_med, 1e-12):
            print("警告：时间步长不均匀，建议不要使用 --no-resample。将继续按推断 fs 写出。")
        samples = normalize_to_int16(x)
        write_wav(out_path, samples, fs=fs)
        print(f"OK: {out_path}  (fs inferred ≈ {fs} Hz)")
    else:
        tu, xu = resample_to_fs(t, x, fs=args.fs)
        samples = normalize_to_int16(xu)
        write_wav(out_path, samples, fs=args.fs)
        dur = (tu[-1] - tu[0]) if tu.size else 0
        print(f"OK: {out_path}  (fs={args.fs} Hz, duration≈{dur:.3f}s, samples={samples.size})")

if __name__ == "__main__":
    main()