-- SAP Performance Analysis Query
-- This is a complex multi-line SQL query for analyzing SAP system performance
-- Much cleaner to keep in a separate file than inline in YAML

SELECT 
    s.session_id,
    s.user_name,
    s.client_id,
    s.program_name,
    s.transaction_code,
    s.start_time,
    s.cpu_time,
    s.memory_usage,
    CASE 
        WHEN s.cpu_time > 30000 THEN 'HIGH'
        WHEN s.cpu_time > 10000 THEN 'MEDIUM'
        ELSE 'LOW'
    END as performance_impact,
    COUNT(*) OVER (PARTITION BY s.user_name) as user_session_count
FROM sap_sessions s
WHERE s.start_time >= CURRENT_TIMESTAMP - INTERVAL '1' HOUR
    AND s.status = 'ACTIVE'
    AND (s.cpu_time > {{.cpu_threshold}} OR s.memory_usage > {{.memory_threshold}})
ORDER BY s.cpu_time DESC, s.memory_usage DESC
LIMIT {{.limit}};

-- Additional analysis for blocking sessions
SELECT 
    blocker.session_id as blocking_session,
    blocker.user_name as blocking_user,
    blocked.session_id as blocked_session,
    blocked.user_name as blocked_user,
    blocked.wait_time,
    blocked.lock_object
FROM sap_sessions blocker
JOIN sap_lock_waits lw ON blocker.session_id = lw.blocking_session
JOIN sap_sessions blocked ON lw.waiting_session = blocked.session_id
WHERE blocked.wait_time > {{.wait_threshold}}
ORDER BY blocked.wait_time DESC;
