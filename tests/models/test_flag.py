from uuid import uuid4
from datetime import datetime, timezone

from app.models.flag import (
    ContentTypeEnum,
    FlagReasonCodeEnum,
    FlagStatusEnum,
    Flag,
)


def test_enum_values():
    assert ContentTypeEnum.VIDEO.value == "video"
    assert FlagReasonCodeEnum.SPAM.value == "spam"
    assert FlagStatusEnum.OPEN.value == "open"


def test_flag_model_instantiation():
    now = datetime.now(timezone.utc)
    flag = Flag(
        flagId=uuid4(),
        userId=uuid4(),
        contentType=ContentTypeEnum.VIDEO,
        contentId=uuid4(),
        reasonCode=FlagReasonCodeEnum.SPAM,
        reasonText="Unwanted content",
        createdAt=now,
        updatedAt=now,
    )

    # Basic assertions that the model has stored the data correctly
    assert flag.status == FlagStatusEnum.OPEN
    assert flag.reasonText == "Unwanted content" 