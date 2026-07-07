# Validation Notes

This file records benchmark values used to check the desktop solver. The reliable solved examples currently available in the project are the textbook pages supplied by the user. Public web search did not return clean, reproducible solved Khosla examples with complete input geometry and correction data.

## Benchmark 1: Three-Pile Barrage Floor

Reference target values from the supplied textbook solution:

| Pile | Point | Corrected pressure % |
|---|---:|---:|
| Upstream pile 1 | E1 | 100.00 |
| Upstream pile 1 | D1 | 80.00 |
| Upstream pile 1 | C1 | 74.38 |
| Intermediate pile 2 | E2 | 66.95 |
| Intermediate pile 2 | D2 | 63.00 |
| Intermediate pile 2 | C2 | 59.72 |
| Downstream pile 3 | E3 | 36.22 |
| Downstream pile 3 | D3 | 32.00 |
| Downstream pile 3 | C3 | 0.00 |

Exit gradient target:

| Quantity | Target |
|---|---:|
| Total head H | 6.00 m |
| Downstream cutoff depth d | 10.30 m |
| Floor length b | 57.00 m |
| Exit gradient GE | 0.105 |

Notes:
- Khosla curve-read values in the textbook are rounded, so a small difference is expected when direct analytical equations are used.
- Slope correction requires the exact point location at the start or end of the slope. If that geometric condition is not explicitly represented in the app inputs, the app should not force a global slope correction onto every pile point.

## Benchmark 2: Analytical Check for Uncorrected Pressures

Reference target values from the supplied analytical solution:

| Pile | Point | Analytical pressure % |
|---|---:|---:|
| Upstream pile 1 | C1 | 71.30 |
| Upstream pile 1 | D1 | 80.10 |
| Intermediate pile 2 | E2 | 70.80 |
| Intermediate pile 2 | D2 | 63.20 |
| Intermediate pile 2 | C2 | 56.40 |
| Downstream pile 3 | E3 | 37.00 |
| Downstream pile 3 | D3 | 25.40 |
| Downstream pile 3 | C3 | 0.00 |

## Benchmark 3: Two-Pile Weir Floor

Reference target values from the supplied textbook solution:

| Quantity | Target |
|---|---:|
| Floor length b | 16.00 m |
| Upstream pile depth | 4.00 m |
| Downstream pile depth | 5.00 m |
| Net head H | 2.50 m |
| Corrected C1 pressure % | 63.00 |
| C1 uplift head | 1.575 m |
| Corrected downstream E pressure % | 42.10 |
| Downstream E uplift head | 1.05 m |

## Benchmark 4: Regulator Floor Thickness and Exit Gradient

Reference target values from the supplied textbook solution:

| Quantity | Target |
|---|---:|
| Floor length b | 13.00 m |
| Total head H | 1.50 m |
| Upstream cutoff depth | 1.50 m |
| Downstream cutoff depth | 2.00 m |
| Corrected C1 pressure % | 72.00 |
| Upstream end required thickness | 1.00 m |
| Downstream E corrected pressure % | 32.60 |
| Downstream end required thickness | 0.40 m |
| Mid-floor thickness | 0.70 m |
| Exit gradient GE | 0.123 |

