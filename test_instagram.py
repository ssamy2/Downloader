"""
Quick test for Instagram browser scraper
"""
import asyncio
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_instagram():
    from instagram_browser_scraper import get_browser_manager
    
    print("=" * 60)
    print("🧪 Testing Instagram Browser Scraper")
    print("=" * 60)
    
    url = "https://www.instagram.com/reel/DTxqsPUDZ5x/"
    output = "test_download.mp4"
    
    print(f"\n📋 Test URL: {url}")
    print(f"📁 Output: {output}\n")
    
    try:
        manager = await get_browser_manager()
        
        print("🔄 Starting download...")
        success = await manager.download_instagram(url, output)
        
        if success:
            import os
            if os.path.exists(output):
                size = os.path.getsize(output)
                print(f"\n✅ Download successful!")
                print(f"📊 File size: {size / 1024 / 1024:.2f} MB")
                print(f"📁 Location: {output}")
            else:
                print("\n❌ File not found after download")
        else:
            print("\n❌ Download failed")
        
        await manager.cleanup_all()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("🏁 Test completed")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_instagram())
