from datetime import date, timedelta

from wgui import tasks
from wgui.extensions import db
from wgui.models import AuditLog, DataList, ListModel


def test_delete_expired_items_second_pass_skips_removed_rows(client, monkeypatch):
    app = client.application
    sent_messages: list[tuple[str, str]] = []

    def fake_send_email(subject: str, body: str) -> None:
        sent_messages.append((subject, body))

    monkeypatch.setattr(tasks, "send_email", fake_send_email)

    with app.app_context():
        db.session.add(ListModel(name="CategoryA", type="text"))
        db.session.commit()
        db.session.add(
            DataList(
                category="CategoryA",
                data="value",
                date=date.today() - timedelta(days=1),
            )
        )
        db.session.commit()

        tasks.delete_expired_items()

        assert DataList.query.count() == 0
        assert sent_messages == [
            (
                "Entries removed",
                "The following entries were removed:\nCategoryA: value",
            )
        ]

        sent_messages.clear()
        initial_logs = AuditLog.query.count()

        tasks.delete_expired_items()

        assert DataList.query.count() == 0
        assert sent_messages == []
        assert AuditLog.query.count() == initial_logs
