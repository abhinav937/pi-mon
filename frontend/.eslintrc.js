module.exports = {
  extends: [
    'react-app',
    'react-app/jest'
  ],
  rules: {
    'no-unused-vars': 'warn',
    'no-console': 'warn',
    'no-undef': 'off' // Disable no-undef since we're using browser APIs
  },
  globals: {
    // WebAuthn APIs
    'PublicKeyCredential': 'readonly',
    'AuthenticatorAttestationResponse': 'readonly',
    'AuthenticatorAssertionResponse': 'readonly',
    
    // Browser APIs
    'navigator': 'readonly',
    'window': 'readonly',
    'localStorage': 'readonly',
    'sessionStorage': 'readonly',
    'fetch': 'readonly',
    'atob': 'readonly',
    'btoa': 'readonly',
    
    // Web APIs
    'ArrayBuffer': 'readonly',
    'Uint8Array': 'readonly',
    'TextEncoder': 'readonly',
    'TextDecoder': 'readonly',
    'crypto': 'readonly',
    'subtle': 'readonly',
    
    // React Scripts globals
    'process': 'readonly'
  },
  env: {
    browser: true,
    es2020: true,
    node: true
  }
};
