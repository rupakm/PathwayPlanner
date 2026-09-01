# Conjunctive close_hinge: does the structure follow the angle?

## Event outcomes by specification

| event specification | outcomes over attempts |
| --- | --- |
| angle only | success, success, success |
| angle and RMSD (conjunctive) | success, success, success |

Open start theta_LID = 143.8 deg. The hinge is closed under a k = 2000 kJ/mol/nm^2 restraint for 50 ps, then the restraint is removed and theta_LID is watched for 250 ps at 5 ps resolution, 2 replicas from each of 3 closed successors.

'Reopened' below means theta_LID returned above 131.3 deg, half the 25.0 deg event back toward the open start.

| successor | replica | closed at | after 50 ps | after 250 ps | max | reopened? |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 104.7 | 103.1 | 106.0 | 112.9 | no |
| 0 | 1 | 104.7 | 106.3 | 107.7 | 116.9 | no |
| 1 | 0 | 105.2 | 102.3 | 99.0 | 110.9 | no |
| 1 | 1 | 105.2 | 104.6 | 95.5 | 108.6 | no |
| 2 | 0 | 111.5 | 121.0 | 107.0 | 127.9 | no |
| 2 | 1 | 111.5 | 113.2 | 115.2 | 120.8 | no |

- Closed to 107.1 deg on average; after 250 ps unbiased the mean is 105.1 deg (open start was 143.8).
- Reopened past 131.3 deg: 0/6 replicas.
- RMSD to the closed crystal: 6.1 A at the open start, 3.5 A when the event fired, 4.2 A after 250 ps unbiased. The endpoints are 7.1 A apart, so this is the fraction of the conformational change the action actually delivered.

## Traces (theta_LID, deg, every 5 ps)

- successor 0 replica 0: 109, 104, 107, 103, 101, 103, 105, 101, 100, 102, 102, 107, 110, 109, 106, 103, 108, 111, 107, 107, 110, 109, 105, 97, 98
- successor 0 replica 1: 107, 102, 103, 109, 108, 104, 101, 104, 106, 107, 117, 109, 109, 100, 108, 107, 103, 108, 102, 102, 103, 107, 101, 104, 103
- successor 1 replica 0: 104, 107, 111, 107, 109, 106, 108, 105, 102, 101, 101, 103, 98, 100, 101, 104, 101, 98, 99, 100, 100, 100, 98, 96, 101
- successor 1 replica 1: 103, 103, 101, 102, 103, 101, 105, 103, 102, 99, 99, 99, 95, 98, 98, 96, 100, 100, 93, 92, 100, 102, 98, 95, 97
- successor 2 replica 0: 111, 115, 117, 121, 119, 128, 122, 119, 122, 116, 121, 115, 118, 111, 110, 103, 98, 100, 107, 105, 103, 104, 103, 99, 102
- successor 2 replica 1: 112, 114, 114, 114, 113, 113, 119, 115, 119, 113, 115, 117, 116, 116, 115, 117, 109, 119, 114, 116, 115, 114, 118, 118, 116

Cost: 525,000 steps in 31 min.
