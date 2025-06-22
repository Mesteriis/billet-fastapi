"""
TestStaticSchema monitoring service for Enterprise level.

Template Version: v1.0.0 (Complete)
Features: Advanced metrics, Alerting, Performance analysis, Custom dashboards
"""

import time
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import logging

# Enterprise monitoring dependencies
try:
    from prometheus_client import CollectorRegistry, Counter, Histogram, Gauge, generate_latest
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    logging.warning("Enterprise monitoring dependencies not available")

# Structured logging
try:
    import structlog
    logger = structlog.get_logger("monitoring.test_static_schemas")
except ImportError:
    import logging
    logger = logging.getLogger("monitoring.test_static_schemas")

# Redis for metrics storage
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class TestStaticSchemaMonitoringService:
    """
    Enterprise-grade monitoring service for TestStaticSchema operations.
    
    Features:
    - Advanced metrics collection and aggregation
    - Real-time alerting and notifications
    - Performance analysis and bottleneck detection
    - Custom dashboards and reporting
    - Distributed tracing integration
    - SLA monitoring and compliance tracking
    
    Example:
        >>> monitoring = TestStaticSchemaMonitoringService()
        >>> await monitoring.record_operation("create", success=True, duration=0.5)
        >>> metrics = await monitoring.get_performance_metrics()
        >>> alerts = await monitoring.check_alert_conditions()
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        enable_tracing: bool = True,
        alert_thresholds: Optional[Dict[str, float]] = None
    ):
        """
        Initialize enterprise monitoring service.
        
        Args:
            redis_client: Redis client for metrics storage
            enable_tracing: Enable distributed tracing
            alert_thresholds: Custom alert thresholds
        """
        self.redis = redis_client
        self.enable_tracing = enable_tracing and MONITORING_AVAILABLE
        
        # Default alert thresholds
        self.alert_thresholds = alert_thresholds or {
            "error_rate_threshold": 0.05,  # 5% error rate
            "response_time_p95": 2.0,      # 2 seconds
            "throughput_min": 10,          # 10 req/min minimum
            "memory_usage_max": 0.85,      # 85% memory usage
            "disk_usage_max": 0.90         # 90% disk usage
        }
        
        # Prometheus metrics registry
        if MONITORING_AVAILABLE:
            self.registry = CollectorRegistry()
            self._setup_metrics()
            
        # Tracing setup
        if self.enable_tracing:
            self.tracer = trace.get_tracer(__name__)

    def _setup_metrics(self):
        """Setup enterprise-level Prometheus metrics."""
        # Business metrics
        self.operation_counter = Counter(
            'test_static_schemas_operations_total',
            'Total teststaticschema operations',
            ['operation', 'status', 'user_type'],
            registry=self.registry
        )
        
        self.operation_duration = Histogram(
            'test_static_schemas_operation_duration_seconds',
            'Operation duration in seconds',
            ['operation'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # System metrics
        self.active_connections = Gauge(
            'test_static_schemas_active_connections',
            'Number of active database connections',
            registry=self.registry
        )
        
        self.cache_hit_rate = Gauge(
            'test_static_schemas_cache_hit_rate',
            'Cache hit rate percentage',
            registry=self.registry
        )
        
        # SLA metrics
        self.sla_compliance = Gauge(
            'test_static_schemas_sla_compliance',
            'SLA compliance percentage',
            ['sla_type'],
            registry=self.registry
        )

    async def record_operation(
        self,
        operation: str,
        success: bool = True,
        duration: float = 0,
        user_type: str = "regular",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a business operation with metrics."""
        try:
            # Record in Prometheus
            if MONITORING_AVAILABLE:
                status = "success" if success else "error"
                self.operation_counter.labels(
                    operation=operation,
                    status=status,
                    user_type=user_type
                ).inc()
                
                if duration > 0:
                    self.operation_duration.labels(operation=operation).observe(duration)
            
            # Store in Redis for aggregation
            if self.redis and REDIS_AVAILABLE:
                await self._store_operation_data({
                    "operation": operation,
                    "success": success,
                    "duration": duration,
                    "user_type": user_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": metadata or {}
                })
            
            # Structured logging
            logger.info(
                "Operation recorded",
                operation=operation,
                success=success,
                duration=duration,
                user_type=user_type
            )
            
        except Exception as e:
            logger.error(f"Failed to record operation: {e}", exc_info=True)

    async def _store_operation_data(self, operation_data: Dict[str, Any]) -> None:
        """Store operation data in Redis for analysis."""
        try:
            # Store in time-series format
            timestamp = int(time.time())
            key = f"test_static_schemas:operations:{timestamp}"
            
            await self.redis.setex(
                key,
                timedelta(days=7).total_seconds(),  # Keep for 7 days
                json.dumps(operation_data)
            )
            
            # Add to operation index
            await self.redis.zadd(
                "test_static_schemas:operations:index",
                {key: timestamp}
            )
            
        except Exception as e:
            logger.error(f"Failed to store operation data: {e}")

    async def get_performance_metrics(
        self,
        time_range: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        try:
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "time_range": str(time_range),
                "prometheus_metrics": {},
                "business_metrics": {},
                "system_health": {}
            }
            
            # Get Prometheus metrics
            if MONITORING_AVAILABLE:
                metrics["prometheus_metrics"] = self._get_prometheus_metrics()
            
            # Get business metrics from Redis
            if self.redis and REDIS_AVAILABLE:
                metrics["business_metrics"] = await self._get_business_metrics(time_range)
            
            # System health checks
            metrics["system_health"] = await self._get_system_health()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {"error": str(e)}

    def _get_prometheus_metrics(self) -> Dict[str, Any]:
        """Get current Prometheus metrics."""
        try:
            # Get current metric values
            return {
                "registry_metrics": generate_latest(self.registry).decode('utf-8'),
                "active_connections": self.active_connections._value._value,
                "cache_hit_rate": self.cache_hit_rate._value._value,
            }
        except Exception as e:
            logger.error(f"Failed to get Prometheus metrics: {e}")
            return {}

    async def _get_business_metrics(self, time_range: timedelta) -> Dict[str, Any]:
        """Get business metrics from Redis storage."""
        try:
            end_time = int(time.time())
            start_time = end_time - int(time_range.total_seconds())
            
            # Get operations in time range
            operation_keys = await self.redis.zrangebyscore(
                "test_static_schemas:operations:index",
                start_time,
                end_time
            )
            
            # Analyze operations
            total_operations = len(operation_keys)
            successful_operations = 0
            total_duration = 0
            operation_types = {}
            
            for key in operation_keys:
                data = await self.redis.get(key)
                if data:
                    operation = json.loads(data)
                    if operation["success"]:
                        successful_operations += 1
                    total_duration += operation["duration"]
                    
                    op_type = operation["operation"]
                    operation_types[op_type] = operation_types.get(op_type, 0) + 1
            
            success_rate = successful_operations / total_operations if total_operations > 0 else 0
            avg_duration = total_duration / total_operations if total_operations > 0 else 0
            
            return {
                "total_operations": total_operations,
                "success_rate": success_rate,
                "average_duration": avg_duration,
                "operation_types": operation_types,
                "throughput": total_operations / time_range.total_seconds() * 60  # per minute
            }
            
        except Exception as e:
            logger.error(f"Failed to get business metrics: {e}")
            return {}

    async def _get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics."""
        try:
            import psutil
            
            return {
                "cpu_usage": psutil.cpu_percent(),
                "memory_usage": psutil.virtual_memory().percent / 100,
                "disk_usage": psutil.disk_usage('/').percent / 100,
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else None
            }
            
        except ImportError:
            return {"error": "psutil not available for system metrics"}
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            return {"error": str(e)}

    async def check_alert_conditions(self) -> List[Dict[str, Any]]:
        """Check for alert conditions and return active alerts."""
        alerts = []
        
        try:
            # Get current metrics
            metrics = await self.get_performance_metrics()
            business_metrics = metrics.get("business_metrics", {})
            system_health = metrics.get("system_health", {})
            
            # Check error rate
            success_rate = business_metrics.get("success_rate", 1.0)
            error_rate = 1.0 - success_rate
            if error_rate > self.alert_thresholds["error_rate_threshold"]:
                alerts.append({
                    "type": "error_rate",
                    "severity": "high",
                    "message": f"Error rate {error_rate:.2%} exceeds threshold {self.alert_thresholds['error_rate_threshold']:.2%}",
                    "value": error_rate,
                    "threshold": self.alert_thresholds["error_rate_threshold"]
                })
            
            # Check response time
            avg_duration = business_metrics.get("average_duration", 0)
            if avg_duration > self.alert_thresholds["response_time_p95"]:
                alerts.append({
                    "type": "response_time",
                    "severity": "medium",
                    "message": f"Average response time {avg_duration:.2f}s exceeds threshold {self.alert_thresholds['response_time_p95']}s",
                    "value": avg_duration,
                    "threshold": self.alert_thresholds["response_time_p95"]
                })
            
            # Check throughput
            throughput = business_metrics.get("throughput", 0)
            if throughput < self.alert_thresholds["throughput_min"]:
                alerts.append({
                    "type": "low_throughput",
                    "severity": "medium",
                    "message": f"Throughput {throughput:.1f} req/min below threshold {self.alert_thresholds['throughput_min']}",
                    "value": throughput,
                    "threshold": self.alert_thresholds["throughput_min"]
                })
            
            # Check system resources
            memory_usage = system_health.get("memory_usage", 0)
            if memory_usage > self.alert_thresholds["memory_usage_max"]:
                alerts.append({
                    "type": "high_memory",
                    "severity": "high",
                    "message": f"Memory usage {memory_usage:.1%} exceeds threshold {self.alert_thresholds['memory_usage_max']:.1%}",
                    "value": memory_usage,
                    "threshold": self.alert_thresholds["memory_usage_max"]
                })
            
            disk_usage = system_health.get("disk_usage", 0)
            if disk_usage > self.alert_thresholds["disk_usage_max"]:
                alerts.append({
                    "type": "high_disk",
                    "severity": "high",
                    "message": f"Disk usage {disk_usage:.1%} exceeds threshold {self.alert_thresholds['disk_usage_max']:.1%}",
                    "value": disk_usage,
                    "threshold": self.alert_thresholds["disk_usage_max"]
                })
            
            # Log alerts
            if alerts:
                logger.warning(f"Active alerts detected: {len(alerts)}", alerts=alerts)
            
            return alerts
            
        except Exception as e:
            logger.error(f"Failed to check alert conditions: {e}")
            return [{
                "type": "monitoring_error",
                "severity": "high",
                "message": f"Alert checking failed: {str(e)}"
            }]

    async def calculate_sla_compliance(
        self,
        sla_type: str = "availability",
        time_range: timedelta = timedelta(days=30)
    ) -> float:
        """Calculate SLA compliance percentage."""
        try:
            if sla_type == "availability":
                # Calculate uptime percentage
                metrics = await self.get_performance_metrics(time_range)
                business_metrics = metrics.get("business_metrics", {})
                success_rate = business_metrics.get("success_rate", 0)
                
                # Update SLA gauge
                if MONITORING_AVAILABLE:
                    self.sla_compliance.labels(sla_type="availability").set(success_rate)
                
                return success_rate
                
            elif sla_type == "performance":
                # Calculate performance SLA (response time < threshold)
                metrics = await self.get_performance_metrics(time_range)
                business_metrics = metrics.get("business_metrics", {})
                avg_duration = business_metrics.get("average_duration", 0)
                
                # Performance SLA: 95% of requests under 2 seconds
                compliance = 1.0 if avg_duration < 2.0 else 0.8  # Simplified calculation
                
                if MONITORING_AVAILABLE:
                    self.sla_compliance.labels(sla_type="performance").set(compliance)
                
                return compliance
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Failed to calculate SLA compliance: {e}")
            return 0.0

    async def health_check(self) -> Dict[str, Any]:
        """Enterprise monitoring service health check."""
        return {
            "status": "healthy",
            "monitoring_available": MONITORING_AVAILABLE,
            "redis_available": REDIS_AVAILABLE and bool(self.redis),
            "tracing_enabled": self.enable_tracing,
            "timestamp": datetime.utcnow().isoformat()
        } 