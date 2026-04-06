"""Seed the database with test data for local development."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.content import Content, ContentStatus, ContentType


async def seed():
    async with AsyncSessionLocal() as db:
        # Create test users
        admin = User(
            feishu_open_id="ou_admin_test",
            feishu_union_id="on_admin_test",
            name="管理员",
            role=UserRole.admin,
        )
        reviewer = User(
            feishu_open_id="ou_reviewer_test",
            feishu_union_id="on_reviewer_test",
            name="审核员",
            role=UserRole.reviewer,
        )
        employee = User(
            feishu_open_id="ou_employee_test",
            feishu_union_id="on_employee_test",
            name="普通员工",
            role=UserRole.employee,
        )
        db.add_all([admin, reviewer, employee])
        await db.flush()

        # Create sample content
        contents = [
            Content(
                title="夏季促销主图",
                description="2024年夏季大促销主视觉图",
                tags=["夏季", "促销", "主图"],
                content_type=ContentType.image,
                status=ContentStatus.approved,
                file_key="uploads/ab/abcdef.jpg",
                uploaded_by=employee.id,
                ai_summary="夏季促销活动主视觉，色彩鲜明，突出优惠力度",
                ai_keywords=["夏季", "促销", "活动", "优惠"],
            ),
            Content(
                title="品牌宣传视频",
                description="有方大健康品牌故事视频",
                tags=["品牌", "宣传", "视频"],
                content_type=ContentType.video,
                status=ContentStatus.pending,
                file_key="uploads/cd/cdefgh.mp4",
                uploaded_by=employee.id,
            ),
        ]
        db.add_all(contents)
        await db.commit()
        print("✅ Seed data inserted successfully")


if __name__ == "__main__":
    asyncio.run(seed())
