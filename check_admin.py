import asyncio
from database import db

async def check_user_status(user_id):
    await db.connect()
    try:
        # Check if user exists
        user = await db.get_user(user_id)
        if not user:
            print(f"User {user_id} not found in database.")
            return
            
        print(f"\nUser ID: {user.user_id}")
        print(f"Username: {user.username}")
        print(f"Is Admin: {user.is_admin}")
        print(f"Is Secondary Owner: {user.is_secondary_owner}")
        print(f"Is Banned: {user.is_banned}")
        
        # Check if user is in admin list
        admins = await db.get_admins()
        admin_ids = [admin.user_id for admin in admins]
        print(f"\nAdmin List: {admin_ids}")
        
        if user_id in admin_ids:
            print("✅ User is in admin list")
        else:
            print("❌ User is NOT in admin list")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await db.close()

if __name__ == "__main__":
    # Replace 6213708507 with the user ID you want to check
    asyncio.run(check_user_status(6213708507))
