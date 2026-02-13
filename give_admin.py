#!/usr/bin/env python3
"""
Script to give admin access to user 6213708507
"""
import asyncio
from database import db

async def main():
    await db.connect()
    
    user_id = 6213708507
    
    # Get or create user
    user = await db.get_user(user_id)
    if not user:
        # Create user if doesn't exist
        await db.add_user(user_id)
        user = await db.get_user(user_id)
    
    # Give admin and secondary owner permissions
    await db.update_user(user_id, is_admin=True, is_secondary_owner=True)
    
    print(f"✅ User {user_id} has been granted admin and secondary owner permissions!")
    
    await db.close()

if __name__ == "__main__":
    asyncio.run(main())
