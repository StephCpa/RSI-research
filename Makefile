PYTHON ?= python3
P1 := P1
FIG := $(P1)/figures/fig_gate_v02.pdf
TEX := $(P1)/manuscript/p1_manuscript_v1.tex
PDF := $(P1)/manuscript/p1_manuscript_v1.pdf

.PHONY: verify figure paper finite-sample-quick finite-sample clean

verify:
	$(PYTHON) $(P1)/run_all.py

figure:
	$(PYTHON) $(P1)/figures/fig.py

paper: figure
	cd $(P1)/manuscript && pdflatex -interaction=nonstopmode p1_manuscript_v1.tex
	cd $(P1)/manuscript && pdflatex -interaction=nonstopmode p1_manuscript_v1.tex

finite-sample-quick:
	$(PYTHON) $(P1)/experiments/finite_sample.py --quick

finite-sample:
	$(PYTHON) $(P1)/experiments/finite_sample.py

clean:
	rm -f $(P1)/manuscript/*.aux $(P1)/manuscript/*.log $(P1)/manuscript/*.out
