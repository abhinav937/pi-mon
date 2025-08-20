#!/usr/bin/env python3
"""
Pi Monitor - WebAuthn Authentication Manager
Handles passkey registration and authentication using WebAuthn
"""

import os
import json
import base64
import hashlib
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import jwt
from urllib.parse import urlparse

try:
    from webauthn import generate_registration_options, verify_registration_response
    from webauthn import generate_authentication_options, verify_authentication_response
    from webauthn.helpers.structs import (
        AuthenticatorSelectionCriteria,
        UserVerificationRequirement,
        RegistrationCredential,
        AuthenticationCredential,
        PublicKeyCredentialDescriptor,
        AuthenticatorTransport
    )
    from webauthn.helpers.cose import COSEAlgorithmIdentifier
    WEBAUTHN_AVAILABLE = True
except ImportError:
    WEBAUTHN_AVAILABLE = False

from auth_database import AuthDatabase
from config import config

logger = logging.getLogger(__name__)

class WebAuthnManager:
    """Manages WebAuthn (passkey) authentication"""
    
    def __init__(self, rp_id: str = None, rp_name: str = "Pi Monitor", origin: str = None):
        if not WEBAUTHN_AVAILABLE:
            raise ImportError("WebAuthn dependencies not installed. Run: pip install webauthn cbor2")
        
        self.rp_id = rp_id or self._get_rp_id()
        self.rp_name = rp_name
        self.origin = origin or self._get_origin()
        self.db = AuthDatabase()
        self.jwt_secret = self._get_jwt_secret()
        
        # Cleanup expired sessions on startup
        self.db.cleanup_expired_sessions()
        
        logger.info(f"WebAuthn Manager initialized - RP ID: {self.rp_id}, Origin: {self.origin}")
    
    def _get_rp_id(self) -> str:
        """Get Relying Party ID from environment or config"""
        rp_id = os.environ.get('WEBAUTHN_RP_ID')
        if rp_id:
            return rp_id

        # Try to get from JSON config (preferred)
        try:
            # Prefer explicit domain
            cfg_domain = config.get('deployment_defaults.domain')
            if isinstance(cfg_domain, str) and cfg_domain.strip():
                return cfg_domain.strip()

            # Fallback to URLs in production config
            prod_backend = config.get('urls.production.backend')
            if isinstance(prod_backend, str) and prod_backend:
                parsed = urlparse(prod_backend)
                if parsed.hostname:
                    return parsed.hostname

            prod_api_base = config.get('urls.production.api_base')
            if isinstance(prod_api_base, str) and prod_api_base:
                parsed = urlparse(prod_api_base)
                if parsed.hostname:
                    return parsed.hostname
        except Exception:
            pass

        # Try to get from current hostname/IP as a last resort
        try:
            import socket
            hostname = socket.getfqdn()
            if hostname and not hostname.startswith('localhost'):
                return hostname
        except Exception:
            pass

        return 'localhost'
    
    def _get_origin(self) -> str:
        """Get origin URL"""
        origin = os.environ.get('WEBAUTHN_ORIGIN')
        if origin:
            return origin

        # Try to get origin from JSON config (preferred)
        try:
            prod_api_base = config.get('urls.production.api_base')
            if isinstance(prod_api_base, str) and prod_api_base.strip():
                return prod_api_base.strip()

            prod_url = config.get('deployment_defaults.production_url')
            if isinstance(prod_url, str) and prod_url.strip():
                return prod_url.strip()
        except Exception:
            pass

        # Default based on RP ID
        if self.rp_id == 'localhost':
            return 'http://localhost'
        return f'https://{self.rp_id}'
    
    def _get_jwt_secret(self) -> str:
        """Get JWT signing secret"""
        secret = os.environ.get('JWT_SECRET')
        if secret:
            return secret
        
        # Generate a secret based on system info for consistency
        try:
            import socket
            import psutil
            system_info = f"{socket.gethostname()}-{psutil.boot_time()}"
            return hashlib.sha256(system_info.encode()).hexdigest()
        except:
            return "pi-monitor-default-jwt-secret-change-in-production"
    
    def generate_jwt_token(self, user_id: str, expires_hours: int = 24) -> str:
        """Generate JWT token for user session"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iat': datetime.utcnow(),
            'iss': 'pi-monitor'
        }
        return jwt.encode(payload, self.jwt_secret, algorithm='HS256')
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if session exists and is valid
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            session = self.db.get_session_by_token(token_hash)
            
            if session and session['is_active']:
                # Update session activity
                self.db.update_session_activity(token_hash)
                return payload
            
            return None
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    def create_user_if_not_exists(self, username: str) -> Optional[str]:
        """Create user if they don't exist, return user_id"""
        user = self.db.get_user_by_username(username)
        if user:
            return user['id']
        
        return self.db.create_user(username)
    
    def _base64url_to_base64(self, base64url: str) -> str:
        """Convert base64url to base64 for decoding"""
        base64_str = base64url.replace('-', '+').replace('_', '/')
        # Add padding if needed
        padding = 4 - (len(base64_str) % 4)
        if padding != 4:
            base64_str += '=' * padding
        return base64_str
    
    def _base64_to_base64url(self, data: bytes) -> str:
        """Convert bytes to base64url encoding"""
        return base64.b64encode(data).decode('utf-8').replace('+', '-').replace('/', '_').replace('=', '')
    
    def generate_registration_options(self, username: str) -> Dict[str, Any]:
        """Generate WebAuthn registration options"""
        try:
            # Get or create user
            user_id = self.create_user_if_not_exists(username)
            if not user_id:
                raise Exception("Failed to create/get user")
            
            # Get existing credentials to exclude them
            existing_creds = self.db.get_user_credentials(user_id)
            exclude_credentials = []
            
            for cred in existing_creds:
                # Convert stored base64url credential ID back to bytes
                cred_id_base64 = self._base64url_to_base64(cred['credential_id'])
                
                exclude_credentials.append(
                    PublicKeyCredentialDescriptor(
                        id=base64.b64decode(cred_id_base64),
                        transports=[
                            AuthenticatorTransport.USB,
                            AuthenticatorTransport.NFC,
                            AuthenticatorTransport.BLE,
                            AuthenticatorTransport.INTERNAL,
                            AuthenticatorTransport.HYBRID,
                        ]
                    )
                )
            
            options = generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=user_id.encode('utf-8'),
                user_name=username,
                user_display_name=username,
                exclude_credentials=exclude_credentials,
                authenticator_selection=AuthenticatorSelectionCriteria(
                    user_verification=UserVerificationRequirement.PREFERRED,
                ),
                supported_pub_key_algs=[
                    COSEAlgorithmIdentifier.ECDSA_SHA_256,
                    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
                ],
            )
            
            # Store challenge for verification
            challenge_key = f"reg_challenge_{user_id}"
            self._store_challenge(challenge_key, options.challenge)
            
            return {
                'success': True,
                'options': {
                    'challenge': self._base64_to_base64url(options.challenge),
                    'rp': {
                        'name': options.rp.name,
                        'id': options.rp.id,
                    },
                    'user': {
                        'id': self._base64_to_base64url(options.user.id),
                        'name': options.user.name,
                        'displayName': options.user.display_name,
                    },
                    'pubKeyCredParams': [
                        {'alg': alg.alg, 'type': 'public-key'} 
                        for alg in options.pub_key_cred_params
                    ],
                    'timeout': options.timeout,
                    'excludeCredentials': [
                        {
                            'id': self._base64_to_base64url(cred.id),
                            'type': 'public-key',
                            'transports': [t.value for t in cred.transports] if cred.transports else []
                        }
                        for cred in options.exclude_credentials
                    ] if options.exclude_credentials else [],
                    'authenticatorSelection': {
                        'userVerification': options.authenticator_selection.user_verification.value
                    }
                },
                'user_id': user_id
            }
        except Exception as e:
            logger.error(f"Failed to generate registration options: {e}")
            return {'error': str(e)}
    
    def verify_registration(self, user_id: str, credential: Dict[str, Any], 
                           device_name: str = None) -> Dict[str, Any]:
        """Verify WebAuthn registration response"""
        try:
            # Get stored challenge
            challenge_key = f"reg_challenge_{user_id}"
            expected_challenge = self._get_challenge(challenge_key)
            if not expected_challenge:
                return {'error': 'Challenge not found or expired'}
            
            # Convert credential data - handle both old and new webauthn library versions
            try:
                # Try new method first (webauthn >= 1.11.0)
                # Convert base64url to base64 for decoding
                raw_id_base64 = self._base64url_to_base64(credential['rawId'])
                
                reg_credential = RegistrationCredential(
                    id=credential['id'],
                    raw_id=base64.b64decode(raw_id_base64),
                    response=credential['response'],
                    type=credential['type']
                )
            except (TypeError, AttributeError):
                # Fallback to old method for compatibility
                reg_credential = RegistrationCredential.parse_raw(json.dumps(credential))
            
            verification = verify_registration_response(
                credential=reg_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
            )
            
            if verification.verified:
                # Store the credential - use base64url encoding for consistency
                credential_id = self._base64_to_base64url(verification.credential_id)
                public_key = base64.b64encode(verification.credential_public_key).decode('utf-8')
                
                cred_id = self.db.store_credential(
                    user_id=user_id,
                    credential_id=credential_id,
                    public_key=public_key,
                    device_name=device_name or "Unknown Device"
                )
                
                if cred_id:
                    # Clean up challenge
                    self._remove_challenge(challenge_key)
                    
                    return {
                        'success': True,
                        'message': 'Registration successful',
                        'credential_id': cred_id
                    }
                else:
                    return {'error': 'Failed to store credential'}
            else:
                return {'error': 'Registration verification failed'}
        
        except Exception as e:
            logger.error(f"Registration verification failed: {e}")
            return {'error': str(e)}
    
    def generate_authentication_options(self, username: str = None) -> Dict[str, Any]:
        """Generate WebAuthn authentication options"""
        try:
            allow_credentials = []
            
            if username:
                # Get user's credentials
                user = self.db.get_user_by_username(username)
                if user:
                    user_creds = self.db.get_user_credentials(user['id'])
                    for cred in user_creds:
                        # Convert stored base64url credential ID back to bytes
                        cred_id_base64 = self._base64url_to_base64(cred['credential_id'])
                        
                        allow_credentials.append(
                            PublicKeyCredentialDescriptor(
                                id=base64.b64decode(cred_id_base64),
                                transports=[
                                    AuthenticatorTransport.USB,
                                    AuthenticatorTransport.NFC,
                                    AuthenticatorTransport.BLE,
                                    AuthenticatorTransport.INTERNAL,
                                    AuthenticatorTransport.HYBRID,
                                ]
                            )
                        )
            
            options = generate_authentication_options(
                rp_id=self.rp_id,
                allow_credentials=allow_credentials if allow_credentials else None,
                user_verification=UserVerificationRequirement.PREFERRED,
            )
            
                            # Store challenge
                challenge_key = f"auth_challenge_{self._base64_to_base64url(options.challenge)[:16]}"
                self._store_challenge(challenge_key, options.challenge)
            
            return {
                'success': True,
                'options': {
                    'challenge': self._base64_to_base64url(options.challenge),
                    'timeout': options.timeout,
                    'rpId': options.rp_id,
                    'allowCredentials': [
                        {
                            'id': self._base64_to_base64url(cred.id),
                            'type': 'public-key',
                            'transports': [t.value for t in cred.transports] if cred.transports else []
                        }
                        for cred in options.allow_credentials
                    ] if options.allow_credentials else [],
                    'userVerification': options.user_verification.value
                },
                'challenge_key': challenge_key
            }
        except Exception as e:
            logger.error(f"Failed to generate authentication options: {e}")
            return {'error': str(e)}
    
    def verify_authentication(self, credential: Dict[str, Any], challenge_key: str,
                             request_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Verify WebAuthn authentication response"""
        try:
            # Get stored challenge
            expected_challenge = self._get_challenge(challenge_key)
            if not expected_challenge:
                return {'error': 'Challenge not found or expired'}
            
            # Convert credential data - handle both old and new webauthn library versions
            try:
                # Try new method first (webauthn >= 1.11.0)
                # Convert base64url to base64 for decoding
                raw_id_base64 = self._base64url_to_base64(credential['rawId'])
                
                auth_credential = AuthenticationCredential(
                    id=credential['id'],
                    raw_id=base64.b64decode(raw_id_base64),
                    response=credential['response'],
                    type=credential['type']
                )
            except (TypeError, AttributeError):
                # Fallback to old method for compatibility
                auth_credential = AuthenticationCredential.parse_raw(json.dumps(credential))
            
            # Get credential from database - convert to base64url for database lookup
            credential_id = self._base64_to_base64url(auth_credential.raw_id)
            stored_cred = self.db.get_credential_by_id(credential_id)
            
            if not stored_cred:
                return {'error': 'Credential not found'}
            
            # Get user info
            user = self.db.get_user(stored_cred['user_id'])
            if not user:
                return {'error': 'User not found'}
            
            verification = verify_authentication_response(
                credential=auth_credential,
                expected_challenge=expected_challenge,
                expected_origin=self.origin,
                expected_rp_id=self.rp_id,
                credential_public_key=base64.b64decode(stored_cred['public_key']),
                credential_current_sign_count=stored_cred['sign_count'],
            )
            
            if verification.verified:
                # Update credential usage
                self.db.update_credential_usage(credential_id, verification.new_sign_count)
                
                # Update user last login
                self.db.update_last_login(user['id'])
                
                # Generate JWT token
                jwt_token = self.generate_jwt_token(user['id'])
                
                # Store session
                token_hash = hashlib.sha256(jwt_token.encode()).hexdigest()
                expires_at = datetime.utcnow() + timedelta(hours=24)
                
                session_id = self.db.create_session(
                    user_id=user['id'],
                    token_hash=token_hash,
                    expires_at=expires_at,
                    user_agent=request_info.get('user_agent') if request_info else None,
                    ip_address=request_info.get('ip_address') if request_info else None
                )
                
                # Clean up challenge
                self._remove_challenge(challenge_key)
                
                return {
                    'success': True,
                    'message': 'Authentication successful',
                    'token': jwt_token,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'display_name': user['display_name']
                    }
                }
            else:
                return {'error': 'Authentication verification failed'}
        
        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            return {'error': str(e)}
    
    def logout(self, token: str) -> Dict[str, Any]:
        """Logout user by invalidating session"""
        try:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            self.db.invalidate_session(token_hash)
            return {'success': True, 'message': 'Logged out successfully'}
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return {'error': str(e)}
    
    def get_user_info(self, token: str) -> Optional[Dict[str, Any]]:
        """Get user info from token"""
        payload = self.verify_jwt_token(token)
        if payload:
            user = self.db.get_user(payload['user_id'])
            if user:
                return {
                    'id': user['id'],
                    'username': user['username'],
                    'display_name': user['display_name'],
                    'credentials': len(self.db.get_user_credentials(user['id']))
                }
        return None
    
    def _store_challenge(self, key: str, challenge: bytes):
        """Store challenge temporarily (in-memory for now)"""
        # For production, consider using Redis or database
        if not hasattr(self, '_challenges'):
            self._challenges = {}
        
        self._challenges[key] = {
            'challenge': challenge,
            'expires': datetime.utcnow() + timedelta(minutes=10)
        }
    
    def _get_challenge(self, key: str) -> Optional[bytes]:
        """Get stored challenge"""
        if not hasattr(self, '_challenges'):
            return None
        
        if key in self._challenges:
            data = self._challenges[key]
            if datetime.utcnow() < data['expires']:
                return data['challenge']
            else:
                del self._challenges[key]
        
        return None
    
    def _remove_challenge(self, key: str):
        """Remove challenge"""
        if hasattr(self, '_challenges') and key in self._challenges:
            del self._challenges[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get authentication statistics"""
        return self.db.get_auth_stats()
