from scipy.io import wavfile

fs, data = wavfile.read("Freesound.wav")
print("OK, fs =", fs, "shape =", getattr(data, "shape", None), "dtype =", data.dtype)