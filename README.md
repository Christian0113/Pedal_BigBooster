# Pedal_BigBooster

A custom-designed guitar booster pedal project developed with **Altium Designer**, including schematic design and audio signal testing.

> **Note:**
> This project is still under active development and iterative refinement.
> Circuit topology, component values, PCB layout, and simulation workflow may continue to change over time.

---

This project contains a simple audio simulation pipeline for testing guitar signals through the simulated circuit.

### 1. Convert WAV to LTspice Input

`wav2ltspice.py` converts a `.wav` audio file into an LTspice-compatible signal file.

The generated file can then be imported into Altium/LTspice simulations as an input signal source.

```text
.wav file
   ↓
wav2ltspice.py
   ↓
LTspice input signal
   ↓
Altium / LTspice Simulation
```

### 2. Convert Simulation Output Back to Audio

`csv2wav.py` converts the exported simulation `.csv` waveform back into a playable `.wav` audio file.

```text
Simulation CSV output
   ↓
csv2wav.py
   ↓
.wav audio output
```
