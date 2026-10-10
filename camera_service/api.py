"""Eigene HTTP-API für Erreichbarkeit und simulierten Kamerastatus."""

import logging
import json
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from camera_service.camera_tools import evaluate_temperature, get_camera_status
from camera_service.document_chat import build_document_context, generate_context_answer, select_context_chunks
from camera_service.semantic_search import retrieve_sections
from camera_service.plan_validation import validate_plan
from camera_service.service_plan import JSON_QUESTION, prepare_plan_context
from camera_service.axis_service import generate_axis_service_advice


app = FastAPI(title="Camera Service Assistant")
logger = logging.getLogger(__name__)


class DocumentSearchRequest(BaseModel):
    """Die JSON-Anfrage muss eine nichtleere Frage enthalten."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    question: str = Field(min_length=1, max_length=1000)


class AxisServiceRequest(BaseModel):
    """Nur einen unserer drei definierten Testfälle zulassen."""

    model_config = ConfigDict(extra="forbid")
    scenario: Literal["unreachable", "access_denied", "no_video"]


@app.get("/health")
def health() -> dict[str, str]:
    """Nur die Erreichbarkeit dieser Anwendung melden."""
    return {"status": "ok"}


@app.post("/axis/service")
def axis_service(request: AxisServiceRequest) -> dict:
    """Simulierten Axis-Fall und einen noch manuell zu prüfenden Textvorschlag liefern."""
    try:
        result = generate_axis_service_advice(request.scenario)
    except OSError as error:
        logger.exception("Axis-Beispieldateien konnten nicht gelesen werden.")
        raise HTTPException(
            status_code=500, detail="Axis-Beispieldateien nicht lesbar. Prüfe die Server-Logs."
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        **result,
        "notice": (
            "Simulierte Geräteantworten und Benutzerangaben, kein Live-Nachweis. "
            "sources nennt mitgesendete Abschnitte. Freier Text ohne Planformatprüfung; "
            "Aussagen, Quellenbelege und offene Prüfungen müssen manuell geprüft werden."
        ),
    }


@app.get("/cameras/{camera_id}/status")
def camera_status(camera_id: str) -> dict:
    """Simulation aus der Datei lesen und die interne Temperatur mit Python prüfen."""
    camera_id = camera_id.upper()
    if camera_id != "CAM-03":
        raise HTTPException(status_code=404, detail=f"Unbekannte Kamera-ID: {camera_id}")
    try:
        status = get_camera_status(camera_id)
        temperature_check = evaluate_temperature(status)
    except (OSError, UnicodeError, ValueError) as error:
        logger.exception("Simulierte Statusdaten für %s konnten nicht verarbeitet werden.", camera_id)
        raise HTTPException(
            status_code=500,
            detail="Simulierte Statusdaten konnten nicht gelesen oder geprüft werden. Prüfe die Server-Logs.",
        ) from error
    return {"status": status, "temperature_check": temperature_check}


@app.post("/documents/search")
def document_search(request: DocumentSearchRequest) -> dict:
    """Abschnitte über Nomic suchen; noch keine Textantwort von Gemma erzeugen."""
    result = retrieve_sections(request.question)
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Dokumentensuche aktuell nicht verfügbar. Prüfe Dokumente, LM Studio und Server-Logs.",
        )
    chunks, ranked = result
    return {
        "question": request.question,
        "matches": [
            {"similarity": score, "source": chunk["source"],
             "section": chunk["section"], "text": chunk["text"]}
            for score, chunk in ranked[:3]
        ],
        "notice": "Ähnlichkeit ist keine Wahrscheinlichkeit; Fundstellen müssen die Frage nicht beantworten.",
    }


@app.post("/documents/answer")
def document_answer(request: DocumentSearchRequest) -> dict:
    """Nomic-Fundstellen als Kontext senden und Gemmas Text über HTTP zurückgeben."""
    result = retrieve_sections(request.question)
    if result is None:
        raise HTTPException(status_code=503, detail="Dokumentensuche aktuell nicht verfügbar. Prüfe die Server-Logs.")
    chunks, ranked = result
    matches = [chunk for score, chunk in ranked[:3]]
    context = build_document_context(chunks, matches)
    if not context.strip():
        raise HTTPException(status_code=503, detail="Kein Dokumentkontext verfügbar; Gemma wurde nicht aufgerufen.")
    try:
        answer = generate_context_answer(request.question, context)
    except ValueError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "question": request.question,
        **answer,
        "sources": [{"source": chunk["source"], "section": chunk["section"]}
                    for chunk in select_context_chunks(chunks, matches)],
        "notice": "sources nennt die mitgelieferten Abschnitte; die Aussagen und Quellen in Gemmas Antwort müssen geprüft werden.",
    }


@app.post("/cameras/{camera_id}/plan")
def camera_plan(camera_id: str) -> dict:
    """Geprüftes Planformat für das feste Szenario CAM-03 mit unscharfem Bild liefern."""
    evidence = camera_status(camera_id)
    result = retrieve_sections("CAM-03 unscharfes Bild Sichtscheibe Sichtprüfung")
    if result is None:
        raise HTTPException(status_code=503, detail="Dokumentensuche aktuell nicht verfügbar. Prüfe die Server-Logs.")
    try:
        context, selected = prepare_plan_context(*result, structured=True)
    except ValueError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    allowed_sources = {(chunk["source"], chunk["section"]) for chunk in selected}
    try:
        answer = generate_context_answer(JSON_QUESTION, context, evidence=evidence, structured=True)
        if answer["finish_reason"] != "stop":
            raise ValueError(f"Kein Plan freigegeben: Antwort nicht regulär beendet ({answer['finish_reason']}).")
        plan = validate_plan(json.loads(answer["answer"]), allowed_sources)
    except ValueError as error:
        raise HTTPException(status_code=502, detail=f"Plan konnte nicht übernommen werden: {error}") from error
    return {
        "scenario": "CAM-03, unscharfes Bild; keine Sichtprüfung durchgeführt.",
        **evidence,
        "plan": plan,
        "sources": [{"source": chunk["source"], "section": chunk["section"]} for chunk in selected],
        "notice": "Planformat und Quellenpaare geprüft; Inhalt weiterhin zu prüfen. Alle Schritte sind noch durchzuführen. Statusdaten sind Simulation und kein Live-Nachweis.",
    }
