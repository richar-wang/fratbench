# FratBench

**Measuring Social Calibration Failure in Frontier Language Models**

FratBench is a 53-question multiple-choice benchmark targeting social calibration failure in LLMs. Questions are drawn from informal social situations common to college students, with one socially appropriate answer and three distractors designed to exploit overaligned model tendencies toward intervention, moralization, and authority escalation.

A human panel (n=12, male, ages 19–23) scores 87.3%. Thirteen frontier models from five labs score between 7.1% and 32.5% in a neutral prompting condition. Persona prompting as a college-aged male produces dramatic but uneven gains, with Gemini 3.1 Pro reaching 77.3% while GPT-5.4 Thinking remains at 11.3%.

## Results

| Model | Neutral % | Persona % |
|-------|-----------|-----------|
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
| **Human baseline** | **87.3** | — |

## Repository Contents

- `fratbench_paper.pdf` — Full paper
- `fratbench_public_questions.md` — 15 of 53 questions (publicly released subset)
- `run_fratbench.py` — Evaluation script used to run all 13 models

The full 53-question benchmark is available on request for independent verification.

## Key Findings

- Every OpenAI model scores below 25% random chance in neutral mode
- Reasoning hurts social calibration across every model pair tested
- 80–86% wrong-answer convergence between Western labs despite independent training pipelines
- Loyalty Navigation accuracy is 0% for all non-Google models
- Persona prompting functions as a diagnostic for latent social knowledge, not a source of new capability

## Running the Evaluation

```
pip install openai anthropic google-generativeai openpyxl
```

Set API keys as environment variables:

```
export OPENAI_API_KEY=...
export ANTHROPIC_API_KEY=...
export GOOGLE_API_KEY=...
export XAI_API_KEY=...
export DEEPSEEK_API_KEY=...
```

Place the benchmark xlsx in the same directory and run:

```
python run_fratbench.py
```

The script validates all API connections before starting, supports resume on interruption, and outputs results to CSV.
