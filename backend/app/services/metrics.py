import threading
from typing import Dict, Any

class CustomMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.metrics = {
            "total_requests": 0,
            "error_requests": 0,
            "api_latency_avg_ms": 0.0,
            "api_latency_p99_ms": 0.0,
            "llm_calls_total": 0,
            "llm_failures_total": 0,
            "llm_cost_usd": 0.0,
            "job_api_failures": 0,
            "application_submissions": 0,
            "active_users": 0,
            "path_latencies": {},
        }
        self._latency_samples = []

    def record_request(self, path: str, status_code: int, duration_ms: float):
        """Called by ObservabilityMiddleware for every request."""
        with self._lock:
            self.metrics["total_requests"] += 1
            if status_code >= 500:
                self.metrics["error_requests"] += 1

            # Track per-path average latency (keep only route prefix)
            route_key = path.split("?")[0]
            latencies = self.metrics["path_latencies"]
            if route_key not in latencies:
                latencies[route_key] = {"count": 0, "total_ms": 0.0}
            latencies[route_key]["count"] += 1
            latencies[route_key]["total_ms"] += duration_ms

            # Rolling latency samples (keep last 500 for p99)
            self._latency_samples.append(duration_ms)
            if len(self._latency_samples) > 500:
                self._latency_samples = self._latency_samples[-500:]

            total = self.metrics["total_requests"]
            # Incremental average
            self.metrics["api_latency_avg_ms"] = round(
                self.metrics["api_latency_avg_ms"] + (duration_ms - self.metrics["api_latency_avg_ms"]) / total, 2
            )
            # P99 from sample window
            if len(self._latency_samples) >= 10:
                sorted_samples = sorted(self._latency_samples)
                p99_idx = int(len(sorted_samples) * 0.99)
                self.metrics["api_latency_p99_ms"] = round(sorted_samples[min(p99_idx, len(sorted_samples) - 1)], 2)

    def record_llm_call(self, model: str, cost: float = 0.0):
        with self._lock:
            self.metrics["llm_calls_total"] += 1
            self.metrics["llm_cost_usd"] += cost

    def record_llm_failure(self):
        with self._lock:
            self.metrics["llm_failures_total"] += 1

    def record_job_api_failure(self):
        with self._lock:
            self.metrics["job_api_failures"] += 1

    def record_application_submission(self):
        with self._lock:
            self.metrics["application_submissions"] += 1

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            # Return a copy, excluding internal latency sample buffer
            result = dict(self.metrics)
            # Compute top-5 slowest paths for the summary
            path_lats = result.pop("path_latencies", {})
            top_paths = sorted(
                path_lats.items(),
                key=lambda x: x[1]["total_ms"] / max(x[1]["count"], 1),
                reverse=True
            )[:5]
            result["slowest_paths"] = {
                path: {"avg_ms": round(data["total_ms"] / max(data["count"], 1), 2), "count": data["count"]}
                for path, data in top_paths
            }
            return result

metrics_service = CustomMetrics()
