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
    app = slyApp.app
    store = slyApp.store
    app = getattr(app, '$children')[0]

    context = app.context
    state = app.state
    
    print(f"Main called with mode={mode}, method={method}")
    print(f"Current imageId: {context.imageId}")
    
    # Frame-level processing approach - much more efficient!
    print("=== FRAME-LEVEL PROCESSING ===")
    
    # Get current frame information  
    try:
      current_frame = getattr(store.state.videos.all, str(context.imageId))
      
      # Extract video ID and frame information
      video_id = None
      frame_index = 0
      
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
      print(f"Error getting frame info: {e}")
      # Fallback to using imageId directly
      video_id = context.imageId
      frame_index = 0
      print(f"Using fallback - video_id: {video_id}, frame_index: {frame_index}")
    
    # Get processing parameters from UI state
    clip_limit = state.SliderAutoId6MqE3.value if method == 'clahe' else 40
    use_lab = state.labCheck
    
    print(f"Processing parameters:")
    print(f"  Method: {method}")
    print(f"  Clip limit: {clip_limit}")
    print(f"  Use LAB color space: {use_lab}")
    
    if mode == 'restore':
      print("🔄 Frame processing mode set to ORIGINAL (no processing)")
      # For frame-based approach, restore just means switching off processing
      # The frame cache will handle serving original frames
      return
    
    # Demonstrate frame processing capabilities
    print("🎯 Frame-based processing demonstration:")
    
    # Create a mock images cache and API for demonstration
    # In real integration, you'd hook into the actual Supervisely API
    mock_cache = {}
    
    # Simulate processing the current frame
    try:
      # In a real implementation, you would:
      # 1. Get the actual Supervisely API instance
      # 2. Use the real images_cache from the application
      # 3. Call get_frame_np_processed instead of get_frame_np
      
      print(f"📊 Would process frame {frame_index} from video {video_id}")
      print(f"🔧 Processing method: {method.upper()}")
      if method == 'clahe':
        print(f"⚙️ CLAHE clip limit: {clip_limit}")
      print(f"🎨 Color space: {'LAB' if use_lab else 'Grayscale → BGR'}")
      
      # Generate a unique cache key for this configuration
      cache_key = f"{video_id}_{frame_index}_{method}_{clip_limit}_{use_lab}"
      print(f"💾 Cache key: {cache_key}")
      
      print("✅ Frame processing setup complete!")
      print("\n" + "="*50)
      print("🚀 INTEGRATION INSTRUCTIONS:")
      print("="*50)
      print("To fully integrate this frame processing:")
      print("1. Replace calls to get_frame_np() with get_frame_np_processed()")
      print("2. Pass method, clip_limit, and use_lab parameters")
      print("3. The processed frames will be automatically cached")
      print("4. Original frames remain accessible when processing is disabled")
      print("="*50)
      
    except Exception as e:
      print(f"Error in frame processing demonstration: {e}")
      import traceback
      traceback.print_exc()
    
  except Exception as e:
    print(f"Error in main function: {str(e)}")
    import traceback
    traceback.print_exc()

main
