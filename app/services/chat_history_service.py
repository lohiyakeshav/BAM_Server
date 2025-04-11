from sqlalchemy.orm import Session
from typing import Optional, List
import json
from app.database.models import ChatHistory, User
from app.models.schemas import ChatResponse

def save_chat_history(
    db: Session,
    query: str,
    response: str or ChatResponse,
    user_id: Optional[int] = None
) -> ChatHistory:
    """
    Save a chat interaction to the database
    
    Args:
        db: Database session
        query: User's question
        response: AI's response (either a string or ChatResponse object)
        user_id: Optional user ID if the user is authenticated
        
    Returns:
        The created ChatHistory object
    """
    # Convert response to JSON if it's a ChatResponse object
    if isinstance(response, ChatResponse):
        response_json = {
            "answer": response.answer,
            "recommendations": response.recommendations,
            "supporting_data": response.supporting_data,
            "sources": response.sources,
            "timestamp": response.timestamp.isoformat() if response.timestamp else None
        }
        response_str = json.dumps(response_json)
    elif isinstance(response, dict):
        response_str = json.dumps(response)
    elif not isinstance(response, str):
        # Attempt to convert any other object type to string for safety
        response_str = str(response)
    else:
        # Check if the string is already JSON
        try:
            # Validate by parsing and re-serializing
            json.loads(response)
            response_str = response
        except json.JSONDecodeError:
            # If not valid JSON, convert to JSON string
            response_str = json.dumps({"answer": response})
    
    chat_entry = ChatHistory(
        query=query,
        response=response_str,
        user_id=user_id
    )
    
    db.add(chat_entry)
    db.commit()
    db.refresh(chat_entry)
    
    return chat_entry

def get_chat_history_for_user(
    db: Session,
    user_id: int,
    limit: int = 50,
    skip: int = 0,
    parse_json: bool = True
) -> List[ChatHistory]:
    """
    Retrieve chat history for a specific user
    
    Args:
        db: Database session
        user_id: ID of the user
        limit: Maximum number of records to return
        skip: Number of records to skip (for pagination)
        parse_json: Whether to parse the JSON response (default: True)
        
    Returns:
        List of ChatHistory objects
    """
    chat_history = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id
    ).order_by(
        ChatHistory.timestamp.desc()
    ).offset(skip).limit(limit).all()
    
    if parse_json:
        for entry in chat_history:
            try:
                entry.parsed_response = json.loads(entry.response)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, provide a fallback format
                entry.parsed_response = {"answer": entry.response}
    
    return chat_history

def delete_chat_history(
    db: Session,
    chat_id: int,
    user_id: int
) -> bool:
    """
    Delete a specific chat history entry
    
    Args:
        db: Database session
        chat_id: ID of the chat entry to delete
        user_id: ID of the user (for authorization)
        
    Returns:
        True if deleted successfully, False otherwise
    """
    chat_entry = db.query(ChatHistory).filter(
        ChatHistory.id == chat_id,
        ChatHistory.user_id == user_id
    ).first()
    
    if not chat_entry:
        return False
    
    db.delete(chat_entry)
    db.commit()
    
    return True

def clear_chat_history_for_user(
    db: Session,
    user_id: int
) -> int:
    """
    Clear all chat history for a specific user
    
    Args:
        db: Database session
        user_id: ID of the user
        
    Returns:
        Number of deleted entries
    """
    deleted_count = db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id
    ).delete()
    
    db.commit()
    
    return deleted_count 