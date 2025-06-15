#!/usr/bin/env python3
"""
Demonstration of Bulk Operations and Cache Warming

This file demonstrates the new bulk operations and automatic cache warming features:
- Bulk create, update, delete operations
- Automatic cache warming for popular queries
- Performance monitoring and statistics
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.base.models import BaseModel as SQLAlchemyBaseModel
from src.core.base.repo.repository import BaseRepository, CacheConfig, CacheWarmingConfig
from src.tools.pydantic import BaseModel as PydanticBaseModel


# Demo models
class DemoUser(SQLAlchemyBaseModel):
    """Demo user model for bulk operations."""

    __tablename__ = "demo_users"

    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    department = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    salary = Column(Integer, nullable=True)


# Pydantic schemas
class DemoUserCreate(PydanticBaseModel):
    name: str
    email: str
    department: Optional[str] = None
    salary: Optional[int] = None


class DemoUserUpdate(PydanticBaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None
    salary: Optional[int] = None


async def demonstrate_bulk_operations():
    """Demonstrate bulk operations with performance monitoring."""

    # Setup database connection
    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Setup cache with warming
        warming_config = CacheWarmingConfig(
            enabled=True,
            popular_queries_limit=5,
            min_usage_count=3,
            warm_interval_seconds=300,  # 5 minutes
            track_usage=True,
        )

        cache_config = CacheConfig(
            default_ttl=600,  # 10 minutes
            use_memory=True,
            use_redis=False,  # Disable Redis for demo
            warming_config=warming_config,
        )

        repo = BaseRepository[DemoUser, DemoUserCreate, DemoUserUpdate](DemoUser, session, cache_config)

        print("=== Bulk Operations and Cache Warming Demo ===\n")

        # 1. Bulk Create Operations
        print("1. BULK CREATE OPERATIONS")
        print("-" * 30)

        # Generate test data
        bulk_data = []
        departments = ["engineering", "marketing", "sales", "hr", "finance"]

        for i in range(1000):
            bulk_data.append(
                {
                    "name": f"User {i + 1}",
                    "email": f"user{i + 1}@company.com",
                    "department": departments[i % len(departments)],
                    "salary": 50000 + (i * 100),
                }
            )

        # Measure bulk create performance
        start_time = time.time()
        result = await repo.bulk_create(
            bulk_data,
            batch_size=100,
            emit_events=False,  # Disable events for performance
            ignore_conflicts=True,
        )
        bulk_time = time.time() - start_time

        print(f"Bulk created {result.success_count} users in {bulk_time:.2f}s")
        print(f"Errors: {result.error_count}")
        print(f"Performance: {result.success_count / bulk_time:.0f} records/second")

        # Compare with individual creates
        individual_data = [{"name": f"Individual {i}", "email": f"individual{i}@company.com"} for i in range(10)]

        start_time = time.time()
        individual_count = 0
        for data in individual_data:
            try:
                await repo.create(data, emit_event=False)
                individual_count += 1
            except Exception:
                pass
        individual_time = time.time() - start_time

        print(f"Individual created {individual_count} users in {individual_time:.2f}s")
        print(f"Bulk operations are {individual_time / bulk_time * 1000:.1f}x faster!\n")

        # 2. Bulk Update Operations
        print("2. BULK UPDATE OPERATIONS")
        print("-" * 30)

        start_time = time.time()
        update_result = await repo.bulk_update(
            filters={"department": "engineering"},
            update_data={"salary": 80000, "updated_at": datetime.now()},
            batch_size=50,
            emit_events=False,
        )
        update_time = time.time() - start_time

        print(f"Bulk updated {update_result.success_count} users in {update_time:.2f}s")
        print(f"Updated user IDs: {update_result.updated_ids[:5]}... (showing first 5)")
        print(f"Errors: {update_result.error_count}\n")

        # 3. Cache Warming Demonstration
        print("3. CACHE WARMING DEMONSTRATION")
        print("-" * 35)

        # Simulate popular queries to build usage statistics
        print("Simulating popular queries...")
        for _ in range(5):
            await repo.list(limit=10, is_active=True)
            await repo.list(limit=20, department="engineering")
            await repo.count(is_active=True)

        # Check cache warming
        if cache_config.should_warm_cache():
            print("Cache warming triggered!")
            await repo.warm_cache()
        else:
            print("Cache warming not needed yet")

        # Demonstrate cache performance
        print("\nCache performance test:")

        # First query (cold)
        start_time = time.time()
        users1 = await repo.list(limit=100, is_active=True)
        cold_time = time.time() - start_time
        print(f"Cold query: {cold_time:.4f}s, found: {len(users1)}")

        # Second query (cached)
        start_time = time.time()
        users2 = await repo.list(limit=100, is_active=True)
        cached_time = time.time() - start_time
        print(f"Cached query: {cached_time:.4f}s, found: {len(users2)}")

        if cached_time > 0:
            speedup = cold_time / cached_time
            print(f"Cache speedup: {speedup:.1f}x\n")

        # 4. Bulk Delete Operations
        print("4. BULK DELETE OPERATIONS")
        print("-" * 30)

        # Soft delete inactive users
        start_time = time.time()
        delete_result = await repo.bulk_delete(
            filters={"is_active": False}, soft_delete=True, batch_size=50, emit_events=False
        )
        delete_time = time.time() - start_time

        print(f"Bulk soft-deleted {delete_result.success_count} users in {delete_time:.2f}s")
        print(f"Errors: {delete_result.error_count}")

        # Hard delete old test data
        old_date = datetime.now() - timedelta(days=30)
        hard_delete_result = await repo.bulk_delete(
            filters={"created_at__lt": old_date, "email__startswith": "test"}, soft_delete=False, batch_size=25
        )

        print(f"Hard deleted {hard_delete_result.success_count} old test users")
        print(f"Deleted IDs: {hard_delete_result.deleted_ids[:5]}... (showing first 5)\n")

        # 5. Performance Summary
        print("5. PERFORMANCE SUMMARY")
        print("-" * 25)

        total_operations = result.success_count + update_result.success_count + delete_result.success_count
        total_time = bulk_time + update_time + delete_time

        print(f"Total operations: {total_operations}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average throughput: {total_operations / total_time:.0f} operations/second")

        # Cache statistics
        popular_queries = cache_config.get_popular_queries()
        print(f"Popular queries tracked: {len(popular_queries)}")
        print(f"Cache usage tracking: {len(cache_config._query_usage)} unique queries")

        print("\n=== Demo completed successfully! ===")


async def demonstrate_advanced_bulk_features():
    """Demonstrate advanced bulk operation features."""

    engine = create_async_engine("postgresql+asyncpg://user:pass@localhost/db")
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        repo = BaseRepository[DemoUser, DemoUserCreate, DemoUserUpdate](DemoUser, session)

        print("=== Advanced Bulk Features Demo ===\n")

        # 1. Bulk create with conflict handling
        print("1. BULK CREATE WITH CONFLICT HANDLING")
        print("-" * 40)

        # Create data with potential conflicts
        conflicting_data = [
            {"name": "John Doe", "email": "john@company.com"},
            {"name": "Jane Smith", "email": "jane@company.com"},
            {"name": "John Doe", "email": "john@company.com"},  # Duplicate
            {"name": "Bob Wilson", "email": "bob@company.com"},
        ]

        # With conflict handling
        result_ignore = await repo.bulk_create(conflicting_data, ignore_conflicts=True, emit_events=True)

        print(f"With ignore_conflicts=True:")
        print(f"  Success: {result_ignore.success_count}")
        print(f"  Errors: {result_ignore.error_count}")
        print(f"  Error messages: {result_ignore.errors[:2]}")

        # 2. Conditional bulk updates
        print("\n2. CONDITIONAL BULK UPDATES")
        print("-" * 30)

        # Update only high-salary users
        conditional_result = await repo.bulk_update(
            filters={"salary__gte": 70000, "department__in": ["engineering", "sales"]},
            update_data={"is_active": True, "updated_at": datetime.now()},
        )

        print(f"Conditional update result:")
        print(f"  Updated: {conditional_result.success_count}")
        print(f"  Errors: {conditional_result.error_count}")

        # 3. Batch size optimization
        print("\n3. BATCH SIZE OPTIMIZATION")
        print("-" * 30)

        # Test different batch sizes
        test_data = [{"name": f"Batch Test {i}", "email": f"batch{i}@test.com"} for i in range(500)]

        batch_sizes = [50, 100, 250]

        for batch_size in batch_sizes:
            start_time = time.time()
            batch_result = await repo.bulk_create(test_data, batch_size=batch_size, emit_events=False)
            batch_time = time.time() - start_time

            print(
                f"  Batch size {batch_size}: {batch_time:.2f}s, {batch_result.success_count / batch_time:.0f} ops/sec"
            )

        # 4. Memory-efficient processing
        print("\n4. MEMORY-EFFICIENT PROCESSING")
        print("-" * 35)

        # Process large dataset in chunks
        async def process_large_dataset():
            chunk_size = 1000
            total_processed = 0

            for chunk_start in range(0, 5000, chunk_size):
                chunk_data = [
                    {"name": f"Large Dataset User {i}", "email": f"large{i}@dataset.com", "department": "bulk_test"}
                    for i in range(chunk_start, min(chunk_start + chunk_size, 5000))
                ]

                chunk_result = await repo.bulk_create(chunk_data, batch_size=100, emit_events=False)

                total_processed += chunk_result.success_count
                print(f"  Processed chunk {chunk_start // chunk_size + 1}: {chunk_result.success_count} records")

            return total_processed

        start_time = time.time()
        total_processed = await process_large_dataset()
        processing_time = time.time() - start_time

        print(f"Total processed: {total_processed} records in {processing_time:.2f}s")
        print(f"Memory-efficient throughput: {total_processed / processing_time:.0f} records/sec")

        # Cleanup
        cleanup_result = await repo.bulk_delete(
            filters={"department": "bulk_test"}, soft_delete=False, emit_events=False
        )
        print(f"\nCleanup: removed {cleanup_result.success_count} test records")

        print("\n=== Advanced demo completed! ===")


if __name__ == "__main__":
    # Run demonstrations
    print("Starting bulk operations demonstration...\n")

    # Basic bulk operations demo
    asyncio.run(demonstrate_bulk_operations())

    print("\n" + "=" * 50 + "\n")

    # Advanced features demo
    asyncio.run(demonstrate_advanced_bulk_features())
