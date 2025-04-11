from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.database.connection import get_db
from app.database.models import User
from app.services import chat_history_service
from app.dependencies.auth import get_current_user

router = APIRouter(
    prefix="/chat-history",
    tags=["Chat History"],
    responses={404: {"description": "Not found"}},
)

class ChatHistoryEntry(BaseModel):
    id: int
    query: str
    response: str
    parsed_response: Optional[Dict[str, Any]] = None
    timestamp: datetime
    
    class Config:
        orm_mode = True

@router.get("/", response_model=List[ChatHistoryEntry])
def get_chat_history(
    skip: int = Query(0, description="Number of records to skip for pagination"),
    limit: int = Query(50, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve chat history for the authenticated user
    """
    chat_history = chat_history_service.get_chat_history_for_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit
    )
    return chat_history

@router.delete("/{chat_id}")
def delete_chat_history_entry(
    chat_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a specific chat history entry
    """
    success = chat_history_service.delete_chat_history(
        db=db,
        chat_id=chat_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Chat history entry not found")
    
    return {"message": "Chat history entry deleted successfully"}

@router.delete("/")
def clear_chat_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Clear all chat history for the authenticated user
    """
    deleted_count = chat_history_service.clear_chat_history_for_user(
        db=db,
        user_id=current_user.id
    )
    
    return {"message": f"Cleared {deleted_count} chat history entries"} 