#!/usr/bin/env python3
"""
Generate a placeholder answer file that matches the expected auto-grader format.

Replace the placeholder logic inside `build_answers()` with your own agent loop
before submitting so the ``output`` fields contain your real predictions.

Reads the input questions from cse_476_final_project_test_data.json and writes
an answers JSON file where each entry contains a string under the "output" key.
"""

import json
from pathlib import Path
from typing import Any, Dict, List
import os
import time
import requests

API_KEY  = os.getenv("OPENAI_API_KEY", "cse476")
API_BASE = os.getenv("API_BASE", "http://10.4.58.53:41701/v1")
MODEL    = os.getenv("MODEL_NAME", "bens_model")


def call_model_chat_completions(prompt: str,
                                system: str = "You are a helpful assistant. Reply with only the final answer—no explanation.",
                                model: str = MODEL,
                                temperature: float = 0.0,
                                timeout: int = 60) -> dict:

    url = f"{API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 256,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        status = resp.status_code
        hdrs   = dict(resp.headers)
        if status == 200:
            data = resp.json()
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"ok": True, "text": text, "raw": data,
                    "status": status, "error": None, "headers": hdrs}
        else:
            try:
                err_text = resp.json()
            except Exception:
                err_text = resp.text
            return {"ok": False, "text": None, "raw": None,
                    "status": status, "error": str(err_text), "headers": hdrs}
    except requests.RequestException as e:
        return {"ok": False, "text": None, "raw": None,
                "status": -1, "error": str(e), "headers": {}}


def answer(question: str) -> str:
    system_instruction = "Hello system, give me the final answer to the prompt. Please only give the answer and nothing but the answer."
    given_prompt = system_instruction + "\n\nQuestion: " + question
    given_prompt = given_prompt + "\nAnswer:"
    
    result = call_model_chat_completions(given_prompt)
    text = result["text"] if result.get("ok") else ""
    
    return text.strip()


AGE_GROUPS = [
    "Rewrite this like a 5th grader.",
    "Rewrite this like a middle schooler.",
    "Rewrite this like a high school student.",
    "Rewrite this like an educated adult."
]


def rewrite_by_age(question_text: str, age_instruction: str) -> str:
    full_prompt = age_instruction + "\n\nRewrite this question clearly:\n" + question_text

    result = call_model_chat_completions(full_prompt)

    if result.get("ok"):
        return (result["text"] or "").strip()
    else:
        return question_text


def age_based_rewrites(question_text: str) -> List[str]:
    list_of_new_questions = []

    for age_instruction in AGE_GROUPS:
        new_question = rewrite_by_age(question_text, age_instruction)
        list_of_new_questions.append(new_question)

    return list_of_new_questions


def temperature_based_answer(question: str, temp_value: float) -> str:
    system_instruction = "Hello system, give me the final answer to the prompt. Please only give the answer and nothing but the answer."

    prompt = system_instruction + "\n\nQuestion: " + question + "\nAnswer:"

    result = call_model_chat_completions(
        prompt,
        system=system_instruction,
        temperature=temp_value
    )

    if result.get("ok"):
        return (result["text"] or "").strip()
    else:
        return ""


def most_common_answer(all_answers: List[str]) -> str:
    answer_counts = {}

    for one_answer in all_answers:
        cleaned = one_answer.lower().strip()
        if cleaned not in answer_counts:
            answer_counts[cleaned] = 1
        else:
            answer_counts[cleaned] += 1

    most_used_key = None
    highest_number = -1

    for cleaned in answer_counts:
        if answer_counts[cleaned] > highest_number:
            most_used_key = cleaned
            highest_number = answer_counts[cleaned]

    for one_answer in all_answers:
        if one_answer.lower().strip() == most_used_key:
            return one_answer

    return all_answers[0]

def agent_loop(question_text: str) -> str:
    rewritten_versions = age_based_rewrites(question_text)

    all_answers = []

    for one_rewritten_question in rewritten_versions:
        one_answer = temperature_based_answer(one_rewritten_question, 0.9)
        all_answers.append(one_answer)

    final_answer = most_common_answer(all_answers)
    return final_answer


INPUT_PATH = Path("cse_476_final_project_test_data.json")
OUTPUT_PATH = Path("cse_476_final_project_answers.json")


def load_questions(path: Path) -> List[Dict[str, Any]]:
    with path.open("r") as fp:
        data = json.load(fp)
    if not isinstance(data, list):
        raise ValueError("Input file must contain a list of question objects.")
    return data


def build_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    answers = []
    for idx, question in enumerate(questions, start=1):
        # Example: assume you have an agent loop that produces an answer string.
        real_answer = agent_loop(question["input"])
        answers.append({"output": real_answer})
    return answers


def validate_results(
    questions: List[Dict[str, Any]], answers: List[Dict[str, Any]]
) -> None:
    if len(questions) != len(answers):
        raise ValueError(
            f"Mismatched lengths: {len(questions)} questions vs {len(answers)} answers."
        )
    for idx, answer in enumerate(answers):
        if "output" not in answer:
            raise ValueError(f"Missing 'output' field for answer index {idx}.")
        if not isinstance(answer["output"], str):
            raise TypeError(
                f"Answer at index {idx} has non-string output: {type(answer['output'])}"
            )
        if len(answer["output"]) >= 5000:
            raise ValueError(
                f"Answer at index {idx} exceeds 5000 characters "
                f"({len(answer['output'])} chars). Please make sure your answer does not include any intermediate results."
            )


def main() -> None:
    questions = load_questions(INPUT_PATH)    
    answers = build_answers(questions)

    with OUTPUT_PATH.open("w") as fp:
        json.dump(answers, fp, ensure_ascii=False, indent=2)

    with OUTPUT_PATH.open("r") as fp:
        saved_answers = json.load(fp)
    validate_results(questions, saved_answers)
    print(
        f"Wrote {len(answers)} answers to {OUTPUT_PATH} "
        "and validated format successfully."
    )


if __name__ == "__main__":
    main()

