# Are the choices different from random, irrespective of profitability?

This addresses selection structure, separately from outcome advantage. Data: 62 confirmed closing lines, two no-edge games excluded in each version. No game outcomes enter the choice classifier, the grouping features, or its tuning. All tests are exploratory and follow earlier examination of this same week; p-values are unadjusted for multiple analyses and are not confirmatory findings.

## Original, unadjusted predictions: an unmistakable directional policy

The model selected the away team in 50 of 60 games (83.3%), and the home team in ten. Away picks went 25-25; home picks went 5-5. Overall: 30-30. This is a concrete example of strongly asymmetric choices coexisting with an even ATS record. The likely mechanical explanation is that the model omitted home advantage while the market incorporated it. It does not establish an independent model advantage.

An outcome-blind classifier using only market spread size, whether the favorite was home, and FBS/FCS matchup type predicted 50/60 model choices under leave-one-out evaluation (balanced accuracy 81.1%). None of 20,000 permutations preserving the same total underdog count matched that balanced accuracy; the plus-one Monte Carlo p-value is 0.00005. This largely reflects the away-selection policy, not subtle game-specific insight. FBS-only results were similar. The old method is no longer the website's current prediction policy.

## With home +3: weaker but visible compression structure

Away selections fall to 36/60, versus 24 home selections. Overall ATS is 31-29. The model takes 39 underdogs (65%) and 21 favorites. Against an independent fair favorite/underdog coin, that imbalance has an exact two-sided binomial p-value of 0.027.

More informative than the overall imbalance: the model selects underdogs in 20/24 games with market spreads of 14+ (83.3%), versus 19/36 below 14 (52.8%). Even against a biased coin preserving all 39 underdog selections, permuting which games receive them produces a gap at least this large about 2.7% of the time (two-sided permutation test, 20,000 draws). Under the original no-home-adjustment predictions, the corresponding rates were 83.3% and 50.0% (p=0.013). Thus compression is not wholly created by the later home-field change.

FBS-only follows the same direction after home adjustment: 10/12 large-spread games versus 19/36 smaller-spread games. The permutation p-value is 0.089, so evidence is weaker once FCS games are excluded. Threshold 14 and these hypotheses have already been explored in this conversation, so these p-values should not be treated as preregistered discoveries.

## A more demanding predictability test does not succeed for the adjusted model

The same three-feature classifier does not successfully predict individual home-adjusted choices out of sample: leave-one-out balanced accuracy is 44.9%, with a label-permutation p-value of 0.847. FBS-only balanced accuracy is 52.0% (p=0.186). Ridge penalty was fixed at one; no search over classifiers or penalties was performed after seeing results. These failures are reported alongside the favorable group-level contrasts. A group-level tendency need not enable reliable classification of each game.

Balanced accuracy averages the fraction of underdog choices predicted correctly and the fraction of favorite choices predicted correctly; always predicting underdog scores 50%. Exact leave-one-out ridge scores are checked against explicit refits. The fixed covariate matrix is standardized without using outcomes, then each held-out label is excluded from its prediction. The permutation benchmark repeats this prediction procedure, preserving the total underdog count.

## Supported interpretation

The original model clearly made structured, directionally biased choices while recording parity in this sample. The current home-adjusted model retains a plausible, measurable anti-blowout preference and also records roughly even performance. It is too strong to call all these choices identical independent fair coin flips. It is also too strong to claim a distinct equally effective optimum: observed parity is not statistical equivalence, and we have not ruled out systematic compression plus otherwise noisy deviations. A conditional random policy reflecting those biases can still be consistent with the evidence.

The distinction is between **random choices**, **a structured choice policy**, and **a structured policy with useful game-specific information**. This week supplies evidence of the middle category, strongest for the old away bias and weaker for the current compression pattern. The prior outcome analysis did not establish the third category. Future frozen weeks can test whether the same selection structure and approximately even results persist.

Files: `pick-structure.json` contains all four original/home-adjusted and all-games/FBS-only variants. Reproduce with `python analysis/pick_structure.py` from football/. Bootstrap or permutation calculations here do not create new games or new independent weeks.
