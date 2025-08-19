#!/usr/bin/env python3
"""
SSL Certificate Setup Script for SolutionManager

This script helps you set up SSL certificates from Cloudflare Origin Certificate.
"""

import os
import sys

def setup_ssl_certificates():
    """Setup SSL certificates for the application"""
    
    ssl_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_path = os.path.join(ssl_dir, 'cloudflare_cert.pem')
    key_path = os.path.join(ssl_dir, 'cloudflare_key.pem')
    
    print("🔐 SSL Certificate Setup for SolutionManager")
    print("=" * 50)
    
    # Ensure SSL directory exists
    if not os.path.exists(ssl_dir):
        os.makedirs(ssl_dir)
        print(f"✅ Created SSL directory: {ssl_dir}")
    
    print(f"\n📁 SSL files location:")
    print(f"   Certificate: {cert_path}")
    print(f"   Private Key: {key_path}")
    
    print("\n📋 Instructions:")
    print("1. Save your Cloudflare Origin Certificate as: ssl/cloudflare_cert.pem")
    print("2. Save your Cloudflare Private Key as: ssl/cloudflare_key.pem")
    print("3. Update your .env file with SSL configuration")
    
    print("\n🔧 Environment Variables to add to .env:")
    print("SSL_ENABLED=true")
    print(f"SSL_CERT_PATH={cert_path}")
    print(f"SSL_KEY_PATH={key_path}")
    print("APP_URL=https://yourdomain.com")
    
    print("\n⚠️  Security Notes:")
    print("- Keep your private key secure and never commit it to version control")
    print("- Add ssl/ directory to .gitignore")
    print("- Use different certificates for development and production")
    print("- Ensure proper file permissions (600 for private key)")
    
    # Check if certificates already exist
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"\n✅ SSL certificates found!")
        print("   You can now run the application with SSL enabled.")
        return True
    else:
        print(f"\n❌ SSL certificates not found.")
        print("   Please follow the instructions above to set up your certificates.")
        return False

def create_gitignore_entry():
    """Add SSL directory to .gitignore"""
    gitignore_path = os.path.join(os.path.dirname(__file__), '.gitignore')
    ssl_entry = "\n# SSL Certificates\nssl/\n*.pem\n*.crt\n*.key\n"
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            content = f.read()
        
        if 'ssl/' not in content:
            with open(gitignore_path, 'a') as f:
                f.write(ssl_entry)
            print("✅ Added SSL files to .gitignore")
        else:
            print("ℹ️  SSL files already in .gitignore")
    else:
        with open(gitignore_path, 'w') as f:
            f.write(ssl_entry)
        print("✅ Created .gitignore with SSL entries")

def verify_ssl_setup():
    """Verify SSL setup is correct"""
    print("\n🔍 Verifying SSL Setup...")
    
    ssl_dir = os.path.join(os.path.dirname(__file__), 'ssl')
    cert_path = os.path.join(ssl_dir, 'cloudflare_cert.pem')
    key_path = os.path.join(ssl_dir, 'cloudflare_key.pem')
    
    checks = []
    
    # Check if SSL directory exists
    checks.append(("SSL directory exists", os.path.exists(ssl_dir)))
    
    # Check if certificate file exists
    checks.append(("Certificate file exists", os.path.exists(cert_path)))
    
    # Check if private key file exists
    checks.append(("Private key file exists", os.path.exists(key_path)))
    
    # Check if files are not empty
    if os.path.exists(cert_path):
        checks.append(("Certificate file not empty", os.path.getsize(cert_path) > 0))
    
    if os.path.exists(key_path):
        checks.append(("Private key file not empty", os.path.getsize(key_path) > 0))
    
    # Display results
    all_passed = True
    for check_name, passed in checks:
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 SSL setup is complete! You can now run your app with HTTPS.")
        print("   Run: python run.py")
    else:
        print("\n⚠️  SSL setup incomplete. Please follow the setup instructions.")
    
    return all_passed

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        verify_ssl_setup()
    else:
        setup_ssl_certificates()
        create_gitignore_entry()
        verify_ssl_setup()
