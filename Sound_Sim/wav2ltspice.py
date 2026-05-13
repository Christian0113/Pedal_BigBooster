import argparse
import numpy as np
from scipy.io import wavfile
from pathlib import Path

def to_mono(x: np.ndarray) -> np.ndarray:
    if x.ndim == 1:
        return x
    # 多声道取平均
    return x.mean(axis=1)

def normalize_pcm(x: np.ndarray) -> np.ndarray:
    # 把 int PCM 转成 [-1,1] 浮点
    if np.issubdtype(x.dtype, np.integer):
        info = np.iinfo(x.dtype)
        # 注意：有符号/无符号都处理
        if info.min < 0:
            return x.astype(np.float64) / max(abs(info.min), info.max)
        else:
            return (x.astype(np.float64) - info.max / 2) / (info.max / 2)
    return x.astype(np.float64)

def resample_linear(x: np.ndarray, fs_in: int, fs_out: int) -> np.ndarray:
    if fs_out == fs_in:
        return x
    duration = len(x) / fs_in
    n_out = int(np.round(duration * fs_out))
    t_in = np.linspace(0, duration, len(x), endpoint=False)
    t_out = np.linspace(0, duration, n_out, endpoint=False)
    return np.interp(t_out, t_in, x)

def write_pwl(out_pwl: Path, x: np.ndarray, fs: int, vscale: float, vdc: float):
    # 写 LTspice PWL：time(s)  voltage(V)
    # 为避免文件巨大，可在外面先降采样
    dt = 1.0 / fs
    t = np.arange(len(x)) * dt
    y = x * vscale + vdc

    with out_pwl.open("w", encoding="utf-8") as f:
        f.write("; LTspice PWL generated from WAV\n")
        f.write("; time(s)\tvoltage(V)\n")
        for ti, yi in zip(t, y):
            f.write(f"{ti:.9e}\t{yi:.9e}\n")

def write_minimal_asc(out_asc: Path, pwl_filename: str, stop_time: float):
    # 一个极简 .asc：V1 -> 节点 in，相对地；并附带 tran 指令
    # 注意：不同 LTspice 版本/平台对坐标不敏感，但这是能直接打开的常见格式
    asc = f"""Version 4
SHEET 1 880 680
WIRE 224 176 96 176
WIRE 352 176 224 176
WIRE 96 240 96 176
WIRE 352 240 352 176
FLAG 96 240 0
SYMBOL voltage 96 160 R0
SYMATTR InstName V1
SYMATTR Value PWL FILE="{pwl_filename}"
SYMBOL res 352 160 R0
SYMATTR InstName Rload
SYMATTR Value 1k
FLAG 352 240 0
TEXT 80 320 Left 2 !.tran 0 {stop_time:.6g}
TEXT 80 360 Left 2 ; node name is "in" at the wire between V1 and Rload
"""
    out_asc.write_text(asc, encoding="utf-8")

def main():
    ap = argparse.ArgumentParser(description="Convert WAV to LTspice PWL + minimal ASC schematic.")
    ap.add_argument("wav", type=str, help="input wav file")
    ap.add_argument("--outdir", type=str, default="ltspice_out", help="output directory")
    ap.add_argument("--channel", type=str, default="mono", choices=["mono", "left", "right"], help="channel selection")
    ap.add_argument("--fs", type=int, default=None, help="output sample rate (Hz). default: original")
    ap.add_argument("--max_seconds", type=float, default=None, help="truncate duration (seconds)")
    ap.add_argument("--vscale", type=float, default=1.0, help="scale [-1,1] audio to volts (Vpeak). e.g. 1.0 => +/-1V")
    ap.add_argument("--vdc", type=float, default=0.0, help="DC offset in volts")
    args = ap.parse_args()

    wav_path = Path(args.wav)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fs_in, data = wavfile.read(wav_path)
    x = normalize_pcm(data)

    if x.ndim == 2:
        if args.channel == "left":
            x = x[:, 0]
        elif args.channel == "right":
            x = x[:, 1]
        else:
            x = to_mono(x)

    if args.max_seconds is not None:
        n = int(args.max_seconds * fs_in)
        x = x[:max(0, n)]

    fs_out = args.fs if args.fs is not None else fs_in
    if fs_out != fs_in:
        x = resample_linear(x, fs_in, fs_out)

    # 生成文件名
    out_pwl = outdir / "signal.pwl"
    out_asc = outdir / "wav_source.asc"

    write_pwl(out_pwl, x, fs_out, args.vscale, args.vdc)
    stop_time = len(x) / fs_out
    write_minimal_asc(out_asc, out_pwl.name, stop_time)

    print(f"OK\n- PWL: {out_pwl}\n- ASC: {out_asc}\nSampleRate: {fs_out} Hz, Duration: {stop_time:.3f} s")

if __name__ == "__main__":
    main()