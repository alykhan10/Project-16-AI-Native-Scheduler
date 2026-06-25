import json
import re
from typing import Dict, List, Any

# ----------------------------
# Text Normalization Layer
# ----------------------------
def normalize_text(text: str) -> str:
    text = text.lower()

    # basic cleanup
    text = re.sub(r"[^\w\s\?\/]", " ", text)

    # normalize common clinical shorthand
    replacements = {
        "r/o": "rule out",
        "ro": "rule out",
        "?": "suspected",
        "suspect": "suspected"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = re.sub(r"\s+", " ", text).strip()
    return text


# ----------------------------
# Keyword Matching
# ----------------------------
def find_matches(text: str, keywords: List[str]) -> List[str]:
    matches = []
    for kw in keywords:
        kw_norm = kw.lower()
        if re.search(rf"\b{re.escape(kw_norm)}\b", text):
            matches.append(kw)
    return matches


# ----------------------------
# Main Routing Engine
# ----------------------------
class DiagnosisRouter:
    def __init__(self, json_path: str):
        with open(json_path, "r") as f:
            self.ruleset = json.load(f)

        self.categories = self.ruleset["categories"]

        # separate DONOTBOOK for priority override
        self.donotbook = next(
            (c for c in self.categories if c["exam_code"] == "DONOTBOOK"),
            None
        )

        self.exams = [
            c for c in self.categories if c["exam_code"] != "DONOTBOOK"
        ]

    # ----------------------------
    # Hard Stop Check
    # ----------------------------
    def check_donotbook(self, text: str) -> Dict:
        if not self.donotbook:
            return {"triggered": False}

        routing = self.donotbook["routing"]

        # FIXED: merge keywords into single list (no separate alias pass)
        keywords = (
            routing.get("include_keywords", []) +
            routing.get("aliases", [])
        )

        matches = find_matches(text, keywords)

        if matches:
            return {
                "triggered": True,
                "exam_code": "DONOTBOOK",
                "message": self.donotbook["message_to_user"],
                "matched_keywords": matches
            }

        return {"triggered": False}

    # ----------------------------
    # Multi-Label Routing
    # ----------------------------
    def route(self, raw_text: str) -> Dict:
        text = normalize_text(raw_text)

        # Step 1: safety gate
        donotbook_result = self.check_donotbook(text)
        if donotbook_result["triggered"]:
            return {
                "status": "BLOCKED",
                "result": donotbook_result
            }

        results = []

        # Step 2: evaluate all categories
        for cat in self.exams:
            routing = cat["routing"]

            # FIXED: merge include + strong + aliases into single list
            keywords = (
                routing.get("include_keywords", []) +
                routing.get("aliases", [])
            )

            all_hits = find_matches(text, keywords)

            # FIXED: deduplicate matches
            all_hits = list(set(all_hits))

            if all_hits:
                results.append({
                    "exam_code": cat["exam_code"],
                    "display_name": cat["display_name"],
                    "matched_keywords": all_hits,
                    "prep": cat["prep"]
                })

        # Step 3: output
        return {
            "status": "OK",
            "matched_exams": results
        }


# ----------------------------
# Example Usage
# ----------------------------
if __name__ == "__main__":
    router = DiagnosisRouter("diagnosis_mapping.json")

    tests = [
        "fibroids and ovarian cyst",
        "rule out appendicitis",
        "RUQ pain gallstones",
        "scrotal pain and swelling",
        "neck lump and breast mass",
        "lower abdominal pain"
    ]

    for t in tests:
        print("\nINPUT:", t)
        print(json.dumps(router.route(t), indent=2))