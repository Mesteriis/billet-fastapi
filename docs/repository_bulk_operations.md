# Bulk Operations and Cache Warming Guide

This guide covers the advanced bulk operations and automatic cache warming features of the BaseRepository system.

## Table of Contents

1. [Bulk Operations Overview](#bulk-operations-overview)
2. [Bulk Create Operations](#bulk-create-operations)
3. [Bulk Update Operations](#bulk-update-operations)
4. [Bulk Delete Operations](#bulk-delete-operations)
5. [Cache Warming System](#cache-warming-system)
6. [Performance Optimization](#performance-optimization)
7. [Error Handling](#error-handling)
8. [Best Practices](#best-practices)

## Bulk Operations Overview

Bulk operations allow you to perform mass database operations efficiently, processing hundreds or thousands of records in a single operation. This is significantly faster than individual operations and reduces database load.

### Key Benefits

- **Performance**: 10-100x faster than individual operations
- **Memory Efficiency**: Processes data in configurable batches
- **Transaction Safety**: All operations within a batch are atomic
- **Error Handling**: Detailed error reporting with partial success support
- **Event System**: Optional event emission for each operation
- **Cache Management**: Automatic cache invalidation after bulk operations

### Supported Operations

- `bulk_create()` - Create multiple records
- `bulk_update()` - Update multiple records based on filters
- `bulk_delete()` - Delete multiple records (soft or hard delete)

## Bulk Create Operations

### Basic Usage

```python
from src.core.base.repo.repository import BaseRepository, BulkOperationResult

# Create repository
repo = BaseRepository[User, UserCreate, UserUpdate](User, db_session)

# Prepare data
users_data = [
    {"name": "John Doe", "email": "john@example.com"},
    {"name": "Jane Smith", "email": "jane@example.com"},
    {"name": "Bob Wilson", "email": "bob@example.com"}
]

# Bulk create
result: BulkOperationResult = await repo.bulk_create(users_data)

print(f"Created: {result.success_count}")
print(f"Errors: {result.error_count}")
print(f"Created IDs: {result.created_ids}")
```

### Advanced Options

```python
# Bulk create with advanced options
result = await repo.bulk_create(
    data_list=users_data,
    batch_size=100,           # Process 100 records per batch
    emit_events=True,         # Emit creation events
    ignore_conflicts=True     # Ignore unique constraint violations
)

# Handle results
if result.error_count > 0:
    print("Errors occurred:")
    for error in result.errors:
        print(f"  - {error}")

# Process created records
for user_id in result.created_ids:
    print(f"Created user: {user_id}")
```

### Performance Comparison

```python
import time

# Individual creates (slow)
start_time = time.time()
for data in users_data:
    await repo.create(data)
individual_time = time.time() - start_time

# Bulk create (fast)
start_time = time.time()
await repo.bulk_create(users_data)
bulk_time = time.time() - start_time

print(f"Individual: {individual_time:.2f}s")
print(f"Bulk: {bulk_time:.2f}s")
print(f"Speedup: {individual_time/bulk_time:.1f}x")
```

## Bulk Update Operations

### Basic Usage

```python
# Update all users in a department
result = await repo.bulk_update(
    filters={"department": "engineering"},
    update_data={"salary": 80000, "updated_at": datetime.now()}
)

print(f"Updated {result.success_count} users")
```

### Complex Filtering

```python
# Update with complex filters
result = await repo.bulk_update(
    filters={
        "salary__lt": 50000,
        "department__in": ["sales", "marketing"],
        "is_active": True
    },
    update_data={
        "salary": 55000,
        "bonus_eligible": True
    },
    batch_size=50,
    emit_events=True
)
```

### Conditional Updates

```python
# Update only if conditions are met
from datetime import datetime, timedelta

old_date = datetime.now() - timedelta(days=90)

result = await repo.bulk_update(
    filters={
        "last_login__lt": old_date,
        "is_active": True
    },
    update_data={
        "is_active": False,
        "deactivated_at": datetime.now(),
        "deactivation_reason": "inactive"
    }
)
```

## Bulk Delete Operations

### Soft Delete (Recommended)

```python
# Soft delete inactive users
result = await repo.bulk_delete(
    filters={"is_active": False},
    soft_delete=True,  # Default
    emit_events=True
)

print(f"Soft deleted {result.success_count} users")
```

### Hard Delete (Permanent)

```python
# Hard delete old test data
result = await repo.bulk_delete(
    filters={
        "email__startswith": "test_",
        "created_at__lt": datetime.now() - timedelta(days=30)
    },
    soft_delete=False,  # Permanent deletion
    batch_size=25
)

print(f"Permanently deleted {result.success_count} records")
```

### Cleanup Operations

```python
# Cleanup old soft-deleted records
cleanup_date = datetime.now() - timedelta(days=365)

result = await repo.bulk_delete(
    filters={
        "deleted_at__lt": cleanup_date,
        "deleted_at__isnotnull": True
    },
    soft_delete=False,  # Permanent cleanup
    emit_events=False   # Skip events for cleanup
)
```

## Cache Warming System

The cache warming system automatically identifies popular queries and pre-loads them into cache to improve performance.

### Configuration

```python
from src.core.base.repo.repository import CacheConfig, CacheWarmingConfig

# Configure cache warming
warming_config = CacheWarmingConfig(
    enabled=True,
    popular_queries_limit=10,    # Track top 10 queries
    min_usage_count=5,           # Query must be used 5+ times
    warm_interval_seconds=3600,  # Warm every hour
    track_usage=True             # Enable usage tracking
)

cache_config = CacheConfig(
    redis_client=redis_client,
    default_ttl=600,
    warming_config=warming_config
)

repo = BaseRepository(User, db_session, cache_config)
```

### Manual Cache Warming

```python
# Manually warm cache
await repo.warm_cache()

# Check if warming is needed
if repo._cache_config.should_warm_cache():
    await repo.warm_cache()
```

### Cache Performance Monitoring

```python
# Monitor cache performance
start_time = time.time()
users = await repo.list(limit=100, is_active=True)  # Cold query
cold_time = time.time() - start_time

start_time = time.time()
users = await repo.list(limit=100, is_active=True)  # Cached query
cached_time = time.time() - start_time

speedup = cold_time / cached_time if cached_time > 0 else 0
print(f"Cache speedup: {speedup:.1f}x")
```

### Popular Queries Tracking

```python
# Get popular queries
popular_queries = repo._cache_config.get_popular_queries()
print(f"Popular queries: {len(popular_queries)}")

# Get usage statistics
usage_stats = repo._cache_config._query_usage
print(f"Total tracked queries: {len(usage_stats)}")
```

## Performance Optimization

### Batch Size Tuning

```python
# Test different batch sizes
batch_sizes = [50, 100, 250, 500]
test_data = [{"name": f"User {i}"} for i in range(1000)]

for batch_size in batch_sizes:
    start_time = time.time()
    result = await repo.bulk_create(test_data, batch_size=batch_size)
    duration = time.time() - start_time

    throughput = result.success_count / duration
    print(f"Batch size {batch_size}: {throughput:.0f} records/sec")
```

### Memory-Efficient Processing

```python
# Process large datasets in chunks
async def process_large_dataset(total_records: int, chunk_size: int = 1000):
    total_processed = 0

    for chunk_start in range(0, total_records, chunk_size):
        chunk_end = min(chunk_start + chunk_size, total_records)

        # Generate chunk data
        chunk_data = [
            {"name": f"User {i}", "email": f"user{i}@example.com"}
            for i in range(chunk_start, chunk_end)
        ]

        # Process chunk
        result = await repo.bulk_create(
            chunk_data,
            batch_size=100,
            emit_events=False  # Disable for performance
        )

        total_processed += result.success_count
        print(f"Processed chunk {chunk_start//chunk_size + 1}: "
              f"{result.success_count} records")

    return total_processed

# Process 10,000 records efficiently
total = await process_large_dataset(10000)
print(f"Total processed: {total}")
```

### Event Management

```python
# Disable events for maximum performance
result = await repo.bulk_create(
    large_dataset,
    emit_events=False,  # Skip event emission
    batch_size=500
)

# Enable events for important operations
result = await repo.bulk_update(
    filters={"role": "admin"},
    update_data={"last_privilege_check": datetime.now()},
    emit_events=True  # Track admin changes
)
```

## Error Handling

### Comprehensive Error Handling

```python
try:
    result = await repo.bulk_create(users_data)

    if result.error_count > 0:
        print(f"Partial success: {result.success_count} created, {result.error_count} failed")

        # Log specific errors
        for i, error in enumerate(result.errors):
            print(f"Error {i+1}: {error}")

        # Continue with successful IDs
        for user_id in result.created_ids:
            await process_created_user(user_id)

    else:
        print(f"Complete success: {result.success_count} users created")

except Exception as e:
    print(f"Bulk operation failed completely: {e}")
```

### Conflict Resolution

```python
# Handle unique constraint conflicts
result = await repo.bulk_create(
    potentially_duplicate_data,
    ignore_conflicts=True
)

# Check for conflicts
conflicts = [error for error in result.errors if "unique" in error.lower()]
if conflicts:
    print(f"Handled {len(conflicts)} unique constraint conflicts")
```

### Transaction Rollback

```python
# Bulk operations are transactional within batches
try:
    async with db_session.begin():
        result1 = await repo.bulk_create(batch1)
        result2 = await repo.bulk_create(batch2)

        if result1.error_count > 0 or result2.error_count > 0:
            raise Exception("Batch processing failed")

except Exception:
    # Both batches will be rolled back
    print("All operations rolled back")
```

## Best Practices

### 1. Choose Appropriate Batch Sizes

```python
# Guidelines for batch sizes:
# - Small records (few fields): 500-1000 per batch
# - Medium records (10-20 fields): 100-500 per batch
# - Large records (many fields/relations): 50-100 per batch
# - Very large records: 10-50 per batch

# Test and optimize for your use case
optimal_batch_size = await find_optimal_batch_size(sample_data)
```

### 2. Use Appropriate Delete Strategy

```python
# Use soft delete for user data (recoverable)
await repo.bulk_delete(
    filters={"status": "inactive"},
    soft_delete=True
)

# Use hard delete for cleanup/maintenance
await repo.bulk_delete(
    filters={"type": "temporary", "created_at__lt": old_date},
    soft_delete=False
)
```

### 3. Monitor Performance

```python
# Always measure performance
import time
from contextlib import asynccontextmanager

@asynccontextmanager
async def measure_time(operation_name: str):
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        print(f"{operation_name}: {duration:.2f}s")

# Usage
async with measure_time("Bulk user creation"):
    result = await repo.bulk_create(users_data)
```

### 4. Handle Large Datasets

```python
# For very large datasets, use streaming approach
async def stream_bulk_create(data_generator, batch_size: int = 100):
    batch = []
    total_processed = 0

    async for item in data_generator:
        batch.append(item)

        if len(batch) >= batch_size:
            result = await repo.bulk_create(batch)
            total_processed += result.success_count
            batch = []

    # Process remaining items
    if batch:
        result = await repo.bulk_create(batch)
        total_processed += result.success_count

    return total_processed
```

### 5. Cache Management

```python
# Clear cache after bulk operations if needed
await repo.bulk_create(large_dataset)
await repo.invalidate_cache("list:*")  # Clear list queries

# Warm cache for frequently accessed data
await repo.bulk_create(new_users)
await repo.warm_cache()  # Pre-load popular queries
```

### 6. Error Recovery

```python
# Implement retry logic for failed operations
async def bulk_create_with_retry(data_list, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            result = await repo.bulk_create(data_list)

            if result.error_count == 0:
                return result

            # Retry only failed items (if identifiable)
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff

        except Exception as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1} failed with exception: {e}")

    return result
```

## Conclusion

Bulk operations and cache warming provide significant performance improvements for applications dealing with large datasets. Key takeaways:

- Use bulk operations for mass data processing (10-100x performance improvement)
- Configure cache warming for frequently accessed queries
- Choose appropriate batch sizes based on your data and hardware
- Implement proper error handling and monitoring
- Use soft deletes for user data, hard deletes for cleanup
- Monitor and optimize performance regularly

For more examples, see `examples/bulk_operations_demo.py`.
