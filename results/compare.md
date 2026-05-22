# Harness vs Public Baselines — per-instance verdict matrix

Legend: ✓ resolved · ✗ failed · ∅ no patch generated · ! error · - missing

| # | instance | tier | diff | harness | sonar | openhands | openhands | tools | sweagent |
|---|---|---|---|---|---|---|---|---|---|
| 1 | astropy-14309 | easy | all | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 2 | django-10097 | easy | spl | - | - | - | ✓ | ✓ | ✓ |
| 3 | matplotlib-20676 | easy | few | - | - | - | - | ✓ | - |
| 4 | astropy-14539 | medium | maj | - | ✓ | - | ✓ | ✓ | ✓ |
| 5 | django-11149 | medium | spl | - | ✓ | ✓ | - | - | ✓ |
| 6 | matplotlib-20488 | medium | spl | - | ✓ | ✓ | - | - | - |
| 7 | xarray-6599 | medium | few | - | - | - | - | ✓ | - |
| 8 | astropy-14369 | hard | spl | - | - | ✓ | ✓ | ✓ | - |
| 9 | django-10554 | hard | few | - | - | - | - | - | - |
| 10 | xarray-6992 | hard | few | - | - | - | - | - | - |

## Aggregate resolve rates

| system | overall | easy | medium | hard |
|---|---|---|---|---|
| harness | 1/1 (100%) | 1/1 (100%) | n/a | n/a |
| sonar | 4/4 (100%) | 1/1 (100%) | 3/3 (100%) | n/a |
| openhands | 4/4 (100%) | 1/1 (100%) | 2/2 (100%) | 1/1 (100%) |
| openhands | 4/4 (100%) | 2/2 (100%) | 1/1 (100%) | 1/1 (100%) |
| tools | 6/6 (100%) | 3/3 (100%) | 2/2 (100%) | 1/1 (100%) |
| sweagent | 4/4 (100%) | 2/2 (100%) | 2/2 (100%) | n/a |

## Differentiation analysis

- **Breakthroughs** (harness solved a 0-1 baseline instance): 0
- **Regressions** (harness failed an all-solved instance): 0
- **Uniquely solved by harness**: 0
- **Uniquely failed by harness**: 0
