# Harness vs Public Baselines — per-instance verdict matrix

Legend: ✓ resolved · ✗ failed · ∅ no patch generated · ! error · - missing

| # | instance | tier | diff | harness | oh/o47 | oh/o46 | sonar/o45 | oh/o45 | oh/s4 | tools/o4 | swea/s4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | astropy-14309 | easy | all | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | django-10097 | easy | spl | ✗ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |
| 3 | matplotlib-20676 | easy | few | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 4 | astropy-14539 | medium | maj | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✓ |
| 5 | django-11149 | medium | spl | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✓ |
| 6 | matplotlib-20488 | medium | spl | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ |
| 7 | xarray-6599 | medium | few | ✓ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✗ |
| 8 | astropy-14369 | hard | spl | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |
| 9 | django-10554 | hard | few | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 10 | xarray-6992 | hard | few | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

## Aggregate resolve rates

| system | overall | easy | medium | hard |
|---|---|---|---|---|
| harness | 7/10 (70%) | 1/3 (33%) | 4/4 (100%) | 2/3 (67%) |
| oh/o47 | 6/10 (60%) | 2/3 (67%) | 4/4 (100%) | 0/3 (0%) |
| oh/o46 | 6/10 (60%) | 2/3 (67%) | 4/4 (100%) | 0/3 (0%) |
| sonar/o45 | 4/10 (40%) | 1/3 (33%) | 3/4 (75%) | 0/3 (0%) |
| oh/o45 | 4/10 (40%) | 1/3 (33%) | 2/4 (50%) | 1/3 (33%) |
| oh/s4 | 4/10 (40%) | 2/3 (67%) | 1/4 (25%) | 1/3 (33%) |
| tools/o4 | 6/10 (60%) | 3/3 (100%) | 2/4 (50%) | 1/3 (33%) |
| swea/s4 | 4/10 (40%) | 2/3 (67%) | 2/4 (50%) | 0/3 (0%) |

## Differentiation analysis

- **Breakthroughs** (harness solved a 0-1 baseline instance): 3
  - `pydata__xarray-6599` (medium)
  - `django__django-10554` (hard)
  - `pydata__xarray-6992` (hard)
- **Regressions** (harness failed an all-solved instance): 0
- **Uniquely solved by harness**: 2
  - `django__django-10554`
  - `pydata__xarray-6992`
- **Uniquely failed by harness**: 0
