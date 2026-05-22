# Harness vs Public Baselines — per-instance verdict matrix

Legend: ✓ resolved · ✗ failed · ∅ no patch generated · ! error · - missing

| # | instance | tier | diff | harness | sonar/o45 | oh/o45 | oh/s4 | tools/o4 | swea/s4 |
|---|---|---|---|---|---|---|---|---|---|
| 1 | astropy-14309 | easy | all | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | django-10097 | easy | spl | ✗ | - | - | ✓ | ✓ | ✓ |
| 3 | matplotlib-20676 | easy | few | - | - | - | - | ✓ | - |
| 4 | astropy-14539 | medium | maj | ✓ | ✓ | - | ✓ | ✓ | ✓ |
| 5 | django-11149 | medium | spl | - | ✓ | ✓ | - | - | ✓ |
| 6 | matplotlib-20488 | medium | spl | - | ✓ | ✓ | - | - | - |
| 7 | xarray-6599 | medium | few | - | - | - | - | ✓ | - |
| 8 | astropy-14369 | hard | spl | ✗ | - | ✓ | ✓ | ✓ | - |
| 9 | django-10554 | hard | few | ✓ | - | - | - | - | - |
| 10 | xarray-6992 | hard | few | ✓ | - | - | - | - | - |

## Aggregate resolve rates

| system | overall | easy | medium | hard |
|---|---|---|---|---|
| harness | 4/6 (67%) | 1/2 (50%) | 1/1 (100%) | 2/3 (67%) |
| sonar/o45 | 4/4 (100%) | 1/1 (100%) | 3/3 (100%) | n/a |
| oh/o45 | 4/4 (100%) | 1/1 (100%) | 2/2 (100%) | 1/1 (100%) |
| oh/s4 | 4/4 (100%) | 2/2 (100%) | 1/1 (100%) | 1/1 (100%) |
| tools/o4 | 6/6 (100%) | 3/3 (100%) | 2/2 (100%) | 1/1 (100%) |
| swea/s4 | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | n/a |

## Differentiation analysis

- **Breakthroughs** (harness solved a 0-1 baseline instance): 2
  - `django__django-10554` (hard)
  - `pydata__xarray-6992` (hard)
- **Regressions** (harness failed an all-solved instance): 0
- **Uniquely solved by harness**: 2
  - `django__django-10554`
  - `pydata__xarray-6992`
- **Uniquely failed by harness**: 0
