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
    
    # Apply the filters with delayed search for dynamic content
    apply_css_filters_to_display(method, clip_limit, use_lab)
    
    # Also try delayed search in case video loads after our script
    print("🔄 Scheduling delayed search for dynamic content...")
    schedule_delayed_search(method, clip_limit, use_lab)

  except Exception as e:
    print(f"Error in main function: {str(e)}")
    import traceback
    traceback.print_exc()

def apply_css_filters_to_display(method, clip_limit, use_lab):
    """Apply CSS filters to image/video elements (CORS-safe approach)"""
    from js import document
    
    try:
        # SUPER COMPREHENSIVE search for Supervisely's video implementation
        print("🔍 Starting comprehensive DOM search...")
        
        # Standard elements
        img_elements = document.querySelectorAll('img')
        canvas_elements = document.querySelectorAll('canvas')
        video_elements = document.querySelectorAll('video')
        iframe_elements = document.querySelectorAll('iframe')
        
        # Supervisely-specific searches
        sly_elements = document.querySelectorAll('[class*="sly"]')
        video_containers = document.querySelectorAll('[class*="video"], [class*="player"], [class*="frame"]')
        image_containers = document.querySelectorAll('[class*="image"], [class*="img"]')
        
        # Look for elements that might have video content
        all_divs = document.querySelectorAll('div')
        all_spans = document.querySelectorAll('span')
        styled_elements = document.querySelectorAll('[style*="background"]')
        
        # WebGL and advanced rendering
        webgl_canvases = document.querySelectorAll('canvas[data-engine], canvas[data-webgl]')
        
        # Look for large elements that might contain video
        large_elements = []
        for div in all_divs:
            try:
                rect = div.getBoundingClientRect()
                if rect.width > 200 and rect.height > 200:
                    large_elements.append(div)
            except:
                pass
        
        # Try to find the largest image/media element (likely the main frame)
        all_media_elements = document.querySelectorAll('img, canvas, video, iframe, div, span')
        
        print(f"🔍 Advanced search results:")
        print(f"   Standard: {len(img_elements)} img, {len(canvas_elements)} canvas, {len(video_elements)} video, {len(iframe_elements)} iframe")
        print(f"   Supervisely: {len(sly_elements)} sly-elements, {len(video_containers)} video containers, {len(image_containers)} image containers")
        print(f"   Layout: {len(all_divs)} divs, {len(all_spans)} spans, {len(styled_elements)} styled elements")
        print(f"   Advanced: {len(webgl_canvases)} WebGL canvases, {len(large_elements)} large elements")
        print(f"   Total: {len(all_media_elements)} elements to examine")
        
        # Generate CSS filter based on method
        css_filter = generate_css_filter(method, clip_limit, use_lab)
        print(f"🎨 Applying CSS filter: {css_filter}")
        
        elements_processed = 0
        
        # FOCUS ON LARGE ELEMENTS FIRST - most likely to contain video
        print("🎯 PRIORITY SEARCH: Focusing on large elements that might contain video")
        for i, element in enumerate(large_elements):
            try:
                element_type = element.tagName.lower()
                classes = getattr(element, 'className', 'no-class')
                rect = element.getBoundingClientRect()
                
                print(f"🔍 LARGE[{i}] {element_type.upper()}: {rect.width:.0f}x{rect.height:.0f}, classes: {classes}")
                
                # Apply dramatic filter to large elements
                if method == 'restore':
                    dramatic_filter = 'none'
                    element.style.border = 'none'
                else:
                    dramatic_filter = css_filter + " saturate(4.0) contrast(3.0)"  # EXTRA dramatic for large elements
                    element.style.border = f"4px solid red"  # RED border for large elements
                
                element.style.filter = dramatic_filter
                element.style.transition = "filter 0.3s ease"
                elements_processed += 1
                print(f"✅ Applied EXTRA DRAMATIC filter to LARGE[{i}] {element_type}: {dramatic_filter}")
                
            except Exception as e:
                print(f"Error applying filter to LARGE[{i}]: {e}")
        
        # Also apply to Supervisely-specific elements
        print("🎯 SUPERVISELY SEARCH: Targeting sly-specific elements")
        for i, element in enumerate(sly_elements):
            try:
                element_type = element.tagName.lower()
                classes = getattr(element, 'className', 'no-class')
                
                print(f"🔍 SLY[{i}] {element_type.upper()}: classes: {classes}")
                
                # Apply dramatic filter to sly elements and their children
                if method == 'restore':
                    dramatic_filter = 'none'
                    element.style.border = 'none'
                else:
                    dramatic_filter = css_filter + " saturate(3.5) contrast(2.5)"
                    element.style.border = f"3px solid purple"  # PURPLE border for sly elements
                
                element.style.filter = dramatic_filter
                element.style.transition = "filter 0.3s ease"
                
                # Also apply to ALL children of sly elements
                children = element.querySelectorAll('*')
                for child in children:
                    child.style.filter = dramatic_filter
                    child.style.border = "1px solid purple"
                
                elements_processed += 1
                print(f"✅ Applied DRAMATIC filter to SLY[{i}] {element_type} and {len(children)} children: {dramatic_filter}")
                
            except Exception as e:
                print(f"Error applying filter to SLY[{i}]: {e}")
        
        # COMPREHENSIVE SEARCH: Apply to key element types  
        print("🚀 COMPREHENSIVE MODE: Checking all potential video containers")
        key_selectors = [
            ('img', img_elements),
            ('canvas', canvas_elements), 
            ('video', video_elements),
            ('iframe', iframe_elements),
            ('video-container', video_containers),
            ('image-container', image_containers)
        ]
        
        for selector_name, elements in key_selectors:
            for i, element in enumerate(elements):
                try:
                    element_type = element.tagName.lower()
                    classes = getattr(element, 'className', 'no-class')
                    
                    if element_type == 'img':
                        width = getattr(element, 'naturalWidth', 0)
                        height = getattr(element, 'naturalHeight', 0)
                        src = getattr(element, 'src', 'no-src')[:50]
                        print(f"🔍 {selector_name.upper()}[{i}] IMG: {width}x{height}, src: {src}..., classes: {classes}")
                    elif element_type == 'canvas':
                        width = getattr(element, 'width', 0)
                        height = getattr(element, 'height', 0)
                        print(f"🔍 {selector_name.upper()}[{i}] CANVAS: {width}x{height}, classes: {classes}")
                    else:
                        print(f"🔍 {selector_name.upper()}[{i}] {element_type.upper()}: classes: {classes}")
                    
                    # Apply dramatic filter
                    if method == 'restore':
                        dramatic_filter = 'none'
                        element.style.border = 'none'
                    else:
                        dramatic_filter = css_filter + " saturate(3.0) contrast(2.0)"
                        element.style.border = f"2px solid orange"
                    
                    element.style.filter = dramatic_filter
                    element.style.transition = "filter 0.3s ease"
                    elements_processed += 1
                    print(f"✅ Applied filter to {selector_name.upper()}[{i}] {element_type}: {dramatic_filter}")
                    
                except Exception as e:
                    print(f"Error applying filter to {selector_name}[{i}]: {e}")
        
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

def schedule_delayed_search(method, clip_limit, use_lab):
    """Schedule delayed searches for dynamically loaded content"""
    from js import setTimeout, document
    
    def delayed_search_callback():
        try:
            print("⏰ DELAYED SEARCH: Looking for dynamically loaded content...")
            
            # Re-run comprehensive search after delay
            apply_css_filters_to_display(method, clip_limit, use_lab)
            
            # Also try searching for elements that might have appeared
            print("🔍 Checking for new elements that loaded after initial search...")
            
            # Look for elements with specific patterns that might indicate video
            video_indicators = document.querySelectorAll('[src*="mp4"], [src*="webm"], [src*="video"], [data-video], [class*="frame"]')
            supervisely_video = document.querySelectorAll('[class*="sly-video"], [class*="video-player"], [class*="image-viewer"]')
            
            if len(video_indicators) > 0:
                print(f"🎯 Found {len(video_indicators)} video indicator elements!")
                for i, elem in enumerate(video_indicators):
                    try:
                        elem.style.filter = generate_css_filter(method, clip_limit, use_lab) + " saturate(5.0) contrast(4.0)"
                        elem.style.border = "5px solid green"  # GREEN for video indicators
                        print(f"✅ Applied MEGA DRAMATIC filter to video indicator {i}")
                    except Exception as e:
                        print(f"Error applying to video indicator {i}: {e}")
            
            if len(supervisely_video) > 0:
                print(f"🎯 Found {len(supervisely_video)} Supervisely video elements!")
                for i, elem in enumerate(supervisely_video):
                    try:
                        elem.style.filter = generate_css_filter(method, clip_limit, use_lab) + " saturate(5.0) contrast(4.0)"
                        elem.style.border = "5px solid cyan"  # CYAN for supervisely video
                        print(f"✅ Applied MEGA DRAMATIC filter to supervisely video {i}")
                    except Exception as e:
                        print(f"Error applying to supervisely video {i}: {e}")
            
        except Exception as e:
            print(f"Error in delayed search: {e}")
    
    # Schedule searches at different intervals
    print("⏰ Scheduling delayed searches at 500ms, 1s, and 2s...")
    setTimeout(delayed_search_callback, 500)   # 0.5 seconds
    setTimeout(delayed_search_callback, 1000)  # 1 second  
    setTimeout(delayed_search_callback, 2000)  # 2 seconds

main
