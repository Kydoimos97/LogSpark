# Production Observability

LogSpark's JSON preset transforms your logging into a structured observability pipeline with guaranteed output format and automatic correlation data.

## The Observability Challenge

Production logging serves different masters than development logging:

- **Log aggregation systems** need consistent, parseable format
- **Monitoring alerts** require reliable field extraction
- **Distributed tracing** needs correlation data injection
- **Storage costs** demand efficient, compact output
- **Incident response** requires predictable, searchable logs

LogSpark's JSON preset solves these systematically.

## Structured Output Guarantees

```python
spark_logger.configure(level=logging.INFO, preset="json")

spark_logger.info("User login", extra={"user_id": 123, "ip": "192.168.1.1"})
spark_logger.error("Payment failed", extra={"order_id": "ord_123", "amount": 99.99})
```

**Output format**:
```json
{"timestamp": "2024-01-01T12:00:00.123Z", "level": "INFO", "message": "User login", "user_id": 123, "ip": "192.168.1.1"}
{"timestamp": "2024-01-01T12:00:01.456Z", "level": "ERROR", "message": "Payment failed", "order_id": "ord_123", "amount": 99.99}
```

**Guarantees**:

- **Single-line JSON**: Each log record produces exactly one line
- **Consistent schema**: Standard fields (timestamp, level, message) plus your extras
- **No formatting artifacts**: Raw JSON without ANSI codes or terminal formatting
- **Traceback compaction**: Multi-line exceptions become single-line JSON strings

## Automatic Correlation Data

When ddtrace is active, correlation fields appear automatically:

```python
# No code changes needed
spark_logger.info("Processing request", extra={"user_id": 123})
```

**Output with active trace**:
```json
{
  "timestamp": "2024-01-01T12:00:00.123Z",
  "level": "INFO", 
  "message": "Processing request",
  "user_id": 123,
  "dd_trace_id": "1234567890123456789",
  "dd_span_id": "9876543210987654321"
}
```

This enables distributed tracing without configuration changes or code modification.

## Log Aggregation Pipeline Integration

LogSpark's JSON output integrates directly with standard log processing:

**Datadog/CloudWatch/ELK Stack**:

- Structured parsing without custom regex patterns
- Automatic field extraction for filtering and alerting
- Correlation data for distributed trace linking
- Consistent timestamps in ISO format

**Example Datadog log processing rule**:
```json
{
  "source": "python",
  "service": "myapp",
  "timestamp": "@timestamp",
  "level": "@level",
  "message": "@message"
}
```

No custom parsing needed - standard JSON fields work everywhere.

## Traceback Policy for Storage Efficiency

Exception handling balances debugging information with storage costs:

```python
from logspark.Types import TracebackOptions

# Minimal storage, basic context
spark_logger.configure(preset="json", traceback=TracebackOptions.COMPACT)

# Full debugging information  
spark_logger.configure(preset="json", traceback=TracebackOptions.FULL)

# No traceback overhead
spark_logger.configure(preset="json", traceback=TracebackOptions.NONE)
```

**COMPACT format** (default):
```json
{"level": "ERROR", "message": "Processing failed", "traceback": "ValueError: Invalid input | service.py:42 in process_data"}
```

**FULL format**:
```json
{"level": "ERROR", "message": "Processing failed", "traceback": "Traceback | File service.py:42 in process_data | File utils.py:15 in validate | ValueError: Invalid input"}
```

Single-line guarantee maintained in all cases.

## Global Logger Control for Operational Safety

Third-party libraries often create logging noise that triggers false alerts:

```python
from logspark import spark_log_manager

# Suppress verbose dependencies
spark_log_manager.adopt_all()
spark_log_manager.unify(
    level=logging.WARNING,  # Suppress INFO/DEBUG from dependencies
    use_spark_handler=True  # Apply consistent JSON formatting
)
```

**Before**:
```
2024-01-01 12:00:00 INFO urllib3.connectionpool Starting new HTTPS connection
2024-01-01 12:00:00 DEBUG boto3.session Loading credentials
2024-01-01 12:00:00 INFO requests.packages.urllib3 Starting new connection
```

**After**:
```json
{"timestamp": "2024-01-01T12:00:00.123Z", "level": "WARNING", "logger": "urllib3", "message": "Connection timeout"}
```

Only warnings and errors from dependencies, formatted consistently.

## Monitoring and Alerting Integration

Structured logs enable precise monitoring rules:

**Application-level alerts**:
```json
// Alert on payment failures
{
  "query": "level:ERROR AND message:\"Payment failed\"",
  "threshold": 5,
  "window": "5m"
}
```

**Correlation-based alerts**:
```json
// Alert on high error rate per trace
{
  "query": "level:ERROR",
  "group_by": "dd_trace_id", 
  "threshold": 3,
  "window": "1m"
}
```

**Performance monitoring**:
```json
// Track request processing time
{
  "query": "message:\"Request completed\"",
  "metric": "duration",
  "aggregation": "p95"
}
```

Consistent field names across services enable cross-service monitoring.

## Incident Response Capabilities

During production incidents, LogSpark enables rapid response:

**Increase verbosity without redeployment**:
```python
# Emergency debugging
spark_log_manager.adopt_all()
spark_log_manager.unify(level=logging.DEBUG, use_spark_handler=True)
```

**Filter by correlation data**:
```bash
# Find all logs for failing trace
grep "dd_trace_id.*1234567890123456789" /var/log/app.log
```

**Switch output formats**:
```python
# Switch to human-readable for investigation
spark_logger.configure(preset="terminal", no_freeze=True)
```

## Performance Characteristics

JSON preset optimizes for production requirements:

**Minimal formatting overhead**:

- Direct JSON serialization (no string formatting)
- Single-line output (no multi-line processing)
- Efficient field extraction

**Predictable resource usage**:

- Constant memory per log record
- No Rich rendering overhead
- Fast parsing by downstream systems

**Storage efficiency**:

- Compact JSON representation
- Configurable traceback verbosity
- No redundant formatting data

Choose JSON preset when performance and structured output matter more than human readability.