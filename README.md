# ENGG2112 — Flu Spread Prediction & Simulation

Modelling influenza spread through Sydney suburbs using ML-driven spreadability scores and a SIR compartmental simulation.

**Team:** 1 software student + 3 biomedical students
**Timeline:** 8 weeks
**Stack:** Python 3.11, scikit-learn, pandas, Flask, JavaScript

## Quick Start

```bash
git clone https://github.com/r0cb/ENGG2112.git
cd ENGG2112
pip install pandas numpy scikit-learn matplotlib seaborn jupyter flask
jupyter notebook notebooks/01_data_exploration.ipynb
```

## Full Project Context

See [MASTER_PLAN.md](./MASTER_PLAN.md) for the complete architecture, data sources, task breakdown, and team assignments.

## Repository Structure

```
ENGG2112/
├── MASTER_PLAN.md          # Full project spec — read this first
├── notebooks/              # Jupyter notebooks (exploration → model → simulation)
├── data/
│   ├── raw/                # Downloaded source files (gitignored)
│   └── processed/          # Merged/cleaned outputs (gitignored)
└── src/                    # Python modules (model, simulation, Flask app)
```
