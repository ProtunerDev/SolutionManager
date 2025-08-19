#!/usr/bin/env python3
"""
Production WSGI server with SSL support using waitress.
This script is designed for production deployment with SSL certificates.
"""

import os
import ssl
import logging
from waitress import serve
from app import create_app

def create_ssl_context(cert_path, key_path):
    """Create SSL context for HTTPS"""
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_path, key_path)
        
        # Security settings for production
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        return context
    except Exception as e:
        print(f"❌ Error creating SSL context: {e}")
        return None

def run_production_server():
    """Run the production server with SSL support"""
    
    # Create Flask app
    app = create_app()
    
    # Get configuration
    ssl_enabled = app.config.get('SSL_ENABLED', False)
    ssl_cert_path = app.config.get('SSL_CERT_PATH')
    ssl_key_path = app.config.get('SSL_KEY_PATH')
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 8000))
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s'
    )
    
    print("🚀 Starting SolutionManager Production Server")
    print("=" * 50)
    
    if ssl_enabled and ssl_cert_path and ssl_key_path:
        # Check if SSL certificate files exist
        if os.path.exists(ssl_cert_path) and os.path.exists(ssl_key_path):
            print(f"🔐 SSL enabled")
            print(f"   Certificate: {ssl_cert_path}")
            print(f"   Private Key: {ssl_key_path}")
            print(f"   Server: https://{host}:{port}")
            
            # Serve with SSL
            serve(
                app,
                host=host,
                port=port,
                url_scheme='https',
                ssl_context=(ssl_cert_path, ssl_key_path),
                threads=6,
                connection_limit=1000,
                cleanup_interval=30,
                channel_timeout=120
            )
        else:
            print("❌ SSL certificates not found!")
            print(f"   Looking for: {ssl_cert_path}")
            print(f"   Looking for: {ssl_key_path}")
            print("   Please check your SSL certificate paths.")
            exit(1)
    else:
        print("⚠️  SSL not enabled - running HTTP server")
        print(f"   Server: http://{host}:{port}")
        
        # Serve without SSL
        serve(
            app,
            host=host,
            port=port,
            threads=6,
            connection_limit=1000,
            cleanup_interval=30,
            channel_timeout=120
        )

if __name__ == '__main__':
    run_production_server()
