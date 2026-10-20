"""Mock authentication: the X-User header identifies the caller.

This is the only place identity is established. Routes receive a `User` via
dependency injection and never read identity from bodies or query params.
"""

import json
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status

from app.models import User
from app.providers.mock import DEFAULT_SEED_PATH


class UserDirectory:
    def __init__(self, seed_path: Path = DEFAULT_SEED_PATH) -> None:
        data = json.loads(seed_path.read_text(encoding="utf-8"))
        self._users: dict[str, User] = {
            username: User(username=username, team=team) for username, team in data["users"].items()
        }

    def get(self, username: str) -> User | None:
        return self._users.get(username)


def get_current_user(request: Request, x_user: Annotated[str | None, Header()] = None) -> User:
    if not x_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User header. Send your username, e.g. 'X-User: alice'.",
        )
    directory: UserDirectory = request.app.state.users
    user = directory.get(x_user)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unknown user '{x_user}'.",
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
