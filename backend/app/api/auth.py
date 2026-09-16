from datetime import timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, Token
from app.schemas.mcp_access_token import MCPAccessTokenCreate, MCPAccessTokenCreateResponse, MCPAccessTokenMetadata
from app.services.auth import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from app.services.mcp_access_token import MCPAccessTokenService
from app.services.user import UserService

router = APIRouter(prefix="/api/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def _get_user_from_access_token(token: Optional[str], db: Session):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    if payload.get("scope") == "note_collab":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Scoped token cannot access this endpoint")
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    service = UserService(db)
    try:
        user = service.get_by_id(UUID(user_id))
    except (ValueError, AttributeError):
        raise credentials_exception
    if user is None:
        raise credentials_exception
    return user


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    return _get_user_from_access_token(token, db)


def get_current_user_from_query_token(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Authenticate an ordinary access token supplied for browser media loads."""
    return _get_user_from_access_token(token, db)


def get_scoped_collaboration_access(
    websocket: WebSocket,
    note_id: UUID,
    db: Session = Depends(get_db),
):
    """Authenticate a short-lived note collaboration ticket for WebSocket routes."""
    from app.collaboration import is_valid_collaboration_ticket
    from app.services.note import NoteService

    ticket = websocket.query_params.get("ticket")
    payload = decode_access_token(ticket) if ticket else None
    if not is_valid_collaboration_ticket(payload, note_id):
        raise WebSocketException(code=4401)
    try:
        user_id = UUID(payload["sub"])
        service = NoteService(db)
        access = service.require_node_access(note_id, user_id)
        user = db.query(User).filter(User.id == user_id).first()
    except (KeyError, TypeError, ValueError, PermissionError):
        raise WebSocketException(code=4403)
    if user is None:
        raise WebSocketException(code=4401)
    return {"user": user, "access": access, "payload": payload, "db": db}


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    service = UserService(db)
    try:
        user = service.create_user(user_in)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    service = UserService(db)
    user = service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=Token)
def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_refresh_token(body.refresh_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    service = UserService(db)
    try:
        user = service.get_by_id(UUID(user_id))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/mcp-tokens", response_model=MCPAccessTokenCreateResponse)
def create_mcp_token(data: MCPAccessTokenCreate, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    token, raw_token = MCPAccessTokenService(db).create_token(current_user.id, data)
    return {**MCPAccessTokenService._metadata(token), "token": raw_token}


@router.get("/mcp-tokens", response_model=list[MCPAccessTokenMetadata])
def list_mcp_tokens(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return MCPAccessTokenService(db).list_tokens(current_user.id)


@router.delete("/mcp-tokens/{token_id}", response_model=MCPAccessTokenMetadata)
def revoke_mcp_token(token_id: UUID, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return MCPAccessTokenService(db).revoke(token_id, current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="MCP token not found")
