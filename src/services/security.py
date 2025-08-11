"""
Enterprise Security Services
Johns Hopkins Healthcare Security Standards
"""
import hashlib
import secrets
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from cryptography.fernet import Fernet
import logging
from sqlalchemy.orm import Session

from src.config.settings import get_settings
from src.models.auth import User, AuditLog, SecurityEvent

logger = logging.getLogger(__name__)
settings = get_settings()

class SecurityManager:
    """Enterprise security management"""
    
    def __init__(self):
        self.encryption_key = settings.encryption_key.encode()
        self.fernet = Fernet(self.encryption_key)
        self.jwt_secret = settings.jwt_secret
        self.password_policy = PasswordPolicy()
        self.audit_logger = AuditLogger()
    
    def encrypt_pii(self, data: str) -> str:
        """Encrypt personally identifiable information"""
        if not data:
            return data
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt_pii(self, encrypted_data: str) -> str:
        """Decrypt personally identifiable information"""
        if not encrypted_data:
            return encrypted_data
        try:
            return self.fernet.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            return "[DECRYPTION_ERROR]"
    
    def hash_password(self, password: str, salt: Optional[str] = None) -> tuple[str, str]:
        """Hash password with salt using PBKDF2"""
        if not salt:
            salt = secrets.token_hex(32)
        
        # Use PBKDF2 with SHA-256 (NIST recommended)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 100,000 iterations
        )
        
        return password_hash.hex(), salt
    
    def verify_password(self, password: str, hashed_password: str, salt: str) -> bool:
        """Verify password against hash"""
        password_hash, _ = self.hash_password(password, salt)
        return secrets.compare_digest(password_hash, hashed_password)
    
    def create_access_token(self, user_id: str, permissions: List[str]) -> str:
        """Create JWT access token with permissions"""
        payload = {
            "user_id": user_id,
            "permissions": permissions,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=8),
            "iss": "medflow-hms",
            "aud": "medflow-api"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=["HS256"],
                audience="medflow-api",
                issuer="medflow-hms"
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {str(e)}")
            return None
    
    async def log_security_event(self, event_type: str, user_id: str, details: Dict[str, Any], db: Session):
        """Log security events for monitoring"""
        security_event = SecurityEvent(
            event_type=event_type,
            user_id=user_id,
            details=details,
            ip_address=details.get("ip_address"),
            user_agent=details.get("user_agent"),
            timestamp=datetime.utcnow()
        )
        
        db.add(security_event)
        db.commit()
        
        # Check for suspicious patterns
        await self._analyze_security_patterns(user_id, event_type, db)
    
    async def _analyze_security_patterns(self, user_id: str, event_type: str, db: Session):
        """Analyze security events for suspicious patterns"""
        # Check for multiple failed logins
        if event_type == "login_failed":
            recent_failures = db.query(SecurityEvent).filter(
                SecurityEvent.user_id == user_id,
                SecurityEvent.event_type == "login_failed",
                SecurityEvent.timestamp >= datetime.utcnow() - timedelta(minutes=15)
            ).count()
            
            if recent_failures >= 5:
                await self._trigger_security_alert("multiple_failed_logins", user_id, db)
        
        # Check for unusual access patterns
        if event_type == "data_access":
            recent_access = db.query(SecurityEvent).filter(
                SecurityEvent.user_id == user_id,
                SecurityEvent.event_type == "data_access",
                SecurityEvent.timestamp >= datetime.utcnow() - timedelta(hours=1)
            ).count()
            
            if recent_access >= 100:  # Unusual volume
                await self._trigger_security_alert("unusual_access_pattern", user_id, db)
    
    async def _trigger_security_alert(self, alert_type: str, user_id: str, db: Session):
        """Trigger security alert and response"""
        logger.critical(f"SECURITY ALERT: {alert_type} for user {user_id}")
        
        # Could integrate with SIEM systems, send notifications, etc.
        # For now, log the alert
        security_event = SecurityEvent(
            event_type="security_alert",
            user_id=user_id,
            details={"alert_type": alert_type},
            timestamp=datetime.utcnow()
        )
        
        db.add(security_event)
        db.commit()

class PasswordPolicy:
    """Enterprise password policy enforcement"""
    
    def __init__(self):
        self.min_length = 12
        self.require_uppercase = True
        self.require_lowercase = True
        self.require_numbers = True
        self.require_special = True
        self.max_age_days = 90
        self.history_count = 12
    
    def validate_password(self, password: str) -> tuple[bool, List[str]]:
        """Validate password against policy"""
        errors = []
        
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        
        if self.require_uppercase and not any(c.isupper() for c in password):
            errors.append("Password must contain uppercase letters")
        
        if self.require_lowercase and not any(c.islower() for c in password):
            errors.append("Password must contain lowercase letters")
        
        if self.require_numbers and not any(c.isdigit() for c in password):
            errors.append("Password must contain numbers")
        
        if self.require_special and not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain special characters")
        
        # Check for common patterns
        if self._contains_common_patterns(password):
            errors.append("Password contains common patterns")
        
        return len(errors) == 0, errors
    
    def _contains_common_patterns(self, password: str) -> bool:
        """Check for common password patterns"""
        common_patterns = [
            "123456", "password", "qwerty", "admin", "letmein",
            "welcome", "monkey", "dragon", "master", "shadow"
        ]
        
        password_lower = password.lower()
        return any(pattern in password_lower for pattern in common_patterns)

class AuditLogger:
    """Comprehensive audit logging for compliance"""
    
    def __init__(self):
        self.logger = logging.getLogger("audit")
    
    async def log_data_access(self, user_id: str, resource_type: str, resource_id: str, 
                            action: str, db: Session, **kwargs):
        """Log data access for HIPAA compliance"""
        audit_entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            timestamp=datetime.utcnow(),
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
            session_id=kwargs.get("session_id")
        )
        
        db.add(audit_entry)
        db.commit()
        
        # Also log to external audit system
        self.logger.info(
            f"AUDIT: User {user_id} performed {action} on {resource_type} {resource_id}",
            extra={
                "user_id": user_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs
            }
        )
    
    async def log_system_event(self, event_type: str, details: Dict[str, Any], db: Session):
        """Log system events"""
        audit_entry = AuditLog(
            action=event_type,
            resource_type="system",
            details=details,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_entry)
        db.commit()

class AccessControl:
    """Role-based access control with fine-grained permissions"""
    
    def __init__(self):
        self.permissions = self._load_permission_matrix()
    
    def _load_permission_matrix(self) -> Dict[str, List[str]]:
        """Load role-based permission matrix"""
        return {
            "physician": [
                "patient:read", "patient:write", "patient:create",
                "encounter:read", "encounter:write", "encounter:create",
                "diagnosis:read", "diagnosis:write", "diagnosis:create",
                "order:read", "order:write", "order:create",
                "medication:prescribe", "lab:order", "imaging:order"
            ],
            "nurse": [
                "patient:read", "patient:write",
                "encounter:read", "encounter:write",
                "vitals:record", "medication:administer",
                "order:read", "order:update_status"
            ],
            "pharmacist": [
                "patient:read", "medication:read", "medication:verify",
                "medication:dispense", "allergy:read", "order:read"
            ],
            "lab_tech": [
                "patient:read", "order:read", "lab:read", "lab:write",
                "lab:result_entry", "specimen:track"
            ],
            "receptionist": [
                "patient:read", "patient:create", "patient:update_demographics",
                "appointment:read", "appointment:create", "appointment:update",
                "insurance:verify"
            ],
            "admin": [
                "user:read", "user:create", "user:update", "user:delete",
                "system:configure", "audit:read", "report:generate"
            ]
        }
    
    def check_permission(self, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission"""
        user_permissions = self.permissions.get(user_role, [])
        return required_permission in user_permissions
    
    def get_user_permissions(self, user_role: str) -> List[str]:
        """Get all permissions for user role"""
        return self.permissions.get(user_role, [])

# Global instances
security_manager = SecurityManager()
access_control = AccessControl()
audit_logger = AuditLogger()