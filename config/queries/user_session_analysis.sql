-- User Session Analysis
-- Analyze user sessions and detect potential issues

SELECT 
    user_name,
    client_id,
    COUNT(*) as session_count,
    AVG(cpu_time) as avg_cpu_time,
    MAX(cpu_time) as max_cpu_time,
    SUM(memory_usage) as total_memory,
    STRING_AGG(DISTINCT transaction_code, ', ') as transactions
FROM sap_sessions 
WHERE start_time >= CURRENT_TIMESTAMP - INTERVAL '{{.hours}}' HOUR
    AND client_id = '{{.client}}'
GROUP BY user_name, client_id
HAVING COUNT(*) > {{.min_sessions}}
ORDER BY total_memory DESC, session_count DESC;
