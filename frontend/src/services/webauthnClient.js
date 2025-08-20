/* eslint-disable no-console */
/**
 * WebAuthn Client Service
 * Handles passkey registration and authentication
 */

class WebAuthnClient {
  constructor(baseURL) {
    this.baseURL = baseURL || `http://${window.location.hostname}:5001`;
    this.token = localStorage.getItem('webauthn-token');
  }

  async checkWebAuthnSupport() {
    if (!window.PublicKeyCredential) {
      return {
        supported: false,
        error: 'WebAuthn not supported by this browser'
      };
    }

    try {
      const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
      return {
        supported: true,
        platformAuthenticator: available,
        conditionalMediation: await PublicKeyCredential.isConditionalMediationAvailable?.() || false
      };
    } catch (error) {
      return {
        supported: true,
        platformAuthenticator: false,
        conditionalMediation: false,
        error: error.message
      };
    }
  }

  async getAuthStatus() {
    try {
      const response = await fetch(`${this.baseURL}/api/auth/status`);
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Failed to get auth status:', error);
      return { error: error.message };
    }
  }

  // Convert base64url to ArrayBuffer
  base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const padLength = (4 - base64.length % 4) % 4;
    const padded = base64 + '='.repeat(padLength);
    const binary = atob(padded);
    const buffer = new ArrayBuffer(binary.length);
    const view = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i++) {
      view[i] = binary.charCodeAt(i);
    }
    return buffer;
  }

  // Convert ArrayBuffer to base64url
  bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const base64 = btoa(binary);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
  }

  async startRegistration(username = 'admin', deviceName = null) {
    try {
      // Get registration options from server
      const response = await fetch(`${this.baseURL}/api/auth/webauthn/register/begin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username }),
      });

      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || `Registration failed: ${response.status}`);
      }

      const { options, user_id } = data;

      // Convert base64 strings to ArrayBuffer
      const publicKeyCredentialCreationOptions = {
        ...options,
        challenge: this.base64urlToBuffer(options.challenge),
        user: {
          ...options.user,
          id: this.base64urlToBuffer(options.user.id),
        },
        excludeCredentials: options.excludeCredentials?.map(cred => ({
          ...cred,
          id: this.base64urlToBuffer(cred.id),
        })) || [],
      };

      // Create credential
      const credential = await navigator.credentials.create({
        publicKey: publicKeyCredentialCreationOptions,
      });

      if (!credential) {
        throw new Error('Failed to create credential');
      }

      // Convert credential to JSON format for server
      const credentialJson = {
        id: credential.id,
        rawId: this.bufferToBase64url(credential.rawId),
        response: {
          attestationObject: this.bufferToBase64url(credential.response.attestationObject),
          clientDataJSON: this.bufferToBase64url(credential.response.clientDataJSON),
        },
        type: credential.type,
      };

      // Complete registration on server
      const completeResponse = await fetch(`${this.baseURL}/api/auth/webauthn/register/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id,
          credential: credentialJson,
          device_name: deviceName || this.getDeviceName(),
        }),
      });

      const result = await completeResponse.json();
      if (!completeResponse.ok || result.error) {
        throw new Error(result.error || `Registration completion failed: ${completeResponse.status}`);
      }

      return {
        success: true,
        message: result.message,
        credential_id: result.credential_id,
      };
    } catch (error) {
      console.error('Registration failed:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async startAuthentication(username = null) {
    try {
      // Get authentication options from server
      const response = await fetch(`${this.baseURL}/api/auth/webauthn/authenticate/begin`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username }),
      });

      const data = await response.json();
      if (!response.ok || data.error) {
        throw new Error(data.error || `Authentication failed: ${response.status}`);
      }

      const { options, challenge_key } = data;

      // Convert base64 strings to ArrayBuffer
      const publicKeyCredentialRequestOptions = {
        ...options,
        challenge: this.base64urlToBuffer(options.challenge),
        allowCredentials: options.allowCredentials?.map(cred => ({
          ...cred,
          id: this.base64urlToBuffer(cred.id),
        })) || [],
      };

      // Get credential
      const credential = await navigator.credentials.get({
        publicKey: publicKeyCredentialRequestOptions,
      });

      if (!credential) {
        throw new Error('Failed to get credential');
      }

      // Convert credential to JSON format for server
      const credentialJson = {
        id: credential.id,
        rawId: this.bufferToBase64url(credential.rawId),
        response: {
          authenticatorData: this.bufferToBase64url(credential.response.authenticatorData),
          clientDataJSON: this.bufferToBase64url(credential.response.clientDataJSON),
          signature: this.bufferToBase64url(credential.response.signature),
        },
        type: credential.type,
      };

      // Complete authentication on server
      const completeResponse = await fetch(`${this.baseURL}/api/auth/webauthn/authenticate/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          credential: credentialJson,
          challenge_key,
        }),
      });

      const result = await completeResponse.json();
      if (!completeResponse.ok || result.error) {
        throw new Error(result.error || `Authentication completion failed: ${completeResponse.status}`);
      }

      // Store token
      if (result.token) {
        this.token = result.token;
        localStorage.setItem('webauthn-token', result.token);
      }

      return {
        success: true,
        message: result.message,
        user: result.user,
        token: result.token,
      };
    } catch (error) {
      console.error('Authentication failed:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async logout() {
    try {
      if (!this.token) {
        return { success: true, message: 'Already logged out' };
      }

      const response = await fetch(`${this.baseURL}/api/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
      });

      const result = await response.json();
      
      // Clear local token regardless of server response
      this.token = null;
      localStorage.removeItem('webauthn-token');

      return {
        success: true,
        message: result.message || 'Logged out successfully',
      };
    } catch (error) {
      console.error('Logout failed:', error);
      // Still clear local token
      this.token = null;
      localStorage.removeItem('webauthn-token');
      
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async getUserInfo() {
    try {
      if (!this.token) {
        return { success: false, error: 'No token available' };
      }

      const response = await fetch(`${this.baseURL}/api/auth/user`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${this.token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.status === 401) {
        // Token is invalid, clear it
        this.token = null;
        localStorage.removeItem('webauthn-token');
        return { success: false, error: 'Authentication expired' };
      }

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Failed to get user info:', error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  getDeviceName() {
    const userAgent = navigator.userAgent;
    if (/iPhone/i.test(userAgent)) return 'iPhone';
    if (/iPad/i.test(userAgent)) return 'iPad';
    if (/Android/i.test(userAgent)) return 'Android Device';
    if (/Windows/i.test(userAgent)) return 'Windows PC';
    if (/Macintosh/i.test(userAgent)) return 'Mac';
    if (/Linux/i.test(userAgent)) return 'Linux PC';
    return 'Unknown Device';
  }

  isAuthenticated() {
    return !!this.token;
  }

  getToken() {
    return this.token;
  }
}

export default WebAuthnClient;
