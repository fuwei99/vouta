import base64
import requests
import config as app_config

def upload_image_to_imgbb(image_data: bytes) -> str:
    """
    Uploads an image to ImgBB and returns the display URL.
    
    Args:
        image_data: The image data in bytes.
        
    Returns:
        The URL of the uploaded image, or None if upload fails.
    """
    api_key = app_config.IMGBB_API_KEY
    if not api_key:
        print("ImgBB API key not configured. Skipping upload.")
        return None

    try:
        # Convert bytes to base64 string
        b64_data = base64.b64encode(image_data).decode('utf-8')
        
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": api_key,
            "image": b64_data,
        }
        
        response = requests.post(url, data=payload)
        response.raise_for_status()
        
        result = response.json()
        if result.get("success"):
            return result["data"]["url"]
        else:
            print(f"ImgBB upload failed: {result}")
            return None
            
    except Exception as e:
        print(f"Error uploading to ImgBB: {e}")
        return None
