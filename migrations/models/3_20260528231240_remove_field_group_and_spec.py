from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `field_group_config`;
        DROP TABLE IF EXISTS `field_group_field_spec`;
        DROP TABLE IF EXISTS `field_spec`;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
