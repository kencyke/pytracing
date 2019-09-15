# pytracing
A python trace profiler that outputs to chrome trace-viewer format (about://tracing).

# usage

```python
from pytracing import TraceProfiler
    tp = TraceProfiler(output=open('/tmp/trace.out', 'wb'))
    with tp.traced():
        ...execute something here...
```
