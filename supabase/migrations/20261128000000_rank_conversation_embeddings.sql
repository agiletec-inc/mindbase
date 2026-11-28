-- Both the HTTP API and MCP search the same provider/model corpus.
CREATE OR REPLACE FUNCTION mindbase_rank_conversation_embeddings(
    query_vector vector, selected_provider text, selected_model text,
    recency_weight double precision, tau_seconds double precision,
    boost_days integer, boost_value double precision
)
RETURNS TABLE (conversation_id uuid, semantic_score double precision,
               recency_score double precision, combined_score double precision)
LANGUAGE sql STABLE SECURITY INVOKER AS $$
    SELECT id, semantic, recency, semantic * (1 - recency_weight) + recency * recency_weight
    FROM (
        SELECT c.id,
            GREATEST(0, 1 - (CASE vector_dims(query_vector)
                WHEN 768 THEN e.vec_768 WHEN 1024 THEN e.vec_1024
                WHEN 3072 THEN e.vec_3072 WHEN 4096 THEN e.vec_4096 END
                              <=> query_vector)) AS semantic,
            LEAST(1.0, EXP(-EXTRACT(EPOCH FROM (NOW() - COALESCE(c.created_at, to_timestamp(0))))
                           / GREATEST(1, tau_seconds))
                  + CASE WHEN c.created_at >= NOW() - GREATEST(0, boost_days) * INTERVAL '1 day'
                         THEN LEAST(1.0, GREATEST(0.0, boost_value)) ELSE 0 END) AS recency
        FROM conversation_embeddings e
        JOIN conversations c ON c.id = e.conversation_id
        WHERE e.provider = selected_provider AND e.model = selected_model
          AND e.dim = vector_dims(query_vector)
    ) scores
$$;
