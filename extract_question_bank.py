import json

IN_PATH = "question_bank.json"
OUT_PATH = "question_bank_L1_1_only.json"
TARGET_LECTURE_ID = "L1_1"

with open(IN_PATH, "r", encoding="utf-8") as f:
    qb = json.load(f)

# 1) Keep only L1_1 lecture
lectures = qb.get("lectures", [])
keep_lectures = [lec for lec in lectures if lec.get("lecture_id") == TARGET_LECTURE_ID]
if not keep_lectures:
    raise ValueError(f"Lecture_id={TARGET_LECTURE_ID} not found in {IN_PATH}")

# 2) Collect concept tags used by those questions
used_tags = set()
for lec in keep_lectures:
    for q in lec.get("questions", []):
        used_tags.update(q.get("concept_tags", []))

# 3) Filter ontology to only those tags
ontology = qb.get("ontology", {})
filtered_ontology = {tag: ontology[tag] for tag in sorted(used_tags) if tag in ontology}

# 4) Build new question bank
new_qb = {
    "ontology": filtered_ontology,
    "lectures": keep_lectures,
    "assignments": []
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(new_qb, f, ensure_ascii=False, indent=2)

print(f"Wrote {OUT_PATH}")
print(f"Kept lecture: {TARGET_LECTURE_ID}")
print(f"Kept tags: {sorted(used_tags)}")
