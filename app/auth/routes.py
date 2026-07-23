import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query, status

from app.database import get_supabase_client
from app.email.sender import send_verification_email, send_password_reset_email
from app.auth.models import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse
)
from app.auth.middleware import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_email_action_token,
    decode_token,
    get_current_user
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def register_user(request: UserRegisterRequest):
    """
    Registers a new user account, hashes password with bcrypt, inserts user record,
    and sends a verification link via Resend.
    """
    client = get_supabase_client()
    email_clean = request.email.strip().lower()
    
    try:
        # Check existing user
        existing_query = client.table("users").select("id").eq("email", email_clean).execute()
        if existing_query.data:
            raise HTTPException(status_code=400, detail="User with this email already exists")
            
        hashed_pwd = hash_password(request.password)
        new_user_data = {
            "email": email_clean,
            "name": request.name.strip(),
            "role": "analyst",
            "password_hash": hashed_pwd,
            "email_verified": False
        }
        
        insert_query = client.table("users").insert(new_user_data).execute()
        if not insert_query.data:
            raise HTTPException(status_code=500, detail="Failed to create user record")
            
        user = insert_query.data[0]
        
        # Issue verification token & send email
        verification_token = create_email_action_token(email_clean, "verify_email")
        await send_verification_email(
            to_email=email_clean,
            name=request.name.strip(),
            token=verification_token
        )
        
        return MessageResponse(message="Check your email to complete verification")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@router.post("/login", response_model=TokenResponse)
async def login_user(request: UserLoginRequest):
    """
    Authenticates user credentials, verifies bcrypt hash, and issues JWT access token (15m)
    and refresh token (30d) with database logging.
    """
    client = get_supabase_client()
    email_clean = request.email.strip().lower()
    
    try:
        user_query = client.table("users").select("*").eq("email", email_clean).execute()
        if not user_query.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        user = user_query.data[0]
        
        if not verify_password(request.password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
        # Issue tokens
        access_token = create_access_token(data={"sub": str(user["id"]), "email": user["email"], "role": user.get("role", "analyst")})
        raw_refresh_token, jti, expires_at = create_refresh_token(user["id"])
        
        # Save refresh token hash in database
        token_hash = hash_password(jti)
        client.table("refresh_tokens").insert({
            "user_id": user["id"],
            "token_hash": token_hash,
            "expires_at": expires_at.isoformat()
        }).execute()
        
        user_resp = UserResponse(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user.get("role", "analyst"),
            email_verified=user.get("email_verified", False),
            created_at=user.get("created_at")
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="bearer",
            user=user_resp
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

@router.post("/logout", response_model=MessageResponse)
async def logout_user(request: RefreshTokenRequest):
    """
    Revokes the provided refresh token in the database.
    """
    client = get_supabase_client()
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") == "refresh":
            user_id = payload.get("sub")
            if user_id:
                # Mark refresh tokens as revoked for user
                client.table("refresh_tokens").update({
                    "revoked_at": datetime.now(timezone.utc).isoformat()
                }).eq("user_id", user_id).execute()
        return MessageResponse(message="Logged out")
    except Exception as e:
        logger.warning(f"Logout cleanup warning: {e}")
        return MessageResponse(message="Logged out")

@router.post("/refresh", response_model=TokenResponse)
async def refresh_tokens(request: RefreshTokenRequest):
    """
    Validates refresh token, executes token rotation (invalidates old, issues new pair).
    """
    client = get_supabase_client()
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
            
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
            
        # Verify user active in DB
        user_query = client.table("users").select("*").eq("id", user_id).execute()
        if not user_query.data:
            raise HTTPException(status_code=401, detail="User not found")
        user = user_query.data[0]
        
        # Check active refresh token in DB
        rt_query = (
            client.table("refresh_tokens")
            .select("*")
            .eq("user_id", user_id)
            .is_("revoked_at", "null")
            .execute()
        )
        if not rt_query.data:
            raise HTTPException(status_code=401, detail="Refresh token revoked or expired")
            
        # Revoke old tokens (token rotation)
        client.table("refresh_tokens").update({
            "revoked_at": datetime.now(timezone.utc).isoformat()
        }).eq("user_id", user_id).execute()
        
        # Issue new token pair
        new_access_token = create_access_token(data={"sub": str(user["id"]), "email": user["email"], "role": user.get("role", "analyst")})
        new_raw_refresh_token, new_jti, new_expires_at = create_refresh_token(user["id"])
        
        client.table("refresh_tokens").insert({
            "user_id": user["id"],
            "token_hash": hash_password(new_jti),
            "expires_at": new_expires_at.isoformat()
        }).execute()
        
        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_raw_refresh_token,
            token_type="bearer"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing tokens: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Token refresh error: {str(e)}")

@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(token: str = Query(...)):
    """
    Validates token from email link and updates email_verified=true.
    """
    client = get_supabase_client()
    try:
        payload = decode_token(token)
        if payload.get("action") != "verify_email":
            raise HTTPException(status_code=400, detail="Invalid verification token")
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token payload")
            
        # Update user record
        client.table("users").update({"email_verified": True}).eq("email", email).execute()
        return MessageResponse(message="Email verified")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify email")

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Generates password reset token and emails link via Resend.
    """
    client = get_supabase_client()
    email_clean = request.email.strip().lower()
    
    try:
        user_query = client.table("users").select("id").eq("email", email_clean).execute()
        if user_query.data:
            reset_token = create_email_action_token(email_clean, "reset_password")
            await send_password_reset_email(email_clean, reset_token)
        # Always return success message to prevent user enumeration
        return MessageResponse(message="Check your email")
    except Exception as e:
        logger.error(f"Error handling forgot password: {e}")
        return MessageResponse(message="Check your email")

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Validates password reset token and updates user password in database.
    """
    client = get_supabase_client()
    try:
        payload = decode_token(request.token)
        if payload.get("action") != "reset_password":
            raise HTTPException(status_code=400, detail="Invalid password reset token")
            
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token payload")
            
        hashed_new_pwd = hash_password(request.new_password)
        client.table("users").update({"password_hash": hashed_new_pwd}).eq("email", email).execute()
        return MessageResponse(message="Password updated")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Protected route requiring valid Bearer JWT. Returns current user details.
    """
    return UserResponse(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user.get("role", "analyst"),
        email_verified=current_user.get("email_verified", False),
        created_at=current_user.get("created_at")
    )
