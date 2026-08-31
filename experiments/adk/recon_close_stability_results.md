# Does a restraint-closed LID stay closed?

Open start theta_LID = 143.8 deg. The hinge is closed under a k = 2000 kJ/mol/nm^2 restraint for 50 ps, then the restraint is removed and theta_LID is watched for 250 ps at 5 ps resolution, 2 replicas from each of 3 closed successors.

'Reopened' below means theta_LID returned above 131.3 deg, half the 25.0 deg event back toward the open start.

| successor | replica | closed at | after 50 ps | after 250 ps | max | reopened? |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 101.1 | 103.4 | 127.1 | 128.7 | no |
| 0 | 1 | 101.1 | 104.8 | 106.5 | 108.5 | no |
| 1 | 0 | 99.3 | 101.1 | 95.8 | 111.6 | no |
| 1 | 1 | 99.3 | 105.9 | 90.5 | 110.9 | no |
| 2 | 0 | 99.0 | 99.9 | 100.4 | 109.4 | no |
| 2 | 1 | 99.0 | 95.8 | 89.9 | 100.5 | no |

- Closed to 99.8 deg on average; after 250 ps unbiased the mean is 101.7 deg (open start was 143.8).
- Reopened past 131.3 deg: 0/6 replicas.

## Traces (theta_LID, deg, every 5 ps)

- successor 0 replica 0: 103, 99, 102, 105, 104, 106, 104, 105, 106, 112, 115, 115, 118, 122, 119, 117, 121, 126, 125, 123, 129, 125, 125, 119, 123
- successor 0 replica 1: 102, 96, 98, 106, 105, 102, 99, 101, 102, 108, 108, 105, 105, 99, 106, 106, 100, 101, 103, 105, 101, 106, 99, 101, 103
- successor 1 replica 0: 99, 105, 109, 109, 110, 106, 102, 101, 97, 99, 104, 109, 108, 102, 103, 110, 103, 103, 104, 100, 94, 97, 95, 95, 99
- successor 1 replica 1: 103, 101, 102, 104, 109, 106, 104, 103, 100, 94, 96, 98, 92, 95, 97, 95, 98, 98, 94, 89, 92, 97, 91, 92, 92
- successor 2 replica 0: 97, 102, 98, 106, 100, 109, 99, 96, 97, 96, 93, 96, 97, 95, 95, 93, 91, 92, 99, 97, 96, 97, 98, 94, 96
- successor 2 replica 1: 98, 99, 101, 96, 95, 97, 95, 96, 97, 93, 92, 92, 91, 95, 98, 93, 88, 94, 89, 93, 92, 89, 92, 91, 93

Cost: 525,000 steps in 21 min.
