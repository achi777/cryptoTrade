#!/usr/bin/env python3
"""Make a user an admin"""
import sys
from app import create_app, db
from app.models.user import User

app = create_app()

with app.app_context():
    # Get email from command line or use default
    email = sys.argv[1] if len(sys.argv) > 1 else 'admin@cryptotrade.com'

    user = User.query.filter_by(email=email).first()

    if not user:
        print(f"User {email} not found")
        print("\nExisting users:")
        for u in User.query.all():
            print(f"  - {u.email} (is_admin={u.is_admin})")
        sys.exit(1)

    if user.is_admin:
        print(f"User {email} is already an admin")
    else:
        user.is_admin = True
        db.session.commit()
        print(f"User {email} is now an admin")
