import discord

ROSTER_MANAGER_ROLE = "roster-manager"
PLAYER_MANAGER_ROLE = "player-manager"
OFFICER_ROLES = {"R4", "R5"}


async def ensure_role_exists(
    guild: discord.Guild,
    role_name: str,
    *,
    mentionable: bool = False,
    reason: str,
) -> discord.Role | None:
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        return role
    try:
        return await guild.create_role(name=role_name, mentionable=mentionable, reason=reason)
    except discord.Forbidden:
        return None
    except discord.HTTPException:
        return None


async def bootstrap_management_roles(guild: discord.Guild, actor: discord.abc.User) -> None:
    reason = f"Bootstrap management roles requested by {actor.display_name}"
    await ensure_role_exists(guild, ROSTER_MANAGER_ROLE, reason=reason)
    await ensure_role_exists(guild, PLAYER_MANAGER_ROLE, reason=reason)


def has_roster_manager_permission(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_names = {role.name for role in member.roles}
    return ROSTER_MANAGER_ROLE in role_names


def has_player_manager_permission(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_names = {role.name for role in member.roles}
    return ROSTER_MANAGER_ROLE in role_names or PLAYER_MANAGER_ROLE in role_names


def has_officer_permission(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    role_names = {role.name for role in member.roles}
    return bool(role_names.intersection(OFFICER_ROLES))
