# RSI Research

Research materials for the P1 verifier self-calibration / identifiability project.

## Layout

- `P1/manuscript/`: merged LaTeX manuscript.
- `P1/figures/`: source for Figure 1; `make paper` regenerates the PDF/PNG assets.
- `P1/proofs/`: deterministic theorem witnesses, certificates, and constructive inverses.
- `P1/notes/`: historical formal memos and merge notes.
- `P1/run_all.py`: one-command deterministic verification.
- `requirements.txt`: Python dependencies.

Exploratory multistart scans are intentionally not part of the verification target; the manuscript uses exact-rational, algebraic, or interval certificates where claims depend on them.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make verify
make paper
```

`make verify` runs the deterministic proof/certificate scripts and reports per-script runtimes. `certify_singleton_n4.py` uses `python-flint`/Arb for the rigorous Krawczyk certificate; if `python-flint` is unavailable, that script reports `RIGOROUS_CERTIFICATE: NOT RUN`.

`make paper` first regenerates `P1/figures/fig_gate_v02.pdf` and then runs `pdflatex` twice.

## License

MIT; see `LICENSE`.
