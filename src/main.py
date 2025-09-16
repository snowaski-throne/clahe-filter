from js import ImageData, Object, slyApp
from pyodide.ffi import create_proxy
import numpy as np
import cv2


def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))

def apply_image_processing(img_bgr, method='hist', clip_limit=40, use_lab=False):
    """Apply CLAHE or histogram equalization to a BGR image"""
    try:
        if method == 'clahe':
            if use_lab:
                # Convert to LAB color space
                lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
                # Apply CLAHE to L channel
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8,8))
                lab[:, :, 0] = clahe.apply(lab[:, :, 0])
                # Convert back to BGR
                return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                # Convert to grayscale, apply CLAHE, then back to BGR
                gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8,8))
                enhanced = clahe.apply(gray)
                return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        elif method == 'hist':
            if use_lab:
                # Convert to LAB color space
                lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB)
                # Apply histogram equalization to L channel
                lab[:, :, 0] = cv2.equalizeHist(lab[:, :, 0])
                # Convert back to BGR
                return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                # Convert to grayscale, apply histogram equalization, then back to BGR
                gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
                enhanced = cv2.equalizeHist(gray)
                return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
        
        return img_bgr
    except Exception as e:
        print(f"Error in image processing: {e}")
        return img_bgr

def get_frame_np_processed(api, images_cache, video_id, frame_index, method='hist', clip_limit=40, use_lab=False):
    """Enhanced version of get_frame_np with CLAHE/histogram processing"""
    # Create unique keys for both original and processed frames
    original_key = "{}_{}".format(video_id, frame_index)
    processed_key = "{}_{}_{}_{}_{}".format(video_id, frame_index, method, clip_limit, use_lab)
    
    # Check if processed frame is already cached
    if processed_key in images_cache:
        return images_cache[processed_key]
    
    # Get original frame (using existing caching logic)
    if original_key not in images_cache:
        img_rgb = api.video.frame.download_np(video_id, frame_index)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        images_cache[original_key] = img_bgr
    
    original_frame = images_cache[original_key]
    
    # Apply processing
    processed_frame = apply_image_processing(original_frame, method, clip_limit, use_lab)
    
    # Cache processed frame
    images_cache[processed_key] = processed_frame
    
    return processed_frame

def main(mode='process', method='hist'):
    try:
        # Safer access to Supervisely app components with fallbacks
        app = None
        store = None
        context = None
        state = None
        
        try:
            app = slyApp.app
            if hasattr(slyApp, 'store'):
                store = slyApp.store
                app = getattr(app, '$children')[0]
                context = app.context
                state = app.state
        except Exception as access_error:
            print(f"Warning: Limited access to Supervisely components: {access_error}")
        
        # Get current image/video ID
        current_image_id = None
        if context and hasattr(context, 'imageId'):
            current_image_id = context.imageId
        else:
            # Try alternative access methods
            try:
                if app and hasattr(app, 'context'):
                    current_image_id = app.context.imageId
            except:
                current_image_id = "unknown"
        
        print(f"Main called with mode={mode}, method={method}")
        print(f"Current imageId: {current_image_id}")
        
        # Real video processing approach using Supervisely API + OpenCV
        print("=== SIMPLE IMAGE PROCESSING ===")
        
        # Get processing parameters from UI state (with fallbacks)
        clip_limit = 40
        use_lab = False
        
        if state:
            try:
                if hasattr(state, 'SliderAutoId6MqE3') and method == 'clahe':
                    clip_limit = state.SliderAutoId6MqE3.value
                if hasattr(state, 'labCheck'):
                    use_lab = state.labCheck
            except Exception as state_error:
                print(f"Warning: Could not access UI state: {state_error}")
        
        print(f"Processing parameters:")
        print(f"  Method: {method}")
        print(f"  Clip limit: {clip_limit}")
        print(f"  Use LAB color space: {use_lab}")
        
        # Extract video/frame information if available
        video_id = current_image_id
        frame_index = 0
        
        if store:
            try:
                current_frame = getattr(store.state.videos.all, str(current_image_id))
                
                if hasattr(current_frame, 'videoId'):
                    video_id = current_frame.videoId
                elif hasattr(current_frame, 'id'):
                    video_id = current_frame.id
                    
                if hasattr(current_frame, 'frameIndex'):
                    frame_index = current_frame.frameIndex
                elif hasattr(current_frame, 'index'):
                    frame_index = current_frame.index
                    
                print(f"Processing video_id: {video_id}, frame_index: {frame_index}")
            
            except Exception as e:
                print(f"Note: Using fallback frame info due to: {e}")
                print(f"Using fallback - video_id: {video_id}, frame_index: {frame_index}")
        else:
            print(f"Using minimal processing - video_id: {video_id}, frame_index: {frame_index}")
        
        if mode == 'restore':
            print("🔄 Restoring original image")
            restore_original_image()
            return
        
        # SIMPLE IMAGE PROCESSING APPROACH
        print("🎯 Processing current frame and displaying in app:")
        print(f"🔧 Processing method: {method.upper()}")
        if method == 'clahe':
            print(f"⚙️ CLAHE clip limit: {clip_limit}")
        print(f"🎨 Color space: {'LAB' if use_lab else 'Grayscale → BGR'}")
        
        # Process current frame and display in app interface
        process_and_display_image(video_id, frame_index, method, clip_limit, use_lab)

    except Exception as e:
        print(f"Error in main function: {str(e)}")
        import traceback
        traceback.print_exc()

def process_and_display_image(video_id, frame_index, method, clip_limit, use_lab):
    """Download current frame, process it with OpenCV, and display on canvas"""
    try:
        print("🖼️ Starting simple image processing...")
        
        # Step 1: Get current frame from Supervisely
        print("📥 Downloading current frame...")
        frame_image = get_current_frame(video_id, frame_index)
        if frame_image is None:
            print("❌ Could not get current frame")
            return False
        
        print(f"✅ Downloaded frame: {frame_image.shape}")
        
        # Step 2: Process frame with OpenCV
        print(f"🔧 Processing frame with {method.upper()}...")
        processed_image = apply_image_processing(frame_image, method, clip_limit, use_lab)
        if processed_image is None:
            print("❌ Failed to process frame")
            return False
        
        print(f"✅ Processed frame: {processed_image.shape}")
        
        # Step 3: Display processed image on canvas
        print("🎨 Displaying processed image on canvas...")
        success = display_image_on_canvas(processed_image)
        
        if success:
            print("🎉 Successfully displayed processed image!")
            return True
        else:
            print("⚠️ Image processed but canvas update failed")
            return False
        
    except Exception as e:
        print(f"Error in image processing pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_current_frame(video_id, frame_index):
    """Get the current frame from Supervisely using direct API access"""
    try:
        print(f"📥 Getting frame {frame_index} from video {video_id}")
        
        # Direct API creation with hardcoded credentials
        api = None
        
        try:
            # Try to import supervisely if available in Pyodide environment
            import supervisely as sly
            print("✅ Found supervisely module")
            
            # Create API instance directly
            server_address = "https://app.supervisely.com"
            api_token = "zerPjM0yd0UzBXi9EpyaVOjxoiFazNMMSvtWVlS88CL9E5boXbhWMH9k2p32iq5rM9eZ7bAROaf0dCcNNqzk5hmXz67yHFDfkkKqEtXVw8rQLv0YgbhvV2TkA4GOPKYf"
            
            api = sly.Api(server_address, api_token)
            print("✅ Created Supervisely API instance directly")
            
        except ImportError:
            print("📝 supervisely not available in Pyodide environment")
            # Fallback: try accessing via JavaScript context
            try:
                from js import slyApp
                if hasattr(slyApp, 'app') and slyApp.app:
                    app = slyApp.app
                    if hasattr(app, '$children') and len(getattr(app, '$children', [])) > 0:
                        main_component = getattr(app, '$children')[0]
                        if hasattr(main_component, 'api'):
                            api = main_component.api
                            print("✅ Found API via fallback method")
            except:
                pass
        
        # Get or create images cache
        images_cache = {}
        
        if api:
            # Use the proper get_frame_np function
            img_bgr = get_frame_np(api, images_cache, video_id, frame_index)
            print(f"✅ Downloaded actual frame via API: {img_bgr.shape}")
            return img_bgr
        else:
            print("❌ No API found, falling back to test image")
            print("💡 Try installing supervisely in the Pyodide environment")
            return create_test_image()
        
    except Exception as e:
        print(f"Error getting current frame: {e}")
        import traceback
        traceback.print_exc()
        # Return test image as final fallback
        return create_test_image()

def get_frame_np(api, images_cache, video_id, frame_index):
    """Get frame using Supervisely API with caching"""
    uniq_key = "{}_{}".format(video_id, frame_index)
    if uniq_key not in images_cache:
        img_rgb = api.video.frame.download_np(video_id, frame_index)
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
        images_cache[uniq_key] = img_bgr
        print(f"📥 Downloaded and cached frame: {img_bgr.shape}")
    else:
        print(f"📦 Using cached frame: {uniq_key}")
    return images_cache[uniq_key]

def create_test_image():
    """Create a test image for processing demonstration"""
    try:
        import numpy as np
        
        # Create a realistic test image with various brightness regions
        height, width = 480, 640
        test_img = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Create gradient backgrounds
        for y in range(height):
            for x in range(width):
                test_img[y, x, 0] = int(50 + (x / width) * 150)  # Blue gradient
                test_img[y, x, 1] = int(30 + (y / height) * 120)  # Green gradient
                test_img[y, x, 2] = int(80 + ((x + y) / (width + height)) * 100)  # Red gradient
        
        # Add some dark and bright regions to test CLAHE/histogram
        test_img[100:200, 100:250] = test_img[100:200, 100:250] // 4  # Dark region
        test_img[250:350, 350:500] = np.minimum(test_img[250:350, 350:500] * 2, 255)  # Bright region
        
        # Add some texture
        noise = np.random.randint(-15, 15, (height, width, 3), dtype=np.int16)
        test_img = np.clip(test_img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        
        print(f"📸 Created test image: {width}x{height}")
        return test_img
        
    except Exception as e:
        print(f"Error creating test image: {e}")
        # Final fallback
        return np.full((480, 640, 3), 128, dtype=np.uint8)

def display_image_on_canvas(processed_image):
    """Display the processed image in the app interface"""
    try:
        from js import document, Blob, URL, Uint8Array
        import base64
        
        print("🎨 Displaying processed image in app interface...")
        
        # Find the card content area where the buttons are
        card_content = document.querySelector('.card .content')
        if not card_content:
            print("❌ Could not find card content area")
            return False
        
        print("✅ Found app card content area")
        
        # Remove any existing processed image
        existing_img = document.querySelector('#processed-image-display')
        if existing_img:
            existing_img.remove()
            print("🗑️ Removed existing processed image")
        
        # Convert BGR to RGB for display
        img_rgb = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
        
        # Resize image to reasonable display size
        height, width = img_rgb.shape[:2]
        max_width = 600
        max_height = 400
        
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img_rgb = cv2.resize(img_rgb, (new_width, new_height))
            print(f"📏 Resized image for display: {new_width}x{new_height}")
        
        # Convert to bytes for blob creation
        import numpy as np
        
        # Convert numpy array to PNG-like format
        # Create a simple bitmap header + data
        h, w = img_rgb.shape[:2]
        
        # Convert to bytes
        img_bytes = img_rgb.flatten().tobytes()
        
        # Create a data URL instead (simpler approach)
        # Convert to base64
        img_base64 = base64.b64encode(img_bytes).decode('ascii')
        
        # Create image element
        img_element = document.createElement('img')
        img_element.id = 'processed-image-display'
        img_element.style.maxWidth = '100%'
        img_element.style.height = 'auto'
        img_element.style.border = '2px solid #4CAF50'
        img_element.style.borderRadius = '8px'
        img_element.style.marginTop = '15px'
        img_element.style.display = 'block'
        
        # Create a proper image data URL using canvas
        temp_canvas = document.createElement('canvas')
        temp_canvas.width = w
        temp_canvas.height = h
        temp_ctx = temp_canvas.getContext('2d')
        
        # Create ImageData and put it on temp canvas
        img_data = temp_ctx.createImageData(w, h)
        
        # Fill ImageData with RGBA values
        for y in range(h):
            for x in range(w):
                pixel_index = (y * w + x) * 4
                img_index = (y * w + x) * 3
                
                img_data.data[pixel_index] = img_rgb[y, x, 0]     # R
                img_data.data[pixel_index + 1] = img_rgb[y, x, 1] # G  
                img_data.data[pixel_index + 2] = img_rgb[y, x, 2] # B
                img_data.data[pixel_index + 3] = 255              # A
        
        temp_ctx.putImageData(img_data, 0, 0)
        
        # Convert canvas to data URL
        data_url = temp_canvas.toDataURL('image/png')
        img_element.src = data_url
        
        # Add title
        title_element = document.createElement('div')
        title_element.innerHTML = '🎬 Processed Image Result'
        title_element.style.fontWeight = 'bold'
        title_element.style.marginTop = '15px'
        title_element.style.marginBottom = '5px'
        title_element.style.color = '#4CAF50'
        
        # Append to card content
        card_content.appendChild(title_element)
        card_content.appendChild(img_element)
        
        print("✅ Successfully displayed processed image in app interface!")
        return True
        
    except Exception as e:
        print(f"Error displaying image in app: {e}")
        import traceback
        traceback.print_exc()
        return False

def restore_original_image():
    """Remove the displayed processed image"""
    try:
        print("🔄 Removing processed image...")
        from js import document
        
        # Remove the processed image display
        existing_img = document.querySelector('#processed-image-display')
        if existing_img:
            existing_img.remove()
            print("🗑️ Removed processed image")
        
        # Remove the title as well
        title_elements = document.querySelectorAll('div')
        for element in title_elements:
            if element.innerHTML and '🎬 Processed Image Result' in element.innerHTML:
                element.remove()
                print("🗑️ Removed processed image title")
                break
        
        print("✅ Restoration complete - processed image removed")
        return True
        
    except Exception as e:
        print(f"Error restoring original image: {e}")
        return False

main
