# Reconnaissance: does anchor rejection restore the ratchet?

Start theta_LID = 110.6 deg; the event needs 135.6 deg (an advance of 25.0). Swarm of 4 x 5 ps, commit 5 ps, 8 cycles, 50,000 steps per execution -- identical to the earlier run. 3 repeats per condition.

## no ratchet (earlier run's defaults)

| repeat | per-cycle anchor theta_LID (deg) | net advance |
| --- | --- | --- |
| 0 | 111.8, 116.6, 118.6, 119.5, 118.3, 116.5, 117.5, 119.6 | +9.1 |
| 1 | 115.3, 117.1, 116.3, 114.0, 115.1, 115.7, 121.2, 117.6 | +7.0 |
| 2 | 110.8, 111.2, 110.4, 109.9, 109.2, 112.0, 109.9, 120.0 | +9.4 |

- Net advance: +8.5 deg mean (range +7.0 to +9.4).
- Peak advance reached at any cycle: +9.7 deg mean (range +9.1 to +10.6).
- Fraction of cycle-to-cycle steps that did not regress: 0.57 (1.00 would be a strict hill-climb).

## ratchet (reject worse anchor and tau2)

| repeat | per-cycle anchor theta_LID (deg) | net advance |
| --- | --- | --- |
| 0 | 117.6, 117.6, 117.6, 117.6, 117.6, 117.6, 117.6, 117.6 | +7.0 |
| 1 | 114.3, 116.1, 119.1, 119.2, 119.2, 122.4, 122.4, 122.4 | +11.8 |
| 2 | 113.3, 121.7, 121.7, 121.7, 122.8, 122.8, 123.3, 123.8 | +13.3 |

- Net advance: +10.7 deg mean (range +7.0 to +13.3).
- Peak advance reached at any cycle: +10.7 deg mean (range +7.0 to +13.3).
- Fraction of cycle-to-cycle steps that did not regress: 1.00 (1.00 would be a strict hill-climb).

Cost: 300,000 steps in 13 min.
