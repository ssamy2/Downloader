import asyncio
from database import db

async def add_admin(user_id: int):
    await db.connect()
    try:
        # Check if user exists
        user = await db.get_user(user_id)
        if not user:
            print(f"User {user_id} not found. Creating user...")
            # Add user if not exists
            await db.add_user(
                user_id=user_id,
                username="Sami3d",  # Replace with actual username if needed
                first_name="Sami",  # Replace with actual first name if needed
                language_code="en"
            )
            print(f"User {user_id} created.")
        
        # Add admin privileges
        await db.update_user(
            user_id=user_id,
            is_admin=True,
            is_secondary_owner=True
        )
        print(f"✅ Successfully added admin privileges to user {user_id}")
        
        # Verify
        user = await db.get_user(user_id)
        print(f"\nVerification:")
        print(f"User ID: {user.user_id}")
        print(f"Is Admin: {user.is_admin}")
        print(f"Is Secondary Owner: {user.is_secondary_owner}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await db.close()

if __name__ == "__main__":
    # Replace with the user ID you want to make admin
    asyncio.run(add_admin(6213708507))
