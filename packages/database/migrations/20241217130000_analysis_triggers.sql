-- Analysis Triggers: Automatic pipeline for conversation analysis
-- Triggers database events to automatically queue and process analysis jobs

-- ===================================
-- 1. AUTO-ANALYSIS TRIGGER FUNCTIONS
-- ===================================

-- Function to automatically queue analysis jobs when conversations are inserted
CREATE OR REPLACE FUNCTION queue_conversation_analysis()
RETURNS TRIGGER AS $$
BEGIN
    -- Queue full analysis for new conversations
    INSERT INTO conversation_analysis_jobs (
        conversation_id,
        job_type,
        status
    ) VALUES (
        NEW.id,
        'full_analysis',
        'pending'
    );
    
    -- Log the queued job
    RAISE NOTICE 'Queued analysis job for conversation: %', NEW.id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to conversations table
CREATE TRIGGER trigger_queue_analysis
    AFTER INSERT ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION queue_conversation_analysis();

-- ===================================
-- 2. PATTERN NOTIFICATION TRIGGERS
-- ===================================

-- Function to notify when new patterns are extracted
CREATE OR REPLACE FUNCTION notify_pattern_extraction()
RETURNS TRIGGER AS $$
DECLARE
    pattern_count INTEGER;
    book_sections_count INTEGER;
BEGIN
    -- Count total patterns for this conversation
    SELECT COUNT(*) INTO pattern_count
    FROM thought_patterns 
    WHERE NEW.id = ANY(source_conversations);
    
    -- Check if we have book sections that might benefit from this pattern
    SELECT COUNT(*) INTO book_sections_count
    FROM book_structure 
    WHERE level > 1 -- Not root book level
        AND completion_percentage < 80 -- Not fully complete
        AND (
            title ILIKE '%' || ANY(NEW.themes) || '%' 
            OR title ILIKE '%' || ANY(NEW.keywords) || '%'
        );
    
    -- Log pattern extraction
    RAISE NOTICE 'New pattern extracted: % (type: %, confidence: %, potential sections: %)', 
        NEW.title, NEW.pattern_type, NEW.confidence_score, book_sections_count;
    
    -- If high-confidence pattern and relevant sections exist, consider book synthesis
    IF NEW.confidence_score >= 0.8 AND book_sections_count > 0 THEN
        RAISE NOTICE 'High-confidence pattern % may trigger book synthesis for % sections', 
            NEW.title, book_sections_count;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to thought_patterns table
CREATE TRIGGER trigger_notify_patterns
    AFTER INSERT ON thought_patterns
    FOR EACH ROW
    EXECUTE FUNCTION notify_pattern_extraction();

-- ===================================
-- 3. BOOK SYNTHESIS TRIGGERS
-- ===================================

-- Function to track book progress and suggest synthesis
CREATE OR REPLACE FUNCTION monitor_book_progress()
RETURNS TRIGGER AS $$
DECLARE
    chapter_completion FLOAT;
    pattern_count INTEGER;
    last_synthesis TIMESTAMP WITH TIME ZONE;
BEGIN
    -- Calculate average completion for this book
    SELECT AVG(completion_percentage) INTO chapter_completion
    FROM book_structure 
    WHERE parent_id = COALESCE(NEW.parent_id, NEW.id)
        AND level > 1; -- Skip root book level
    
    -- Count available patterns that could enhance this section
    SELECT COUNT(*) INTO pattern_count
    FROM thought_patterns
    WHERE confidence_score >= 0.7
        AND (
            NEW.title ILIKE '%' || ANY(themes) || '%'
            OR NEW.title ILIKE '%' || ANY(keywords) || '%'
        );
    
    -- Check when this section was last updated
    last_synthesis = OLD.updated_at;
    
    -- Log progress update
    RAISE NOTICE 'Book section updated: % (completion: % → %, patterns available: %)', 
        NEW.title, 
        COALESCE(OLD.completion_percentage, 0), 
        NEW.completion_percentage,
        pattern_count;
    
    -- Suggest synthesis if conditions are met
    IF pattern_count >= 3 
        AND NEW.completion_percentage < 60 
        AND (last_synthesis IS NULL OR last_synthesis < NOW() - INTERVAL '24 hours') THEN
        
        RAISE NOTICE 'Section % may benefit from synthesis (% patterns available, %% complete)', 
            NEW.title, pattern_count, NEW.completion_percentage;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to book_structure table
CREATE TRIGGER trigger_monitor_book_progress
    AFTER UPDATE OF content, completion_percentage ON book_structure
    FOR EACH ROW
    EXECUTE FUNCTION monitor_book_progress();

-- ===================================
-- 4. ANALYSIS JOB COMPLETION TRIGGERS
-- ===================================

-- Function to handle analysis job completion
CREATE OR REPLACE FUNCTION handle_analysis_completion()
RETURNS TRIGGER AS $$
DECLARE
    conversation_title TEXT;
    pattern_count INTEGER;
BEGIN
    -- Only process completed jobs
    IF NEW.status != 'completed' OR OLD.status = 'completed' THEN
        RETURN NEW;
    END IF;
    
    -- Get conversation title
    SELECT title INTO conversation_title
    FROM conversations 
    WHERE id = NEW.conversation_id;
    
    -- Count patterns extracted for this conversation
    SELECT COUNT(*) INTO pattern_count
    FROM thought_patterns 
    WHERE NEW.conversation_id = ANY(source_conversations);
    
    -- Log completion
    RAISE NOTICE 'Analysis completed for "%" (type: %, patterns found: %)', 
        conversation_title, NEW.job_type, pattern_count;
    
    -- If this was a full analysis with good pattern extraction, log success
    IF NEW.job_type = 'full_analysis' AND pattern_count > 0 THEN
        RAISE NOTICE 'Successful full analysis: % patterns extracted from "%"', 
            pattern_count, conversation_title;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to conversation_analysis_jobs table
CREATE TRIGGER trigger_handle_analysis_completion
    AFTER UPDATE OF status ON conversation_analysis_jobs
    FOR EACH ROW
    EXECUTE FUNCTION handle_analysis_completion();

-- ===================================
-- 5. CROSS-PATTERN ANALYSIS TRIGGERS
-- ===================================

-- Function to detect cross-conversation patterns
CREATE OR REPLACE FUNCTION detect_cross_patterns()
RETURNS TRIGGER AS $$
DECLARE
    similar_patterns INTEGER;
    pattern_group TEXT;
BEGIN
    -- Check for similar patterns across conversations
    SELECT COUNT(*) INTO similar_patterns
    FROM thought_patterns tp
    WHERE tp.id != NEW.id
        AND tp.pattern_type = NEW.pattern_type
        AND (
            tp.keywords && NEW.keywords  -- Array overlap operator
            OR tp.themes && NEW.themes
        )
        AND NOT (NEW.source_conversations && tp.source_conversations); -- Different conversations
    
    -- Create pattern group identifier
    pattern_group = NEW.pattern_type || ':' || array_to_string(NEW.keywords[1:2], ',');
    
    -- Log cross-pattern detection
    IF similar_patterns >= 2 THEN
        RAISE NOTICE 'Cross-pattern detected: % similar patterns for group "%" (confidence: %)', 
            similar_patterns, pattern_group, NEW.confidence_score;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to thought_patterns table for cross-pattern analysis
CREATE TRIGGER trigger_detect_cross_patterns
    AFTER INSERT ON thought_patterns
    FOR EACH ROW
    EXECUTE FUNCTION detect_cross_patterns();

-- ===================================
-- 6. PERFORMANCE MONITORING TRIGGERS
-- ===================================

-- Function to monitor system performance
CREATE OR REPLACE FUNCTION monitor_analysis_performance()
RETURNS TRIGGER AS $$
DECLARE
    processing_time INTERVAL;
    avg_processing_time INTERVAL;
BEGIN
    -- Calculate processing time for completed jobs
    IF NEW.status = 'completed' AND NEW.started_at IS NOT NULL THEN
        processing_time = NEW.completed_at - NEW.started_at;
        
        -- Get average processing time for this job type
        SELECT AVG(completed_at - started_at) INTO avg_processing_time
        FROM conversation_analysis_jobs
        WHERE job_type = NEW.job_type
            AND status = 'completed'
            AND started_at IS NOT NULL
            AND completed_at > NOW() - INTERVAL '7 days'; -- Last 7 days
        
        -- Log performance metrics
        RAISE NOTICE 'Job % completed in % (avg: % for %)', 
            NEW.job_type, 
            processing_time, 
            COALESCE(avg_processing_time, processing_time),
            NEW.job_type;
        
        -- Alert if processing took significantly longer than average
        IF avg_processing_time IS NOT NULL 
            AND processing_time > avg_processing_time * 2 THEN
            RAISE WARNING 'Slow processing detected: % took % (avg: %)', 
                NEW.job_type, processing_time, avg_processing_time;
        END IF;
    END IF;
    
    -- Alert on failed jobs
    IF NEW.status = 'failed' AND OLD.status != 'failed' THEN
        RAISE WARNING 'Analysis job failed: % for conversation % (error: %)', 
            NEW.job_type, NEW.conversation_id, NEW.error_message;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to conversation_analysis_jobs for performance monitoring
CREATE TRIGGER trigger_monitor_performance
    AFTER UPDATE OF status ON conversation_analysis_jobs
    FOR EACH ROW
    EXECUTE FUNCTION monitor_analysis_performance();

-- ===================================
-- 7. CLEANUP AND MAINTENANCE TRIGGERS
-- ===================================

-- Function to clean up old completed jobs
CREATE OR REPLACE FUNCTION cleanup_old_jobs()
RETURNS void AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    -- Delete completed jobs older than 30 days
    DELETE FROM conversation_analysis_jobs
    WHERE status = 'completed'
        AND completed_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    
    -- Log cleanup
    IF cleaned_count > 0 THEN
        RAISE NOTICE 'Cleaned up % old analysis jobs', cleaned_count;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ===================================
-- 8. UTILITY VIEWS FOR MONITORING
-- ===================================

-- View for analysis pipeline status
CREATE VIEW analysis_pipeline_status AS
SELECT 
    j.job_type,
    j.status,
    COUNT(*) as job_count,
    AVG(EXTRACT(EPOCH FROM (j.completed_at - j.started_at))) as avg_processing_seconds,
    MIN(j.created_at) as oldest_pending,
    MAX(j.completed_at) as latest_completion
FROM conversation_analysis_jobs j
WHERE j.created_at > NOW() - INTERVAL '7 days'
GROUP BY j.job_type, j.status
ORDER BY j.job_type, j.status;

-- View for pattern extraction metrics
CREATE VIEW pattern_extraction_metrics AS
SELECT 
    tp.pattern_type,
    COUNT(*) as total_patterns,
    AVG(tp.confidence_score) as avg_confidence,
    AVG(tp.business_viability_score) as avg_business_score,
    AVG(tp.technical_feasibility_score) as avg_technical_score,
    AVG(tp.innovation_score) as avg_innovation_score,
    COUNT(DISTINCT c.id) as source_conversations
FROM thought_patterns tp
JOIN conversations c ON c.id = ANY(tp.source_conversations)
WHERE tp.created_at > NOW() - INTERVAL '30 days'
GROUP BY tp.pattern_type
ORDER BY total_patterns DESC;

-- View for book synthesis opportunities
CREATE VIEW synthesis_opportunities AS
SELECT 
    bs.id,
    bs.title,
    bs.level,
    bs.completion_percentage,
    bs.target_word_count,
    bs.word_count,
    COUNT(tp.id) as available_patterns,
    AVG(tp.confidence_score) as avg_pattern_confidence,
    bs.updated_at as last_updated
FROM book_structure bs
LEFT JOIN thought_patterns tp ON (
    bs.title ILIKE '%' || ANY(tp.themes) || '%'
    OR bs.title ILIKE '%' || ANY(tp.keywords) || '%'
)
WHERE bs.level > 1 
    AND bs.completion_percentage < 80
    AND tp.confidence_score >= 0.7
GROUP BY bs.id, bs.title, bs.level, bs.completion_percentage, 
         bs.target_word_count, bs.word_count, bs.updated_at
HAVING COUNT(tp.id) >= 3
ORDER BY COUNT(tp.id) DESC, bs.completion_percentage ASC;

-- ===================================
-- COMMENTS AND DOCUMENTATION
-- ===================================

COMMENT ON FUNCTION queue_conversation_analysis() IS 'Automatically queues analysis jobs when new conversations are added';
COMMENT ON FUNCTION notify_pattern_extraction() IS 'Notifies and logs when new thought patterns are extracted';
COMMENT ON FUNCTION monitor_book_progress() IS 'Tracks book section progress and suggests synthesis opportunities';
COMMENT ON FUNCTION handle_analysis_completion() IS 'Handles analysis job completion and logging';
COMMENT ON FUNCTION detect_cross_patterns() IS 'Detects patterns that appear across multiple conversations';
COMMENT ON FUNCTION monitor_analysis_performance() IS 'Monitors and alerts on analysis performance metrics';
COMMENT ON FUNCTION cleanup_old_jobs() IS 'Cleans up old completed analysis jobs to maintain performance';

COMMENT ON VIEW analysis_pipeline_status IS 'Real-time status of the analysis pipeline';
COMMENT ON VIEW pattern_extraction_metrics IS 'Metrics and performance data for pattern extraction';
COMMENT ON VIEW synthesis_opportunities IS 'Book sections ready for content synthesis';

-- Create an index for efficient pattern matching
CREATE INDEX idx_thought_patterns_themes_keywords_gin 
ON thought_patterns USING gin((themes || keywords));

-- Create function to manually trigger synthesis suggestions
CREATE OR REPLACE FUNCTION suggest_synthesis_targets()
RETURNS TABLE (
    section_id UUID,
    section_title TEXT,
    completion_percentage FLOAT,
    pattern_count BIGINT,
    avg_confidence FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        bs.id,
        bs.title,
        bs.completion_percentage,
        COUNT(tp.id) as pattern_count,
        AVG(tp.confidence_score) as avg_confidence
    FROM book_structure bs
    LEFT JOIN thought_patterns tp ON (
        bs.title ILIKE '%' || ANY(tp.themes) || '%'
        OR bs.title ILIKE '%' || ANY(tp.keywords) || '%'
    )
    WHERE bs.level > 1 
        AND bs.completion_percentage < 80
        AND tp.confidence_score >= 0.7
    GROUP BY bs.id, bs.title, bs.completion_percentage
    HAVING COUNT(tp.id) >= 3
    ORDER BY COUNT(tp.id) DESC, bs.completion_percentage ASC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION suggest_synthesis_targets() IS 'Returns book sections that would benefit from content synthesis';