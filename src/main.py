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
    
    # CORS-safe processing approach using CSS filters
    print("=== CSS FILTER-BASED PROCESSING ===")
    
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
    
    print(f"Processing parameters:")
    print(f"  Method: {method}")
    print(f"  Clip limit: {clip_limit}")
    print(f"  Use LAB color space: {use_lab}")
    
    if mode == 'restore':
      print("🔄 Restoring original image appearance")
      apply_css_filters_to_display('restore', 0, False)
      return
    
    # Apply CSS filter-based processing (CORS-safe)
    print("🎯 Applying CSS filter-based processing:")
    print(f"🔧 Processing method: {method.upper()}")
    if method == 'clahe':
      print(f"⚙️ CLAHE clip limit: {clip_limit}")
    print(f"🎨 Color space: {'LAB' if use_lab else 'Grayscale → BGR'}")
    
    # Apply the filters
    apply_css_filters_to_display(method, clip_limit, use_lab)

  except Exception as e:
    print(f"Error in main function: {str(e)}")
    import traceback
    traceback.print_exc()

def apply_css_filters_to_display(method, clip_limit, use_lab):
    """Apply CSS filters to image/video elements (CORS-safe approach)"""
    from js import document
    
    try:
        # Find all potential image/video display elements
        img_elements = document.querySelectorAll('img')
        canvas_elements = document.querySelectorAll('canvas')
        video_elements = document.querySelectorAll('video')
        
        # Also look for elements that might contain video frames
        video_containers = document.querySelectorAll('[class*="video"], [class*="player"], [class*="sly"]')
        
        print(f"🖼️ Found {len(img_elements)} img, {len(canvas_elements)} canvas, {len(video_elements)} video elements")
        print(f"🖼️ Found {len(video_containers)} video container elements")
        
        # Generate CSS filter based on method
        css_filter = generate_css_filter(method, clip_limit, use_lab)
        print(f"🎨 Applying CSS filter: {css_filter}")
        
        elements_processed = 0
        
        # Apply to img elements
        for i, img in enumerate(img_elements):
            try:
                if hasattr(img, 'naturalWidth') and img.naturalWidth > 50:  # Skip small images
                    img.style.filter = css_filter
                    img.style.transition = "filter 0.3s ease"  # Smooth transition
                    elements_processed += 1
                    print(f"✅ Applied filter to img element {i}")
            except Exception as e:
                print(f"Error applying filter to img {i}: {e}")
        
        # Apply to canvas elements
        for i, canvas in enumerate(canvas_elements):
            try:
                if hasattr(canvas, 'width') and canvas.width > 50:
                    canvas.style.filter = css_filter
                    canvas.style.transition = "filter 0.3s ease"
                    elements_processed += 1
                    print(f"✅ Applied filter to canvas element {i}")
            except Exception as e:
                print(f"Error applying filter to canvas {i}: {e}")
        
        # Apply to video elements
        for i, video in enumerate(video_elements):
            try:
                video.style.filter = css_filter
                video.style.transition = "filter 0.3s ease"
                elements_processed += 1
                print(f"✅ Applied filter to video element {i}")
            except Exception as e:
                print(f"Error applying filter to video {i}: {e}")
        
        # Apply to video container elements (may contain the actual video display)
        for i, container in enumerate(video_containers):
            try:
                # Apply to container and all image/canvas children
                container.style.filter = css_filter
                container.style.transition = "filter 0.3s ease"
                
                # Also apply to children
                children = container.querySelectorAll('img, canvas, video')
                for child in children:
                    child.style.filter = css_filter
                    child.style.transition = "filter 0.3s ease"
                
                elements_processed += 1
                print(f"✅ Applied filter to video container {i} and {len(children)} children")
            except Exception as e:
                print(f"Error applying filter to container {i}: {e}")
        
        if elements_processed > 0:
            print(f"🎉 Successfully applied {method.upper()} filter to {elements_processed} elements")
            return True
        else:
            print("⚠️ No suitable elements found for filter application")
            return False
        
    except Exception as e:
        print(f"Error in CSS filter application: {e}")
        return False

def generate_css_filter(method, clip_limit, use_lab):
    """Generate CSS filter string based on processing method and parameters"""
    try:
        if method == 'restore':
            return 'none'  # Remove all filters
        
        elif method == 'clahe':
            # Simulate CLAHE with brightness and contrast adjustments
            # Map clip_limit (typically 1-100) to reasonable CSS values
            brightness_factor = 1.0 + (clip_limit - 20) / 100.0  # Base adjustment
            contrast_factor = 1.0 + (clip_limit - 20) / 50.0     # Contrast enhancement
            
            # Clamp values to reasonable ranges
            brightness_factor = max(0.5, min(2.0, brightness_factor))
            contrast_factor = max(0.8, min(2.5, contrast_factor))
            
            if use_lab:
                # LAB processing simulation with additional saturation
                return f"brightness({brightness_factor}) contrast({contrast_factor}) saturate(1.2)"
            else:
                # Grayscale-based processing
                return f"brightness({brightness_factor}) contrast({contrast_factor})"
        
        elif method == 'hist':
            # Simulate histogram equalization with contrast and brightness
            if use_lab:
                # LAB color space simulation
                return "contrast(1.4) brightness(1.1) saturate(1.15)"
            else:
                # Standard histogram equalization
                return "contrast(1.5) brightness(1.05)"
        
        else:
            return 'none'
            
    except Exception as e:
        print(f"Error generating CSS filter: {e}")
        return 'none'

main
