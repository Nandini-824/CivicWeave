from datetime import datetime, timezone

from app.models.incident import StatusHistory


async def record_status_change(
    db,
    entity_type: str,
    entity_id: str,
    previous_status: str | None,
    new_status: str,
    changed_by: str | None,
    remarks: str | None = None,
):
    """
    Record a complaint/incident status change
    in MongoDB.
    """

    history = StatusHistory(
        entity_type=entity_type,
        entity_id=str(entity_id),
        previous_status=previous_status,
        new_status=new_status,
        changed_by=str(changed_by) if changed_by else None,
        remarks=remarks,
        created_at=datetime.now(timezone.utc),
    )

    document = history.model_dump(
        exclude_none=True
    )

    result = await db.status_history.insert_one(
        document
    )

    document["id"] = str(result.inserted_id)

    return document