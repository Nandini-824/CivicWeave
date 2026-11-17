from datetime import datetime, timezone

from app.models.notification import Notification


async def create_notification(
    db,
    user_id: str,
    title: str,
    message: str,
):
    """
    Create a notification for a CivicWeave user.
    """

    notification = Notification(
        user_id=str(user_id),
        title=title,
        message=message,
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )

    document = notification.model_dump(
        exclude_none=True
    )

    result = await db.notifications.insert_one(
        document
    )

    document["id"] = str(result.inserted_id)

    return document