from __future__ import annotations

from app.database import get_connection
from app.logger import logger
from app.schemas import TicketRecord


INSERT_TICKET_SQL = """
INSERT INTO tickets (
    client_id,
    channel,
    text,
    category,
    confidence,
    escalate,
    draft_reply,
    error
) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
"""


def save_ticket(record: TicketRecord) -> int:
    with get_connection() as conn:
        cursor = conn.execute(
            INSERT_TICKET_SQL,
            (
                record.client_id,
                record.channel,
                record.text,
                record.category,
                record.confidence,
                int(record.escalate),
                record.draft_reply,
                record.error,
            ),
        )
        ticket_id = int(cursor.lastrowid)
    logger.info(
        "Ticket saved: id=%s client_id=%s category=%s confidence=%s escalate=%s error=%s",
        ticket_id,
        record.client_id,
        record.category,
        record.confidence,
        record.escalate,
        bool(record.error),
    )
    return ticket_id
