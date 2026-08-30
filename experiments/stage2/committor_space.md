# Is the committor determined by phi alone, or by (phi, psi)?

Reconstructed from 22 measurement points saved by the committor profile run; no dynamics were re-run. Reactant basin center [-79.3  50.2] deg, product basin (np.float64(72.0), np.float64(-65.0)) deg, basin radius 40.0 deg.

| phi (deg) | psi (deg) | q_hat | B | A | unresolved |
| --- | --- | --- | --- | --- | --- |
| -54.4 | 46.1 | 0.00 | 0 | 20 | 0 |
| -40.7 | 41.2 | 0.00 | 0 | 20 | 0 |
| -38.0 | 37.6 | 0.00 | 0 | 20 | 0 |
| -27.3 | 36.3 | 0.00 | 0 | 20 | 0 |
| -14.0 | 32.6 | 0.00 | 0 | 20 | 0 |
| -5.1 | 27.0 | 0.00 | 0 | 20 | 0 |
| 4.0 | 25.2 | 0.00 | 0 | 20 | 0 |
| 14.0 | 9.6 | 0.00 | 0 | 20 | 0 |
| 14.1 | 15.5 | 0.00 | 0 | 40 | 0 |
| 15.7 | 14.1 | 0.00 | 0 | 40 | 0 |
| 17.9 | 17.5 | 0.00 | 0 | 40 | 0 |
| 19.8 | 5.8 | 0.00 | 0 | 40 | 0 |
| 21.6 | 7.1 | 0.00 | 0 | 40 | 0 |
| 22.4 | 19.6 | 0.00 | 0 | 40 | 0 |
| 23.7 | -40.7 | 1.00 | 20 | 0 | 0 |
| 37.3 | -42.5 | 1.00 | 20 | 0 | 0 |
| 47.8 | -67.8 | 1.00 | 20 | 0 | 0 |
| 56.9 | -56.5 | 1.00 | 20 | 0 | 0 |
| 64.5 | -17.5 | 1.00 | 20 | 0 | 0 |
| 72.4 | -58.7 | 1.00 | 20 | 0 | 0 |
| 81.8 | -64.1 | 1.00 | 20 | 0 | 0 |
| 91.4 | -29.1 | 1.00 | 20 | 0 | 0 |

## 1. Configurations that agree in phi
- 8 pairs within 5 deg in phi; 1 of them differ by more than 0.5 in q_hat.
  - phi -40.7 / -38.0 deg (delta 2.7), psi 41.2 / 37.6 deg (delta 3.6), q_hat 0.00 / 0.00
  - phi 14.0 / 14.1 deg (delta 0.1), psi 9.6 / 15.5 deg (delta 5.9), q_hat 0.00 / 0.00
  - phi 14.1 / 15.7 deg (delta 1.6), psi 15.5 / 14.1 deg (delta 1.4), q_hat 0.00 / 0.00
  - phi 15.7 / 17.9 deg (delta 2.2), psi 14.1 / 17.5 deg (delta 3.3), q_hat 0.00 / 0.00
  - phi 17.9 / 19.8 deg (delta 1.9), psi 17.5 / 5.8 deg (delta 11.6), q_hat 0.00 / 0.00
  - phi 19.8 / 21.6 deg (delta 1.8), psi 5.8 / 7.1 deg (delta 1.3), q_hat 0.00 / 0.00
  - phi 21.6 / 22.4 deg (delta 0.9), psi 7.1 / 19.6 deg (delta 12.5), q_hat 0.00 / 0.00
  - phi 22.4 / 23.7 deg (delta 1.3), psi 19.6 / -40.7 deg (delta 60.3), q_hat 0.00 / 1.00

## 2. Binomial model comparison
- Model A, phi only: log-likelihood -40.53, AIC 87.05
- Model B, phi and psi: log-likelihood -0.75, AIC 11.50
- Likelihood-ratio statistic 79.55 on 2 df, approximate p = 0.0000 (approximate: an L2 penalty of 0.01 is applied because points at q_hat = 0 or 1 give perfect separation).
- Verdict by AIC: **psi adds explanatory power**.

## 3. Can this design attribute the committor to a coordinate?
- Pearson correlation of phi with psi across the sampled configurations: **-0.855**.
- phi ranges: q_hat < 0.5 reaches 22.4 deg, q_hat >= 0.5 starts at 23.7 deg — phi separates the two classes without overlap.

## Interpretation
- The committor turns over sharply within the sampled ensemble, between phi 22.4 and 23.7 deg — equivalently between psi 19.6 and -40.7 deg.
- **This dataset cannot attribute the committor to phi or to psi individually.** Every configuration was harvested from phi-biased trajectories, along which psi follows phi; the two coordinates are correlated at r = -0.855 across the measurement points. The pair that straddles the transition differs in both coordinates at once, and the model comparison in section 2 is confounded by the same collinearity: with two near-collinear predictors, the larger model can fit a sharper threshold without any genuine psi dependence. The AIC gap is therefore not evidence that psi matters.
- Separating the two requires configurations that break the correlation: hold phi fixed by restraint and sample a range of psi, then measure the committor across that range. Until that is done, the honest statement is that the transition is sharp in the sampled ensemble, and which coordinate controls it is open.
- The classifier and CV space used throughout Stage 2 are the full periodic (phi, psi) plane; only the profile's *reporting axis* was phi. Nothing here indicts the Stage 2 evaluation: it bears on how the profile should be described, not on how the actions were classified.
