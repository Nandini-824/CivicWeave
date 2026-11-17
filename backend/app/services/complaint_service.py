from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId

from app.models.complaint import (
    Complaint,
    ComplaintAnalysis,
    ComplaintStatus,
)
from app.models.incident import (
    Incident,
    IncidentComplaint,
    LinkStatus,
    IncidentStatus,
    PriorityAssessment,
)

from app.ai.classifier import classify_complaint
from app.ai.embeddings import (
    generate_embedding,
    embedding_to_json,
    embedding_from_json,
)
from app.ai.incident_linker import evaluate_complaint_match
from app.ai.priority_engine import estimate_priority

from app.services.status_service import record_status_change
from app.config import get_settings


settings = get_settings()


def _object_id(value: str | ObjectId | None):
    """
    Convert a string/ObjectId into MongoDB ObjectId.
    """
    if value is None:
        return None

    if isinstance(value, ObjectId):
        return value

    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


async def get_department_by_name(db, name: str):
    """
    Find a department by name.
    """
    return await db.departments.find_one({
        "name": name
    })


async def analyze_complaint_preview(
    db,
    title: str,
    description: str,
    latitude: float,
    longitude: float,
    category: str | None = None,
):
    """
    Analyze a complaint before submission.

    Performs:
    - category classification
    - department recommendation
    - embedding generation
    - semantic/spatial/temporal incident matching
    """

    classification = classify_complaint(
        title,
        description,
    )

    if category:
        classification["category"] = category

    department = await get_department_by_name(
        db,
        classification["department"],
    )
    text = f"{title}. {description}"
    embedding = await generate_embedding(text)

    related_incidents = []

    incidents_cursor = db.incidents.find({
        "category": classification["category"]
    })

    incidents = await incidents_cursor.to_list(
        length=500
    )

    for incident in incidents:

        incident_id = incident["_id"]

        links = await db.incident_complaints.find({
            "incident_id": incident_id
        }).to_list(length=500)

        best_match = None

        for link in links:

            complaint_id = link.get("complaint_id")

            complaint = await db.complaints.find_one({
                "_id": complaint_id
            })

            if not complaint:
                continue

            analysis = await db.complaint_analysis.find_one({
                "complaint_id": str(complaint_id)
            })

            if not analysis:
                continue

            embedding_reference = analysis.get(
                "embedding_reference"
            )

            if not embedding_reference:
                continue

            try:
                existing_embedding = embedding_from_json(
                    embedding_reference
                )
            except Exception:
                continue

            created_at = complaint.get("created_at")

            if not created_at:
                continue

            match = evaluate_complaint_match(
                embedding,
                existing_embedding,

                latitude,
                longitude,
                datetime.now(timezone.utc),

                complaint.get("latitude"),
                complaint.get("longitude"),
                created_at,

                classification["category"],
            )

            if match["recommendation"] == "possible_match":

                if (
                    best_match is None
                    or match["combined_score"]
                    > best_match["combined_score"]
                ):
                    best_match = match

        if best_match:

            complaint_count = len(links)

            related_incidents.append({
                "incident_id": str(incident["_id"]),
                "incident_number": incident["incident_number"],
                "title": incident["title"],

                "distance_meters": best_match[
                    "distance_meters"
                ],

                "related_complaint_count": complaint_count,

                "status": incident["status"],

                "semantic_score": best_match[
                    "semantic_score"
                ],

                "spatial_score": best_match[
                    "spatial_score"
                ],

                "temporal_score": best_match[
                    "temporal_score"
                ],

                "combined_score": best_match[
                    "combined_score"
                ],

                "similarity_explanation": (
                    f"Text similarity: "
                    f"{best_match['semantic_score']:.0%}, "

                    f"Location proximity: "
                    f"{best_match['spatial_score']:.0%} "
                    f"({best_match['distance_meters']:.0f}m away), "

                    f"Time relevance: "
                    f"{best_match['temporal_score']:.0%}"
                ),
            })

    related_incidents.sort(
        key=lambda x: x["combined_score"],
        reverse=True,
    )

    return {
        "classification": classification,

        "suggested_department": classification[
            "department"
        ],

        "suggested_department_id": (
            str(department["_id"])
            if department
            else None
        ),

        "potential_related_incidents": len(
            related_incidents
        ),

        "related_incidents": related_incidents[:3],

        "analysis_status": "Completed",
    }


async def create_complaint(
    db,
    citizen_id: str,
    title: str,
    description: str,
    category: str | None,
    latitude: float,
    longitude: float,
    address: str,
    city: str,
    image_url: str | None,
    link_to_incident_id: str | None,
    submit_separately: bool,
):
    """
    Create a complaint and perform AI analysis.

    MongoDB workflow:

    Complaint
        ↓
    AI classification
        ↓
    Embedding
        ↓
    Incident linking
        ↓
    Priority recalculation
        ↓
    Status history
    """

    classification = classify_complaint(
        title,
        description,
    )

    if category:
        classification["category"] = category

    department = await get_department_by_name(
        db,
        classification["department"],
    )

    # ------------------------------------------------
    # Generate complaint number
    # ------------------------------------------------
    # Temporary MongoDB-safe number.
    # We can move this into number_generator.py later.
    timestamp = datetime.now(timezone.utc)

    complaint_number = (
        f"CW-{timestamp.strftime('%Y%m%d%H%M%S%f')[-12:]}"
    )

    # ------------------------------------------------
    # Create complaint document
    # ------------------------------------------------

    complaint = Complaint(
        complaint_number=complaint_number,

        citizen_id=str(citizen_id),

        title=title,
        description=description,

        category=classification["category"],

        suggested_department_id=(
            str(department["_id"])
            if department
            else None
        ),

        assigned_department_id=(
            str(department["_id"])
            if department
            else None
        ),

        latitude=latitude,
        longitude=longitude,

        address=address,
        city=city,

        image_url=image_url,

        status=ComplaintStatus.submitted.value,

        citizen_link_choice=(
            "linked"
            if link_to_incident_id
            else (
                "separate"
                if submit_separately
                else "new"
            )
        ),
    )

    complaint_document = complaint.model_dump(
        exclude_none=True
    )

    # Store GeoJSON for future 2dsphere queries
    complaint_document["location"] = {
        "type": "Point",
        "coordinates": [
            longitude,
            latitude,
        ],
    }

    result = await db.complaints.insert_one(
        complaint_document
    )

    complaint_id = result.inserted_id

    # ------------------------------------------------
    # AI embedding
    # ------------------------------------------------
    text = f"{title}. {description}"
    embedding = await generate_embedding(text)

    analysis = ComplaintAnalysis(
        complaint_id=str(complaint_id),

        predicted_category=classification[
            "category"
        ],

        prediction_method=classification[
            "method"
        ],

        classification_confidence=classification[
            "confidence"
        ],

        embedding_reference=embedding_to_json(
            embedding
        ),
    )

    await db.complaint_analysis.insert_one(
        analysis.model_dump(
            exclude_none=True
        )
    )

    # ------------------------------------------------
    # Status history
    # ------------------------------------------------

    await record_status_change(
        db=db,
        entity_type="complaint",
        entity_id=str(complaint_id),
        previous_status=None,
        new_status=ComplaintStatus.submitted.value,
        changed_by=str(citizen_id),
        remarks="Complaint submitted",
    )

    await record_status_change(
        db=db,
        entity_type="complaint",
        entity_id=str(complaint_id),
        previous_status=ComplaintStatus.submitted.value,
        new_status="AI Analysis Completed",
        changed_by=str(citizen_id),
        remarks="AI analysis completed",
    )

    # ------------------------------------------------
    # Link complaint to existing incident
    # ------------------------------------------------

    if link_to_incident_id and not submit_separately:

        incident_object_id = _object_id(
            link_to_incident_id
        )

        incident = None

        if incident_object_id:
            incident = await db.incidents.find_one({
                "_id": incident_object_id
            })

        if incident:

            links = await db.incident_complaints.find({
                "incident_id": incident["_id"]
            }).to_list(length=500)

            reference_complaint = None

            for link in links:

                reference_id = link.get(
                    "complaint_id"
                )

                reference_complaint = (
                    await db.complaints.find_one({
                        "_id": reference_id
                    })
                )

                if not reference_complaint:
                    continue

                reference_analysis = (
                await db.complaint_analysis.find_one({
                    "complaint_id": str(reference_id)
                })
                 
                )
                if (
                    reference_analysis
                    and reference_analysis.get(
                        "embedding_reference"
                    )
                ):
                    break

                reference_complaint = None

            match = {
                "semantic_score": 0,
                "spatial_score": 0,
                "temporal_score": 0,
                "combined_score": 0,
            }

            if reference_complaint:

                reference_analysis = (
                    await db.complaint_analysis.find_one({
                        "complaint_id":
                            reference_complaint["_id"]
                    })
                )

                existing_embedding = (
                    embedding_from_json(
                        reference_analysis[
                            "embedding_reference"
                        ]
                    )
                )

                match = evaluate_complaint_match(
                    embedding,
                    existing_embedding,

                    latitude,
                    longitude,
                    datetime.now(timezone.utc),

                    reference_complaint[
                        "latitude"
                    ],

                    reference_complaint[
                        "longitude"
                    ],

                    reference_complaint[
                        "created_at"
                    ],

                    classification["category"],
                )

            link = IncidentComplaint(
                incident_id=str(
                    incident["_id"]
                ),

                complaint_id=str(
                    complaint_id
                ),

                semantic_score=match[
                    "semantic_score"
                ],

                spatial_score=match[
                    "spatial_score"
                ],

                temporal_score=match[
                    "temporal_score"
                ],

                combined_score=match[
                    "combined_score"
                ],

                link_status=(
                    LinkStatus.citizen_linked.value
                ),
            )

            link_document = link.model_dump(
                exclude_none=True
            )

            link_document["incident_id"] = (
                incident["_id"]
            )

            link_document["complaint_id"] = (
                complaint_id
            )

            await db.incident_complaints.insert_one(
                link_document
            )

            await db.incidents.update_one(
                {"_id": incident["_id"]},
                {
                    "$set": {
                        "last_reported_at":
                            datetime.now(
                                timezone.utc
                            ),
                        "updated_at":
                            datetime.now(
                                timezone.utc
                            ),
                    }
                },
            )

            await _recalculate_incident_priority(
                db,
                incident["_id"],
            )

    # ------------------------------------------------
    # Create a new incident
    # ------------------------------------------------

    else:

        incident_number = (
            f"CW-INC-{timestamp.strftime('%Y%m%d%H%M%S%f')[-10:]}"
        )

        now = datetime.now(timezone.utc)

        incident = Incident(
            incident_number=incident_number,

            title=title,
            description=description,

            category=classification[
                "category"
            ],

            department_id=(
                str(department["_id"])
                if department
                else None
            ),

            center_latitude=latitude,
            center_longitude=longitude,

            first_reported_at=now,
            last_reported_at=now,

            status=IncidentStatus.under_review.value,
        )

        incident_document = incident.model_dump(
            exclude_none=True
        )

        incident_document["location"] = {
            "type": "Point",
            "coordinates": [
                longitude,
                latitude,
            ],
        }

        incident_result = (
            await db.incidents.insert_one(
                incident_document
            )
        )

        incident_id = incident_result.inserted_id

        # New incident starts with its complaint
        link = IncidentComplaint(
            incident_id=str(incident_id),
            complaint_id=str(complaint_id),

            semantic_score=1.0,
            spatial_score=1.0,
            temporal_score=1.0,
            combined_score=1.0,

            link_status=LinkStatus.confirmed.value,
        )

        link_document = link.model_dump(
            exclude_none=True
        )

        link_document["incident_id"] = incident_id
        link_document["complaint_id"] = complaint_id

        await db.incident_complaints.insert_one(
            link_document
        )

        await _recalculate_incident_priority(
            db,
            incident_id,
        )

    # ------------------------------------------------
    # Return complaint
    # ------------------------------------------------

    saved_complaint = await db.complaints.find_one({
        "_id": complaint_id
    })

    saved_complaint["id"] = str(
        saved_complaint["_id"]
    )

    saved_complaint.pop("_id", None)

    return Complaint.model_validate(
        saved_complaint
    )


async def _recalculate_incident_priority(
    db,
    incident_id,
):
    """
    Recalculate explainable incident priority.
    """

    links = await db.incident_complaints.find({
        "incident_id": incident_id,

        "link_status": {
            "$in": [
                "confirmed",
                "citizen_linked",
                "pending",
            ]
        },
    }).to_list(length=1000)

    complaint_ids = [
        link["complaint_id"]
        for link in links
    ]

    complaints = []

    if complaint_ids:

        complaints = await db.complaints.find({
            "_id": {
                "$in": complaint_ids
            }
        }).to_list(length=1000)

    unique_reporters = len(
        set(
            str(c["citizen_id"])
            for c in complaints
        )
    )

    support_count = await db.incident_supports.count_documents({
        "incident_id": incident_id
    })

    incident = await db.incidents.find_one({
        "_id": incident_id
    })

    if not incident:
        return

    now = datetime.now(timezone.utc)

    first = incident["first_reported_at"]

    if first.tzinfo is None:
        first = first.replace(
            tzinfo=timezone.utc
        )

    unresolved_days = max(
        0,
        (now - first).days,
    )

    descriptions = [
        c["description"]
        for c in complaints
    ]

    result = estimate_priority(
        related_complaints=len(complaints),

        unique_reporters=unique_reporters,

        support_count=support_count,

        unresolved_days=unresolved_days,

        category=incident["category"],

        descriptions=descriptions,
    )

    await db.incidents.update_one(
        {"_id": incident_id},
        {
            "$set": {
                "recommended_priority":
                    result["recommended_priority"],

                "updated_at":
                    datetime.now(timezone.utc),
            }
        },
    )

    # Preserve human-approved priority.
    if not incident.get("approved_priority"):

        await db.incidents.update_one(
            {"_id": incident_id},
            {
                "$set": {
                    "approved_priority":
                        result["recommended_priority"]
                }
            },
        )

    assessment = PriorityAssessment(
        incident_id=str(incident_id),

        recommended_priority=result[
            "recommended_priority"
        ],

        factor_scores=result[
            "factor_scores"
        ],

        explanation=result[
            "explanation"
        ],

        model_version=result[
            "model_version"
        ],
    )

    assessment_document = assessment.model_dump(
        exclude_none=True
    )

    assessment_document["incident_id"] = (
        incident_id
    )

    await db.priority_assessments.insert_one(
        assessment_document
    )