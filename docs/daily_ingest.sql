SELECT *
FROM
   ingest_hash
WHERE
   time >= NOW() - INTERVAL '24 hours'
;