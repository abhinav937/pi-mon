#!/usr/bin/env python3
"""
Pi Monitor - WebAuthn Test Suite
Comprehensive testing of passkey implementation for x86 development
"""

import os
import sys
import json
import base64
import hashlib
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

class TestWebAuthnManager(unittest.TestCase):
    """Test WebAuthn Manager functionality"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'WEBAUTHN_RP_ID': 'test.localhost',
            'WEBAUTHN_ORIGIN': 'http://test.localhost',
            'JWT_SECRET': 'test-jwt-secret-123'
        })
        self.env_patcher.start()
        
        # Mock config
        self.config_patcher = patch('webauthn_manager.config')
        self.mock_config = self.config_patcher.start()
        self.mock_config.get.return_value = None
        
        # Mock auth database
        self.db_patcher = patch('webauthn_manager.AuthDatabase')
        self.mock_db_class = self.db_patcher.start()
        self.mock_db = Mock()
        self.mock_db_class.return_value = self.mock_db
        
        # Mock webauthn library
        self.webauthn_patcher = patch('webauthn_manager.WEBAUTHN_AVAILABLE', True)
        self.webauthn_patcher.start()
        
        # Mock webauthn functions
        self.webauthn_funcs_patcher = patch.multiple(
            'webauthn_manager',
            generate_registration_options=Mock(),
            verify_registration_response=Mock(),
            generate_authentication_options=Mock(),
            verify_authentication_response=Mock()
        )
        self.webauthn_funcs_patcher.start()
        
        # Mock webauthn structs
        self.structs_patcher = patch.multiple(
            'webauthn_manager',
            AuthenticatorSelectionCriteria=Mock(),
            UserVerificationRequirement=Mock(),
            RegistrationCredential=Mock(),
            AuthenticationCredential=Mock(),
            PublicKeyCredentialDescriptor=Mock(),
            AuthenticatorTransport=Mock(),
            COSEAlgorithmIdentifier=Mock()
        )
        self.structs_patcher.start()
        
        # Import after mocking
        from webauthn_manager import WebAuthnManager
        self.webauthn_manager = WebAuthnManager()
        
    def tearDown(self):
        """Clean up test environment"""
        # Remove temporary database
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
        
        # Stop all patches
        self.env_patcher.stop()
        self.config_patcher.stop()
        self.db_patcher.stop()
        self.webauthn_funcs_patcher.stop()
        self.structs_patcher.stop()
        self.webauthn_patcher.stop()
    
    def test_initialization(self):
        """Test WebAuthn manager initialization"""
        self.assertEqual(self.webauthn_manager.rp_id, 'test.localhost')
        self.assertEqual(self.webauthn_manager.origin, 'http://test.localhost')
        self.assertEqual(self.webauthn_manager.rp_name, 'Pi Monitor')
        self.assertIsNotNone(self.webauthn_manager.jwt_secret)
    
    def test_rp_id_from_environment(self):
        """Test RP ID extraction from environment"""
        with patch.dict(os.environ, {'WEBAUTHN_RP_ID': 'custom.domain.com'}):
            manager = WebAuthnManager()
            self.assertEqual(manager.rp_id, 'custom.domain.com')
    
    def test_rp_id_from_config(self):
        """Test RP ID extraction from config"""
        self.mock_config.get.side_effect = lambda key: {
            'deployment_defaults.domain': 'config.domain.com'
        }.get(key)
        
        manager = WebAuthnManager()
        self.assertEqual(manager.rp_id, 'config.domain.com')
    
    def test_origin_from_environment(self):
        """Test origin extraction from environment"""
        with patch.dict(os.environ, {'WEBAUTHN_ORIGIN': 'https://custom.origin.com'}):
            manager = WebAuthnManager()
            self.assertEqual(manager.origin, 'https://custom.origin.com')
    
    def test_origin_from_config(self):
        """Test origin extraction from config"""
        self.mock_config.get.side_effect = lambda key: {
            'urls.production.api_base': 'https://config.origin.com'
        }.get(key)
        
        manager = WebAuthnManager()
        self.assertEqual(manager.origin, 'https://config.origin.com')
    
    def test_jwt_token_generation(self):
        """Test JWT token generation and verification"""
        user_id = "test-user-123"
        token = self.webauthn_manager.generate_jwt_token(user_id, expires_hours=1)
        
        # Verify token
        payload = self.webauthn_manager.verify_jwt_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_id'], user_id)
        self.assertEqual(payload['iss'], 'pi-monitor')
    
    def test_jwt_token_expiration(self):
        """Test JWT token expiration"""
        user_id = "test-user-123"
        token = self.webauthn_manager.generate_jwt_token(user_id, expires_hours=0)
        
        # Token should be expired
        payload = self.webauthn_manager.verify_jwt_token(token)
        self.assertIsNone(payload)
    
    def test_base64_conversions(self):
        """Test base64 and base64url conversions"""
        test_data = b"Hello, WebAuthn!"
        
        # Test base64 to base64url
        base64url = self.webauthn_manager._base64_to_base64url(test_data)
        self.assertIsInstance(base64url, str)
        self.assertNotIn('+', base64url)
        self.assertNotIn('/', base64url)
        self.assertNotIn('=', base64url)
        
        # Test base64url to base64
        base64_str = self.webauthn_manager._base64url_to_base64(base64url)
        decoded_data = base64.b64decode(base64_str)
        self.assertEqual(decoded_data, test_data)
    
    def test_user_creation(self):
        """Test user creation and retrieval"""
        username = "testuser"
        user_id = "test-user-123"
        
        # Mock database responses
        self.mock_db.get_user_by_username.return_value = None
        self.mock_db.create_user.return_value = user_id
        
        result = self.webauthn_manager.create_user_if_not_exists(username)
        self.assertEqual(result, user_id)
        
        # Test existing user
        self.mock_db.get_user_by_username.return_value = {'id': user_id, 'username': username}
        result = self.webauthn_manager.create_user_if_not_exists(username)
        self.assertEqual(result, user_id)
    
    def test_registration_options_generation(self):
        """Test registration options generation"""
        username = "testuser"
        user_id = "test-user-123"
        
        # Mock database responses
        self.mock_db.get_user_by_username.return_value = None
        self.mock_db.create_user.return_value = user_id
        self.mock_db.get_user_credentials.return_value = []
        
        # Mock webauthn library response
        mock_options = Mock()
        mock_options.challenge = b"test-challenge"
        mock_options.rp.name = "Test RP"
        mock_options.rp.id = "test.localhost"
        mock_options.user.id = b"test-user-id"
        mock_options.user.name = username
        mock_options.user.display_name = username
        mock_options.pub_key_cred_params = [Mock(alg=Mock(alg=-7))]
        mock_options.timeout = 60000
        mock_options.exclude_credentials = []
        mock_options.authenticator_selection.user_verification.value = "preferred"
        
        from webauthn_manager import generate_registration_options
        generate_registration_options.return_value = mock_options
        
        # Mock challenge storage
        self.mock_db.store_challenge.return_value = True
        
        result = self.webauthn_manager.generate_registration_options(username)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['user_id'], user_id)
        self.assertIn('options', result)
        self.assertEqual(result['options']['rp']['id'], 'test.localhost')
    
    def test_registration_verification(self):
        """Test registration verification"""
        user_id = "test-user-123"
        credential = {
            'id': 'test-credential-id',
            'rawId': 'dGVzdC1yYXctaWQ=',
            'response': {
                'attestationObject': 'dGVzdC1hdHRlc3RhdGlvbi1vYmplY3Q=',
                'clientDataJSON': 'dGVzdC1jbGllbnQtZGF0YS1qc29u'
            },
            'type': 'public-key'
        }
        device_name = "Test Device"
        
        # Mock challenge retrieval
        self.mock_db.get_challenge.return_value = {
            'challenge': base64.b64encode(b"test-challenge").decode('utf-8')
        }
        
        # Mock webauthn verification
        mock_verification = Mock()
        mock_verification.verified = True
        mock_verification.credential_public_key = b"test-public-key"
        
        from webauthn_manager import verify_registration_response
        verify_registration_response.return_value = mock_verification
        
        # Mock credential storage
        self.mock_db.store_credential.return_value = "cred-123"
        
        # Mock challenge removal
        self.mock_db.delete_challenge.return_value = True
        
        result = self.webauthn_manager.verify_registration(user_id, credential, device_name)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['credential_id'], "cred-123")
    
    def test_authentication_options_generation(self):
        """Test authentication options generation"""
        username = "testuser"
        user_id = "test-user-123"
        
        # Mock user lookup
        self.mock_db.get_user_by_username.return_value = {'id': user_id, 'username': username}
        
        # Mock credentials
        self.mock_db.get_user_credentials.return_value = [{
            'credential_id': 'dGVzdC1jcmVkZW50aWFsLWlk'
        }]
        
        # Mock webauthn library response
        mock_options = Mock()
        mock_options.challenge = b"test-challenge"
        mock_options.timeout = 60000
        mock_options.rp_id = "test.localhost"
        mock_options.allow_credentials = []
        mock_options.user_verification.value = "preferred"
        
        from webauthn_manager import generate_authentication_options
        generate_authentication_options.return_value = mock_options
        
        # Mock challenge storage
        self.mock_db.store_challenge.return_value = True
        
        result = self.webauthn_manager.generate_authentication_options(username)
        
        self.assertTrue(result['success'])
        self.assertIn('options', result)
        self.assertIn('challenge_key', result)
    
    def test_authentication_verification(self):
        """Test authentication verification"""
        credential = {
            'id': 'test-credential-id',
            'rawId': 'dGVzdC1yYXctaWQ=',
            'response': {
                'authenticatorData': 'dGVzdC1hdXRoZW50aWNhdG9yLWRhdGE=',
                'clientDataJSON': 'dGVzdC1jbGllbnQtZGF0YS1qc29u',
                'signature': 'dGVzdC1zaWduYXR1cmU='
            },
            'type': 'public-key'
        }
        challenge_key = "test-challenge-key"
        
        # Mock challenge retrieval
        self.mock_db.get_challenge.return_value = {
            'challenge': base64.b64encode(b"test-challenge").decode('utf-8')
        }
        
        # Mock credential lookup
        self.mock_db.get_credential_by_id.return_value = {
            'user_id': 'test-user-123',
            'public_key': base64.b64encode(b"test-public-key").decode('utf-8'),
            'sign_count': 0
        }
        
        # Mock user lookup
        self.mock_db.get_user.return_value = {
            'id': 'test-user-123',
            'username': 'testuser',
            'display_name': 'Test User'
        }
        
        # Mock webauthn verification
        mock_verification = Mock()
        mock_verification.verified = True
        mock_verification.new_sign_count = 1
        
        from webauthn_manager import verify_authentication_response
        verify_authentication_response.return_value = mock_verification
        
        # Mock database updates
        self.mock_db.update_credential_usage.return_value = None
        self.mock_db.update_last_login.return_value = None
        self.mock_db.create_session.return_value = "session-123"
        self.mock_db.delete_challenge.return_value = True
        
        result = self.webauthn_manager.verify_authentication(
            credential, challenge_key, {'user_agent': 'Test Browser'}
        )
        
        self.assertTrue(result['success'])
        self.assertIn('token', result)
        self.assertIn('user', result)
    
    def test_logout(self):
        """Test user logout"""
        token = "test-jwt-token"
        
        # Mock session invalidation
        self.mock_db.invalidate_session.return_value = None
        
        result = self.webauthn_manager.logout(token)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['message'], 'Logged out successfully')
    
    def test_user_info_retrieval(self):
        """Test user info retrieval from token"""
        token = "test-jwt-token"
        user_id = "test-user-123"
        
        # Mock JWT verification
        with patch.object(self.webauthn_manager, 'verify_jwt_token') as mock_verify:
            mock_verify.return_value = {'user_id': user_id}
            
            # Mock user lookup
            self.mock_db.get_user.return_value = {
                'id': user_id,
                'username': 'testuser',
                'display_name': 'Test User'
            }
            
            # Mock credentials count
            self.mock_db.get_user_credentials.return_value = [{'id': 'cred1'}, {'id': 'cred2'}]
            
            result = self.webauthn_manager.get_user_info(token)
            
            self.assertIsNotNone(result)
            self.assertEqual(result['username'], 'testuser')
            self.assertEqual(result['credentials'], 2)
    
    def test_challenge_management(self):
        """Test challenge storage and retrieval"""
        challenge_key = "test-challenge"
        challenge_data = b"test-challenge-data"
        user_id = "test-user-123"
        
        # Mock challenge storage
        self.mock_db.store_challenge.return_value = True
        
        # Test challenge storage
        result = self.webauthn_manager._store_challenge(
            challenge_key, challenge_data, user_id, 'registration'
        )
        self.assertTrue(result)
        
        # Mock challenge retrieval
        self.mock_db.get_challenge.return_value = {
            'challenge': base64.b64encode(challenge_data).decode('utf-8')
        }
        
        # Test challenge retrieval
        retrieved_challenge = self.webauthn_manager._get_challenge(challenge_key)
        self.assertEqual(retrieved_challenge, challenge_data)
        
        # Mock challenge removal
        self.mock_db.delete_challenge.return_value = True
        
        # Test challenge removal
        self.webauthn_manager._remove_challenge(challenge_key)
    
    def test_error_handling(self):
        """Test error handling in various scenarios"""
        # Test registration with invalid user
        self.mock_db.create_user.return_value = None
        
        result = self.webauthn_manager.generate_registration_options("invaliduser")
        self.assertIn('error', result)
        
        # Test authentication with missing challenge
        self.mock_db.get_challenge.return_value = None
        
        result = self.webauthn_manager.verify_authentication(
            {'id': 'test'}, "missing-challenge", {}
        )
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Challenge not found or expired')
        
        # Test authentication with missing credential
        self.mock_db.get_challenge.return_value = {
            'challenge': base64.b64encode(b"test").decode('utf-8')
        }
        self.mock_db.get_credential_by_id.return_value = None
        
        result = self.webauthn_manager.verify_authentication(
            {'id': 'test'}, "test-challenge", {}
        )
        self.assertIn('error', result)
        self.assertEqual(result['error'], 'Credential not found')
    
    def test_webauthn_library_unavailable(self):
        """Test behavior when WebAuthn library is not available"""
        # Stop the webauthn patch
        self.webauthn_patcher.stop()
        
        # Mock the import error
        with patch('webauthn_manager.WEBAUTHN_AVAILABLE', False):
            with self.assertRaises(ImportError):
                from webauthn_manager import WebAuthnManager
                WebAuthnManager()
        
        # Restart the patch
        self.webauthn_patcher.start()


class TestWebAuthnIntegration(unittest.TestCase):
    """Integration tests for WebAuthn functionality"""
    
    def setUp(self):
        """Set up integration test environment"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Set up environment
        os.environ['WEBAUTHN_RP_ID'] = 'localhost'
        os.environ['WEBAUTHN_ORIGIN'] = 'http://localhost'
        os.environ['JWT_SECRET'] = 'integration-test-secret'
    
    def tearDown(self):
        """Clean up integration test environment"""
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == '1',
        "Integration tests require INTEGRATION_TESTS=1 environment variable"
    )
    def test_full_registration_flow(self):
        """Test complete registration flow with real WebAuthn library"""
        # This test requires the actual webauthn library to be installed
        # and INTEGRATION_TESTS=1 environment variable
        pass
    
    @unittest.skipUnless(
        os.environ.get('INTEGRATION_TESTS') == '1',
        "Integration tests require INTEGRATION_TESTS=1 environment variable"
    )
    def test_full_authentication_flow(self):
        """Test complete authentication flow with real WebAuthn library"""
        # This test requires the actual webauthn library to be installed
        # and INTEGRATION_TESTS=1 environment variable
        pass


def run_webauthn_tests():
    """Run WebAuthn tests with detailed output"""
    print("🧪 Running WebAuthn Test Suite")
    print("=" * 50)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestWebAuthnManager)
    
    # Add integration tests if requested
    if os.environ.get('INTEGRATION_TESTS') == '1':
        suite.addTests(loader.loadTestsFromTestCase(TestWebAuthnIntegration))
        print("🔗 Including integration tests")
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 50)
    print(f"📊 Test Results: {result.testsRun} tests run")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"⚠️  Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print("\n⚠️  Errors:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_webauthn_tests()
    sys.exit(0 if success else 1)
