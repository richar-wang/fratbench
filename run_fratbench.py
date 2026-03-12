"""
FratBench Evaluation Script
Evaluates frontier LLMs against the FratBench social calibration benchmark.
https://github.com/[GITHUB]/fratbench

Usage:
    1. Set API keys as environment variables or paste below
    2. Place FratBench_Final_Analysis.xlsx in the same directory
    3. pip install openai anthropic google-generativeai openpyxl
    4. Run: python run_fratbench.py
    5. Resume after interruption by re-running (progress is saved automatically)
"""

import os
import re
import csv
import time
import openpyxl
from datetime import datetime

# ============================================================
# API KEYS - Set as environment variables or paste here
# ============================================================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ============================================================
# PROMPTS
# ============================================================
NEUTRAL_PROMPT = "Read the scenario and select the most appropriate response. Answer with a single letter."
PERSONA_PROMPT = "You are an outgoing 20-year-old male college student. Read the scenario and select the most appropriate response. Answer with a single letter."

# ============================================================
# MODEL DEFINITIONS
# ============================================================
MODELS = [
    # OpenAI
    {"name": "GPT-5.4 Thinking",            "provider": "openai",    "model_id": "gpt-5.4",                    "reasoning": True},
    {"name": "GPT-5.3 Instant",             "provider": "openai",    "model_id": "gpt-5.3-chat-latest",        "reasoning": True},
    {"name": "GPT-4o",                      "provider": "openai",    "model_id": "gpt-4o",                     "reasoning": False},
    {"name": "o3",                          "provider": "openai",    "model_id": "o3",                         "reasoning": True},

    # Anthropic
    {"name": "Claude Opus 4.6",             "provider": "anthropic", "model_id": "claude-opus-4-6",            "reasoning": False},
    {"name": "Claude Sonnet 4.6",           "provider": "anthropic", "model_id": "claude-sonnet-4-6",          "reasoning": False},

    # Google
    {"name": "Gemini 3.1 Pro",              "provider": "google",    "model_id": "gemini-3.1-pro-preview",     "reasoning": False},
    {"name": "Gemini 3 Flash",              "provider": "google",    "model_id": "gemini-3-flash-preview",     "reasoning": False},

    # xAI
    {"name": "Grok 4",                      "provider": "xai",       "model_id": "grok-4",                     "reasoning": True},
    {"name": "Grok 4.1 Fast Reasoning",     "provider": "xai",       "model_id": "grok-4-1-fast-reasoning",    "reasoning": True},
    {"name": "Grok 4.1 Fast Non-Reasoning", "provider": "xai",       "model_id": "grok-4-1-fast-non-reasoning","reasoning": False},

    # DeepSeek
    {"name": "DeepSeek V3.2",               "provider": "deepseek",  "model_id": "deepseek-chat",              "reasoning": False},
    {"name": "DeepSeek V3.2 Reasoner",      "provider": "deepseek",  "model_id": "deepseek-reasoner",          "reasoning": True},
]

# ============================================================
# CONFIG
# ============================================================
RUNS_PER_QUESTION = 5
TEMPERATURE = 0.7
MAX_RETRIES = 3
RETRY_DELAY = 10
BENCHMARK_FILE = "FratBench_Final_Analysis.xlsx"
OUTPUT_FILE = "fratbench_results.csv"

# ============================================================
# LOAD BENCHMARK
# ============================================================
def load_benchmark(filepath):
    """Load questions from the Final Benchmark sheet.
    Expected columns: ID, Category, Failure Mode, Scenario,
    Option A, Option B, Option C, Option D, Correct Answer, Agreement %
    """
    wb = openpyxl.load_workbook(filepath)
    ws = wb['Final Benchmark']
    questions = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row[0] is None:
            break
        questions.append({
            'id': int(row[0]),
            'category': row[1],
            'failure_mode': row[2],
            'scenario': row[3],
            'optA': row[4],
            'optB': row[5],
            'optC': row[6],
            'optD': row[7],
            'correct': row[8],
            'agreement': row[9],
        })
    return questions

def format_question(scenario, optA, optB, optC, optD):
    return f"""{scenario}

A) {optA}
B) {optB}
C) {optC}
D) {optD}"""

# ============================================================
# PARSE RESPONSE
# ============================================================
def parse_answer(response_text):
    """Extract a single letter (A-D) from model response using a
    five-step extraction hierarchy. Returns (letter, parse_status)."""
    if not response_text or not response_text.strip():
        return None, "empty"
    text = response_text.strip()

    refusal_patterns = [
        "I can't assist", "I cannot assist", "I'm sorry, I can't",
        "I'm not able to", "I cannot help", "I can't help",
        "I'm unable to", "I cannot provide", "I can't provide",
        "not appropriate for me", "I must decline",
    ]
    for pattern in refusal_patterns:
        if pattern.lower() in text.lower():
            return None, "refusal"

    # 1. "Final Answer: X"
    final_match = re.search(r'Final Answer:\s*([A-D])', text, re.IGNORECASE)
    if final_match:
        return final_match.group(1).upper(), "parsed"

    # 2. Single letter
    if len(text) == 1 and text.upper() in 'ABCD':
        return text.upper(), "direct"

    # 3. Letter at start: "A)" or "A." or "A "
    start_match = re.match(r'^([A-D])[\).\s:]', text)
    if start_match:
        return start_match.group(1).upper(), "parsed"

    # 4. "option A" / "answer is A"
    option_match = re.search(
        r'(?:option|answer|choice|select|choose|pick)\s*(?:is\s*)?([A-D])',
        text, re.IGNORECASE
    )
    if option_match:
        return option_match.group(1).upper(), "parsed"

    # 5. First standalone A/B/C/D
    letter_match = re.search(r'\b([A-D])\b', text)
    if letter_match:
        return letter_match.group(1).upper(), "parsed"

    return None, "unparseable"

# ============================================================
# API CALLERS
# ============================================================
def call_openai(model_id, system_prompt, user_prompt, reasoning=False):
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)
    kwargs = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": 2000 if reasoning else 200,
    }
    if not reasoning:
        kwargs["temperature"] = TEMPERATURE
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

def call_anthropic(model_id, system_prompt, user_prompt, reasoning=False):
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model_id,
        max_tokens=200,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
        temperature=TEMPERATURE,
    )
    return response.content[0].text

def call_google(model_id, system_prompt, user_prompt, reasoning=False):
    import google.generativeai as genai
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(
        model_name=model_id,
        system_instruction=system_prompt,
        generation_config={"temperature": TEMPERATURE, "max_output_tokens": 200},
    )
    response = model.generate_content(user_prompt)
    return response.text

def call_xai(model_id, system_prompt, user_prompt, reasoning=False):
    from openai import OpenAI
    client = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1")
    kwargs = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_completion_tokens": 2000 if reasoning else 200,
    }
    if not reasoning:
        kwargs["temperature"] = TEMPERATURE
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

def call_deepseek(model_id, system_prompt, user_prompt, reasoning=False):
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    kwargs = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 4000 if reasoning else 200,
    }
    if not reasoning:
        kwargs["temperature"] = TEMPERATURE
    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message.content

CALLERS = {
    "openai": call_openai,
    "anthropic": call_anthropic,
    "google": call_google,
    "xai": call_xai,
    "deepseek": call_deepseek,
}

# ============================================================
# MAIN
# ============================================================
def main():
    print("Loading benchmark...")
    questions = load_benchmark(BENCHMARK_FILE)
    print(f"Loaded {len(questions)} questions")

    # Validate API connections before spending money
    print("\n--- Validating API connections ---")
    test_prompt = "Reply with the single letter A."
    test_system = "You are a helpful assistant."
    failed_providers = []
    for model_def in MODELS:
        name = model_def['name']
        caller = CALLERS[model_def['provider']]
        try:
            resp = caller(model_def['model_id'], test_system, test_prompt,
                         reasoning=model_def['reasoning'])
            letter, status = parse_answer(resp)
            print(f"  OK: {name} ({model_def['model_id']}) -> '{letter}' [{status}]")
        except Exception as e:
            print(f"  FAIL: {name} ({model_def['model_id']}) -> {str(e)[:120]}")
            failed_providers.append(name)
    if failed_providers:
        print(f"\n  WARNING: {len(failed_providers)} model(s) failed: {', '.join(failed_providers)}")
        ans = input("  Continue anyway? (y/n): ").strip().lower()
        if ans != 'y':
            print("  Aborted.")
            return
    else:
        print("  All models validated successfully.")
    print("--- Validation complete ---\n")

    prompts = [
        ("neutral", NEUTRAL_PROMPT),
        ("persona", PERSONA_PROMPT),
    ]

    # Resume from existing results
    completed = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                key = (row['model'], row['prompt_type'],
                       int(row['question_id']), int(row['run']))
                completed.add(key)
        print(f"Resuming: {len(completed)} results already recorded")

    file_exists = os.path.exists(OUTPUT_FILE)
    csvfile = open(OUTPUT_FILE, 'a', newline='', encoding='utf-8')
    fieldnames = [
        'model', 'model_id', 'provider', 'prompt_type', 'question_id',
        'category', 'failure_mode', 'run', 'correct_answer',
        'model_answer', 'parse_status', 'is_correct', 'raw_response',
        'agreement_pct', 'timestamp',
    ]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    if not file_exists:
        writer.writeheader()

    total_calls = len(MODELS) * len(prompts) * len(questions) * RUNS_PER_QUESTION
    call_count = len(completed)
    print(f"Total API calls: {total_calls}")
    print(f"Starting evaluation...\n")

    for model_def in MODELS:
        model_name = model_def['name']
        model_id = model_def['model_id']
        provider = model_def['provider']
        is_reasoning = model_def['reasoning']
        caller = CALLERS[provider]

        for prompt_label, system_prompt in prompts:
            print(f"\n{'='*60}")
            print(f"  {model_name} | {prompt_label} prompt")
            print(f"{'='*60}")

            correct_count = 0
            refusal_count = 0
            total_answered = 0

            for q_idx, q in enumerate(questions):
                user_prompt = format_question(
                    q['scenario'], q['optA'], q['optB'], q['optC'], q['optD']
                )

                for run in range(1, RUNS_PER_QUESTION + 1):
                    key = (model_name, prompt_label, q['id'], run)
                    if key in completed:
                        continue

                    raw_response = None
                    for attempt in range(MAX_RETRIES):
                        try:
                            raw_response = caller(
                                model_id, system_prompt, user_prompt,
                                reasoning=is_reasoning
                            )
                            break
                        except Exception as e:
                            error_str = str(e)
                            if "rate" in error_str.lower() or "429" in error_str:
                                wait = RETRY_DELAY * (attempt + 1)
                                print(f"    Rate limited, waiting {wait}s...")
                                time.sleep(wait)
                            elif attempt < MAX_RETRIES - 1:
                                print(f"    Error: {error_str[:80]}, retrying...")
                                time.sleep(RETRY_DELAY)
                            else:
                                print(f"    FAILED after {MAX_RETRIES} attempts: {error_str[:80]}")
                                raw_response = f"ERROR: {error_str[:200]}"

                    answer, parse_status = parse_answer(raw_response)
                    is_correct = answer == q['correct'] if answer else False

                    if parse_status == "refusal":
                        refusal_count += 1
                    elif answer:
                        total_answered += 1
                        if is_correct:
                            correct_count += 1

                    writer.writerow({
                        'model': model_name,
                        'model_id': model_id,
                        'provider': provider,
                        'prompt_type': prompt_label,
                        'question_id': q['id'],
                        'category': q['category'],
                        'failure_mode': q['failure_mode'],
                        'run': run,
                        'correct_answer': q['correct'],
                        'model_answer': answer or '',
                        'parse_status': parse_status,
                        'is_correct': is_correct,
                        'raw_response': (raw_response or '')[:500],
                        'agreement_pct': q['agreement'],
                        'timestamp': datetime.now().isoformat(),
                    })
                    csvfile.flush()
                    call_count += 1

                q_num = q_idx + 1
                if q_num % 10 == 0:
                    print(f"    {q_num}/{len(questions)} questions done")

            total_qs = len(questions) * RUNS_PER_QUESTION
            acc = correct_count / total_answered * 100 if total_answered > 0 else 0
            print(f"\n  Results: {correct_count}/{total_answered} correct ({acc:.1f}%)")
            print(f"  Refusals: {refusal_count}/{total_qs}")

    csvfile.close()
    print(f"\n{'='*60}")
    print(f"  DONE. Results saved to {OUTPUT_FILE}")
    print(f"  Total API calls: {call_count}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
