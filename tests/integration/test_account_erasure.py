"""Account erasure completeness for messaging data.

``erase_user_account`` (driven here through ``POST /user/me/delete-account``)
must hard-delete the erased user's inbox, anonymise messages they sent, drop
their receipts, and leave everyone else's data intact — without FK violations
from ``messages``' five user FKs or threaded replies.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from pindb.database.message import (
    Message,
    MessageCategory,
    MessageReceipt,
)
from pindb.database.user import User
from pindb.models.message_body import TextBody
from tests.fixtures.users import SUBJECT_USER_PARAMS


@pytest.mark.integration
class TestErasureWithMessages:
    @pytest.mark.parametrize("subject_user", SUBJECT_USER_PARAMS, indirect=True)
    def test_delete_account_erases_inbox_and_anonymises_sent(
        self,
        auth_client_as_subject,
        db_session,
        subject_user,
        admin_user,
    ):
        user_id: int = subject_user.id
        username: str = subject_user.username

        received = Message(
            category=MessageCategory.direct,
            body=TextBody(text="to the subject"),
            sender_id=admin_user.id,
            recipient_id=user_id,
        )
        sent = Message(
            category=MessageCategory.direct,
            body=TextBody(text="from the subject"),
            sender_id=user_id,
            recipient_id=admin_user.id,
        )
        broadcast = Message(
            category=MessageCategory.announcement,
            body=TextBody(text="site-wide"),
        )
        db_session.add_all([received, sent, broadcast])
        db_session.flush()

        reply = Message(
            category=MessageCategory.direct,
            body=TextBody(text="threaded reply to the inbox row"),
            sender_id=user_id,
            recipient_id=admin_user.id,
            parent_id=received.id,
        )
        # Subject's receipt on the broadcast, and the *admin's* receipt on the
        # subject's inbox row (must cascade when that row is deleted).
        subject_receipt = MessageReceipt(
            message_id=broadcast.id,
            user_id=user_id,
        )
        admin_receipt = MessageReceipt(
            message_id=received.id,
            user_id=admin_user.id,
        )
        db_session.add_all([reply, subject_receipt, admin_receipt])
        db_session.commit()

        received_id: int = received.id
        sent_id: int = sent.id
        broadcast_id: int = broadcast.id
        reply_id: int = reply.id

        response = auth_client_as_subject.post(
            "/user/me/delete-account",
            data={"confirm_username": username},
            follow_redirects=False,
        )
        assert response.status_code == 303

        db_session.expire_all()

        # User gone.
        assert db_session.get(User, user_id) is None

        # Inbox row hard-deleted; everything else survives.
        assert db_session.get(Message, received_id) is None
        surviving_sent = db_session.get(Message, sent_id)
        assert surviving_sent is not None
        assert surviving_sent.sender_id is None
        assert db_session.get(Message, broadcast_id) is not None

        # Threaded reply orphaned (parent SET NULL) and anonymised, not deleted.
        surviving_reply = db_session.get(Message, reply_id)
        assert surviving_reply is not None
        assert surviving_reply.parent_id is None
        assert surviving_reply.sender_id is None

        # No receipt row references either the erased user or the deleted
        # inbox message.
        remaining_receipts = db_session.scalars(select(MessageReceipt)).all()
        assert all(receipt.user_id != user_id for receipt in remaining_receipts)
        assert all(receipt.message_id != received_id for receipt in remaining_receipts)
