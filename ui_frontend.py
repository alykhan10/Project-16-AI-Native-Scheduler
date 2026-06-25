from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request

from clinical_booking import DiagnosisRouter

app = FastAPI()
templates = Jinja2Templates(directory="templates")

router = DiagnosisRouter("diagnosis_mapping.json")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("web_app.html", {"request": request, "result": None})


@app.post("/route", response_class=HTMLResponse)
def route_text(request: Request, text: str = Form(...)):
    result = router.route(text)

    formatted = []

    if result["status"] == "BLOCKED":
        formatted = {
            "blocked": True,
            "message": result["result"]["message"],
            "matched_keywords": result["result"]["matched_keywords"]
        }
    else:
        exams = result["matched_exams"]

        for e in exams:
            formatted.append({
                "exam": e["exam_code"],
                "display_name": e["display_name"],
                "prep": e["prep"]["instructions"]
            })

    return templates.TemplateResponse(
        "web_app.html",
        {"request": request, "result": formatted}
    )