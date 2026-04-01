# FratBench

Measuring social calibration failure in frontier language models. A 53-question multiple-choice benchmark drawn from informal social situations common to college students, with distractors designed to exploit overaligned model tendencies toward intervention, moralization, and authority escalation.

## Key Finding

A human panel (n=12, male, ages 19-23) scores 87.3%. Thirteen frontier models from five labs score between 7.1% and 32.5%. Persona prompting as a college-aged male produces dramatic but uneven gains.

| Model | Neutral % | Persona % |
|---|---|---|
| **Human baseline** | **87.3** | -- |
| Gemini 3.1 Pro | 29.4 | **77.3** |
| Gemini 3 Flash | 31.9 | 59.8 |
| Grok 4.1 Fast Reasoning | 26.0 | 49.8 |
| Claude Opus 4.6 | 24.5 | 49.4 |
| Grok 4 | 27.9 | 42.4 |
| Claude Sonnet 4.6 | 25.3 | 41.9 |
| Grok 4.1 Fast | **32.5** | 38.1 |
| DeepSeek V3.2 | 12.5 | 19.2 |
| GPT-5.3 Instant | 7.9 | 19.2 |
| GPT-4o | 10.6 | 17.4 |
| o3 | 7.2 | 12.1 |
| GPT-5.4 Thinking | 8.7 | 11.3 |
| DeepSeek V3.2 Reasoner | 7.1 | 11.0 |

## Findings

- Every OpenAI model scores below 25% random chance in neutral mode
- Reasoning hurts social calibration across every model pair tested
- 80-86% wrong-answer convergence between Western labs despite independent training pipelines
- Loyalty Navigation accuracy is 0% for all non-Google models
- Persona prompting functions as a diagnostic for latent social knowledge, not a source of new capability

## Repository Structure

```
FratBench/
├── README.md
├── fratbench_paper.pdf              <- Full paper
├── fratbench_public_questions.md    <- 15 of 53 questions (public subset)
└── run_fratbench.py                 <- Evaluation script for all 13 models
```

For the full 53-question benchmark, contact rwang859@uwo.ca.

## Reproducing

```bash
pip install openai anthropic google-generativeai openpyxl

export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export GOOGLE_API_KEY=...
export XAI_API_KEY=...
export DEEPSEEK_API_KEY=...

python run_fratbench.py
```

Place the benchmark xlsx in the same directory. The script validates all API connections before starting, supports resume on interruption, and outputs results to CSV.
