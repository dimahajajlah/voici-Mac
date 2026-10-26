# voiceclone (Intel Mac edition)

Clone your own voice from a short recording, then speak any text with it. Runs locally and free,
Arabic and English supported.

## Setup (once)

1. Install Apple's command line tools if you don't have them (`xcode-select --install`). One dependency
   has no prebuilt Intel-Mac version and gets compiled during install, which takes a few minutes.
2. Install Python 3.11 (python.org installer or `brew install python@3.11`).
   Python 3.13+ will NOT work: PyTorch's last Intel-Mac build is 2.2.2, which supports up to 3.12.
3. In Terminal, from this folder:

       bash setup_mac.sh
       source .venv/bin/activate
       python voiceclone.py --check

## Record your voice

Voice Memos or QuickTime is fine (m4a works, converted automatically).
15-30 seconds, quiet room, natural speaking pace, no music or echo. Read something in the tone
you want the output to have.

## Use

    python voiceclone.py --ref me.m4a --text "Hello, this is my cloned voice." --out hello.wav
    python voiceclone.py --ref me.m4a --text "مرحبا، هذا صوتي" --out arabic.wav
    python voiceclone.py --ref me.m4a --text-file script.txt --out script.wav
    python voiceclone.py --ref me.m4a        # interactive: model loads once, type lines, get output_001.wav...

First run downloads the model (~2 GB) and asks you to accept the Coqui license (CPML, non-commercial).

## Speed expectations

No GPU on this Mac, so everything runs on the CPU. Expect generation to take several times longer
than the audio's length. Tips: use interactive mode (model loads once), keep texts short while
testing, and close heavy apps (Chrome) so RAM and CPU are free.

## Troubleshooting

- "A module compiled with NumPy 1.x cannot be run in NumPy 2": `pip install "numpy<2"`
- pip can't find torch 2.2.2: you're on Python 3.13+, recreate the venv with 3.11.
- Build error mentioning a compiler or `monotonic_alignment_search`: command line tools are missing or incomplete, run `xcode-select --install`.
- Anything else: run `python voiceclone.py --check` and send the output.

## Too slow? Use the free-GPU notebook

Upload `voiceclone_colab.ipynb` to https://colab.research.google.com, set the runtime to T4 GPU, and run the
cells top to bottom. Same model, same clone, generation takes seconds instead of minutes.
