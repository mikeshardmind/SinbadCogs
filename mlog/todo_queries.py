channel_message_history = """
WITH last_edits AS (
    SELECT message_id, edited_at, new_content FROM (
        SELECT *, RANK() OVER(PARTITION BY message_id ORDER BY edited_at DESC) dr FROM EDITS
    )
    WHERE dr=1
)
SELECT
    messages.message_id as mid,
    messages.author_id as aid,
    COALESCE(new_content, content) as current_content,
    COALESCE(edited_at, created_at) as edited_or_created_at,
    created_at
FROM messages LEFT OUTER JOIN last_edits ON messages.message_id=last_edits.message_id
WHERE messages.channel_id = ?
ORDER BY created_at
"""

inactivy_metrics = """
SELECT ar.author_id, ar.mc, DATETIME(ar.most_recent, "unixepoch")
FROM (
    SELECT COUNT(*) as mc, author_id, MAX(created_at) as most_recent
    FROM messages WHERE guild_id = :guild_id
    GROUP BY author_id
) as ar
WHERE ar.most_recent < COALESCE(:when, 0) OR ar.mc < COALESCE(:low, 0)
ORDER BY ar.most_recent, ar.mc
LIMIT COALESCE(:limit, -1)
"""
