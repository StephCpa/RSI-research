PYTHON ?= python3
P1 := P1
FIG := $(P1)/figures/fig_gate_v02.pdf
TEX := $(P1)/manuscript/p1_manuscript_v1.tex
PDF := $(P1)/manuscript/p1_manuscript_v1.pdf

.PHONY: verify figure paper finite-sample-quick finite-sample coverage-quick coverage degeneracy-quick degeneracy audit-freeze audit-ds-excess audit-allocation clean

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

coverage-quick:
	$(PYTHON) $(P1)/experiments/finite_sample_coverage.py --quick

coverage:
	$(PYTHON) $(P1)/experiments/finite_sample_coverage.py

degeneracy-quick:
	$(PYTHON) $(P1)/experiments/degeneracy_paths.py --quick

degeneracy:
	$(PYTHON) $(P1)/experiments/degeneracy_paths.py

audit-freeze:
	$(PYTHON) $(P1)/experiments/freeze_audit_config.py $(P1)/experiments/audit_config.json

audit-ds-excess:
	$(PYTHON) $(P1)/experiments/ds_excess.py $(P1)/experiments/audit_table.csv

audit-allocation:
	$(PYTHON) $(P1)/experiments/audit_allocation.py $(P1)/experiments/audit_table.csv

clean:
	rm -f $(P1)/manuscript/*.aux $(P1)/manuscript/*.log $(P1)/manuscript/*.out
