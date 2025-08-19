from src.database import get_session
from src.models.role_model import Role, PermissionLevel, PermissionType
from sqlalchemy import select
from typing import Dict

DEFAULT_ROLES = [
    {
        "name": "пользователь",
        "description": "Обычный пользователь с базовыми правами",
        "level": PermissionLevel.USER,
        "default_role": True
    },
    {
        "name": "начинающий модератор",
        "description": "Может отвечать на обращения поддержки",
        "level": PermissionLevel.JUNIOR_MODERATOR
    },
    {
        "name": "модератор",
        "description": "Может рассматривать жалобы, а также быть наставником",
        "level": PermissionLevel.MODERATOR
    },
    {
        "name": "модератор по мультиаккаунтам",
        "description": "Отвечает за учет и работу с мультиаккаунтами",
        "level": PermissionLevel.MULTI_ACCOUNT_MODERATOR
    },
    {
        "name": "супервайзер модераторов",
        "description": "Следит за активными чатами и ведет отчетность",
        "level": PermissionLevel.MODERATOR_SUPERVISOR
    },
    {
        "name": "чиф куратор",
        "description": "Отвечает на жалобы на модерацию",
        "level": PermissionLevel.CHIEF_CURATOR
    },
    {
        "name": "главный администратор",
        "description": "Отвечает на обращения по амнистии",
        "level": PermissionLevel.LEAD_ADMINISTRATOR
    },
    {
        "name": "модератор форума",
        "description": "Управляет ролями и пользователями на форуме",
        "level": PermissionLevel.FORUM_MODERATOR
    },
    {
        "name": "руководство",
        "description": "Высшее руководство модерации",
        "level": PermissionLevel.EXECUTIVE_MODERATOR
    }
]

def generate_role_permissions(level: PermissionLevel) -> Dict[str, bool]:
    """Генерирует словарь permissions на основе уровня роли"""
    return {
        perm.value: perm.level.value <= level.value
        for perm in PermissionType
    }

async def init_roles():
    async for db in get_session():
        try:
            for role_data in DEFAULT_ROLES:
                existing_role = await db.execute(
                    select(Role).where(Role.name == role_data["name"])
                )
                if not existing_role.scalars().first():
                    permissions = generate_role_permissions(role_data["level"])
                    role = Role(
                        **role_data,
                        permissions=permissions
                    )
                    db.add(role)
                    await db.commit()
        except Exception as e:
            await db.rollback()
            raise e