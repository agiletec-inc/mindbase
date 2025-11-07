"""Control endpoints for running Makefile commands."""

import asyncio

from fastapi import APIRouter, HTTPException

from app.schemas.conversation import CommandResult
from app.services import settings_store

router = APIRouter(prefix="/control", tags=["control"])

ACTION_MAP = {
    "up": "up",
    "down": "down",
    "logs": "logs",
    "worker": "worker",
    "restart": "restart",
}


async def run_make_command(command: str) -> CommandResult:
    repo_root = settings_store.get_repo_root()
    process = await asyncio.create_subprocess_exec(
        "make",
        command,
        cwd=str(repo_root),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    return CommandResult(
        action=command,
        returncode=process.returncode,
        stdout=stdout.decode(),
        stderr=stderr.decode(),
    )


@router.post("/{action}", response_model=CommandResult)
async def control_action(action: str) -> CommandResult:
    if action not in ACTION_MAP:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")
    result = await run_make_command(ACTION_MAP[action])
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr or "Command failed")
    return result
