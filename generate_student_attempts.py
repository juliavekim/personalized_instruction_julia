"""
generate_student_attempts.py

Simplest possible synthetic dataset generator.

Input: question_bank.json (curriculum JSON)
Output: student_attempts.jsonl (one JSON record per student-question)

Overview:
Each student answers every question exactly once. 
Each student is assigned K "weak" concept tags.
If a question has any weak tag, student is likely to get it wrong.
Otherwise, student is likely to get it right. 
"""

# --------------
# Import modules 
# --------------
import json 
from typing import Set, Any, Dict, List 
import random 
import argparse 

# ----------------
# Helper functions
# ----------------
def load_question_bank(path: str) -> Dict[str, Any]:
    """
    Load the question bank JSON file from disk. 
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f) 

def iter_all_questions(question_bank: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Return a flat list of ALL QUESTIONS in the curriculum. 

    The question banks stores questions in a nested structure:
    - lecture -> questions
    - assignment -> parts -> questions.

    This function walks through that structure, specified above, and collects every question dictionary into 
    a single list. 
    """
    out = [] 

    # Lectures
    for lec in question_bank.get("lectures", []):
        out.extend(lec.get("questions", []))

    # Assignments
    for asg in question_bank.get("assignments", []):
        for part in asg.get("parts", []):
            out.extend(part.get("questions", []))
    
    return out 

def choose_weak_tags(all_tags: List[str], rng: random.Random, k_min: int = 1, k_max: int = 3) -> List[str]:
    """
    Pick k weak tags for a student, k is random in [k_min, k_max].
    """
    if not all_tags:
        return []
    k_low = max(0, min(k_min, len(all_tags)))
    k_high = max(0, min(k_max, len(all_tags)))
    if k_low > k_high:
        k_low = k_high 
    k = rng.randint(k_low, k_high)
    return rng.sample(all_tags, k)

def any_weak_tag(question_tags: List[str], weak_tags_set: set) -> bool:
    """
    True if this question touches any tag the student is weak at.
    """
    return any(t in weak_tags_set for t in question_tags)

def pick_answer_single_select(options: Dict[str, str], correct_options: List[str], want_correct: bool, rng: random.Random) -> List[str]:
    """
    Simulate a student's answer to a single_select MCQ.
    correct_options must be a list of exactly one key, e.g., ["B"]. 
    Returns a list like ["A"]. 
    """
    if len(correct_options) != 1:
        raise ValueError(f"single_select expects exactly 1 correct options, got {correct_options}")
        
    all_keys = list(options.keys())
    correct_option = correct_options[0]

    if want_correct:
        return [correct_option]

    wrong_keys = [k for k in all_keys if k != correct_option]
    return [rng.choice(wrong_keys)]

def decide_correct(has_weak: bool, rng: random.Random, p_wrong_if_weak: float, p_wrong_if_strong: float) -> bool:
    """
    Decide whether a student answers a question correctly.

    This function is designed to simulate realistic student behaviour, in that:
    - If a question involves a concept with which the student is weak, they are MORE LIKELY to answer incorrectly.
    - If a question is strong on a concept, they are STILL POSSIBLE (though less likely to answer incorrectly).
    """
    p_wrong = p_wrong_if_weak if has_weak else p_wrong_if_strong
    return rng.random() > p_wrong 

# ----------------
# Core generation
# ----------------
def generate_attempts(question_bank_path: str, out_path: str, num_students: int, seed: int, k_min: int,
    k_max: int, p_wrong_if_weak: float, p_wrong_if_strong: float) -> None:
    """
    Generate a JSONL file where each line is one student answering one question.

    Output record schema:
    {
        "student_id": "S000123",
        "question_id": "L1_1_Q1",
        "selected_options": ["A"],
        "is_correct": false,
        "concept_tags": ["AI_HISTORY_FOUNDING"]
    }
    """
    rng = random.Random(seed)

    qb = load_question_bank(question_bank_path)
    questions = iter_all_questions(qb)

    all_tags = sorted({tag for q in questions for tag in q.get("concept_tags", [])})

    with open(out_path, "w", encoding="utf-8") as f_out:
        for s in range(num_students):
            student_id = f"S{s:06d}"

            weak_tags = choose_weak_tags(all_tags, rng=rng, k_min=k_min, k_max=k_max)
            weak_set = set(weak_tags)

            for q in questions:
                qid = q["question_id"]
                qtags = q.get("concept_tags", [])
                has_weak = any_weak_tag(qtags, weak_set)

                is_correct = decide_correct(
                    has_weak=has_weak,
                    rng=rng,
                    p_wrong_if_weak=p_wrong_if_weak,
                    p_wrong_if_strong=p_wrong_if_strong,
                )

                qtype = q.get("question_type", "single_select")
                if qtype == "single_select":
                    selected = pick_answer_single_select(
                        options=q["options"],
                        correct_options=q["correct_options"],
                        want_correct=is_correct,
                        rng=rng,
                    )
                else:
                    raise ValueError(f"Unsupported question_type: {qtype} (question_id={qid})")

                record = {
                    "student_id": student_id,
                    "question_id": qid,
                    "selected_options": selected,
                    "is_correct": is_correct,
                    "concept_tags": qtags,
                }

                f_out.write(json.dumps(record, ensure_ascii=False) + "\n")

# -----------------
# Run from terminal
# -----------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic student attempt logs (JSONL) from a question_bank.json file.")
    parser.add_argument("--question-bank", type=str, default="question_bank_L1_1_only.json", help="Path to question_bank.json")
    parser.add_argument("--out", type=str, default="student_attempts.jsonl", help="Output path for student_attempts.jsonl")
    parser.add_argument("--num-students", default=100, type=int, help="Number of students to simulate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--k-min", type=int, default=1, help="Minimum number of weak concept tags per student")
    parser.add_argument("--k-max", type=int, default=3, help="Maximum number of weak concept tags per student")
    parser.add_argument("--p-wrong-if-weak", type=float, default=0.35, help="Probability of wrong answer if question touches a weak tag")
    parser.add_argument("--p-wrong-if-strong", type=float, default=0.10, help="Probability of wrong answer if question does NOT touch a weak tag")

    args = parser.parse_args() 

    generate_attempts(
            question_bank_path=args.question_bank,
            out_path=args.out,
            num_students=args.num_students,      # ← FIX
            seed=args.seed,
            k_min=args.k_min,
            k_max=args.k_max,
            p_wrong_if_weak=args.p_wrong_if_weak,
            p_wrong_if_strong=args.p_wrong_if_strong,
        )