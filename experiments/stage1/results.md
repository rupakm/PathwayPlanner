# Stage 1 results (Wolfe-Quapp)

Parameters: kT=0.7, dt=1e-3, n_steps=4000, replicas=6, bias=2.5, batches of 30, delta_comp runs=100.

## 1. Reproducibility
- Batch 1 outcomes: {'partial': 6, 'success': 24}
- Batch 2 outcomes: {'success': 27, 'failure': 1, 'partial': 2}
- JS divergence: **0.0440** (gate: < 0.1)
- Gate: PASS

## 2. Contract calibration
- Recorded success rate (batch 1): 0.800
- Held-out success rate (batch 2): 0.900
- Calibration error: **0.100** (gate: < 0.2)
- Gate: PASS

## 3. delta_comp (cross ; relax)
- Fine abstraction: actual=0.450, predicted=0.522, **delta=0.072**
  - class weights: {(True, np.False_): 0.39, (True, np.True_): 0.19, (False, np.True_): 0.34, (False, np.False_): 0.02}
- Coarse abstraction: actual=0.520, predicted=0.797, **delta=0.277**
- Fine <= coarse: PASS

## 4. Committor validation of success labels
- 24 success successors; reference q range [1.000, 1.000] (gate: all > 0.5)
- Gate: PASS

## Stage 1 gate: PASS
