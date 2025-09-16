from js import ImageData, Object, slyApp
from pyodide.ffi import create_proxy
import numpy as np
import cv2


def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))

def main(mode='process', method='hist'):
  try:
    app = slyApp.app
    store = slyApp.store
    app = getattr(app, '$children')[0]

    context = app.context
    state = app.state
    
    print(f"Main called with mode={mode}, method={method}")
    print(f"Current imageId: {context.imageId}")
    
    # Debug video mode access
    print("=== SEARCHING FOR VIDEO CANVAS ===")
    print(f"Current imageId: {context.imageId}")
    
    # The metadata record doesn't contain the canvas - let's look elsewhere
    img_cvs = None
    
    # Try different locations where the video frame canvas might be stored
    canvas_search_paths = [
      # Try current video frame in store
      ("store.state.videos.current", lambda: getattr(store.state.videos, 'current', None)),
      ("store.state.videos.currentFrame", lambda: getattr(store.state.videos, 'currentFrame', None)),
      ("store.state.videos.activeFrame", lambda: getattr(store.state.videos, 'activeFrame', None)),
      
      # Try context properties
      ("context.imageData", lambda: getattr(context, 'imageData', None)),
      ("context.canvas", lambda: getattr(context, 'canvas', None)),
      ("context.currentFrame", lambda: getattr(context, 'currentFrame', None)),
      
      # Try store state general properties
      ("store.state.currentImage", lambda: getattr(store.state, 'currentImage', None)),
      ("store.state.activeImage", lambda: getattr(store.state, 'activeImage', None)),
      ("store.state.frame", lambda: getattr(store.state, 'frame', None)),
      
      # Try app context
      ("app.currentImage", lambda: getattr(app, 'currentImage', None)),
      ("app.activeFrame", lambda: getattr(app, 'activeFrame', None)),
    ]
    
    for path_name, path_func in canvas_search_paths:
      try:
        result = path_func()
        print(f"Checking {path_name}: {result is not None}")
        
        if result is not None:
          print(f"  -> type: {type(result)}")
          
          # Check if this object has canvas-like properties
          canvas_props = ['imageData', 'canvas', 'sources']
          for prop in canvas_props:
            if hasattr(result, prop):
              prop_value = getattr(result, prop)
              print(f"  -> {prop}: {type(prop_value)}")
              
              # Check if this looks like a canvas
              if hasattr(prop_value, 'width') and hasattr(prop_value, 'height'):
                print(f"    -> Found canvas! {prop_value.width}x{prop_value.height}")
                img_cvs = prop_value
                print(f"    -> Using {path_name}.{prop}")
                break
          
          # Check if result itself is a canvas
          if img_cvs is None and hasattr(result, 'width') and hasattr(result, 'height'):
            print(f"  -> Result itself is canvas! {result.width}x{result.height}")
            img_cvs = result
            print(f"    -> Using {path_name} directly")
            
        if img_cvs is not None:
          break
            
      except Exception as e:
        print(f"Error checking {path_name}: {e}")
    
    if img_cvs is None:
      print("=== COMPREHENSIVE OBJECT EXPLORATION ===")
      
      # Explore what's actually available in store.state
      try:
        if hasattr(store.state, 'object_keys'):
          store_keys = list(store.state.object_keys())
          print(f"store.state keys: {store_keys}")
        
        # Check if videos has other properties
        if hasattr(store.state, 'videos'):
          videos = store.state.videos
          if hasattr(videos, 'object_keys'):
            video_keys = list(videos.object_keys())
            print(f"store.state.videos keys: {video_keys}")
        
        # Explore context object
        if hasattr(context, 'object_keys'):
          context_keys = list(context.object_keys())
          print(f"context keys: {context_keys}")
      except Exception as e:
        print(f"Error exploring objects: {e}")
      
      print("=== EXPLORING CONTEXT.FRAME PROPERTY ===")
      # The context has a 'frame' property - let's explore it!
      try:
        if hasattr(context, 'frame'):
          frame_obj = context.frame
          print(f"context.frame exists: {frame_obj is not None}")
          if frame_obj is not None:
            print(f"context.frame type: {type(frame_obj)}")
            
            # Explore frame object properties
            if hasattr(frame_obj, 'object_keys'):
              frame_keys = list(frame_obj.object_keys())
              print(f"context.frame keys: {frame_keys}")
            
            # Check for canvas-like properties on frame
            frame_props = ['imageData', 'canvas', 'sources', 'data', 'url', 'image']
            for prop in frame_props:
              if hasattr(frame_obj, prop):
                prop_value = getattr(frame_obj, prop)
                print(f"frame.{prop}: {type(prop_value)}")
                if hasattr(prop_value, 'width') and hasattr(prop_value, 'height'):
                  print(f"  -> Found canvas in frame.{prop}! {prop_value.width}x{prop_value.height}")
                  img_cvs = prop_value
                  break
      except Exception as e:
        print(f"Error exploring context.frame: {e}")
      
      print("=== TRYING IMAGE-BASED VIDEO DISPLAY ===")
      # Video frames might be displayed as <img> elements, not canvas
      try:
        from js import document
        
        # Look for image elements that might contain video frames
        img_selectors = [
          'img',
          '.video-frame',
          '.frame-image',
          '.annotation-image',
          '[data-frame]',
          '.sly-frame',
          '.video-display img'
        ]
        
        for selector in img_selectors:
          try:
            elements = document.querySelectorAll(selector)
            print(f"Found {len(elements)} img elements for '{selector}'")
            
            for i, element in enumerate(elements):
              if hasattr(element, 'naturalWidth') and hasattr(element, 'naturalHeight'):
                print(f"  Image {i}: {element.tagName} {element.naturalWidth}x{element.naturalHeight}")
                print(f"    -> src: {element.src[:100] if hasattr(element, 'src') else 'No src'}...")
                
                # If this is a substantial image, it might be our video frame
                if element.naturalWidth > 100 and element.naturalHeight > 100:
                  print(f"    -> Large image found, might be video frame")
                  # We can't directly get canvas from img, but we can create one
                  # and copy the image data to it
                  try:
                    from js import document
                    canvas = document.createElement('canvas')
                    canvas.width = element.naturalWidth
                    canvas.height = element.naturalHeight
                    ctx = canvas.getContext('2d')
                    ctx.drawImage(element, 0, 0)
                    img_cvs = canvas
                    print(f"    -> Created canvas from image: {canvas.width}x{canvas.height}")
                    break
                  except Exception as canvas_error:
                    print(f"    -> Error creating canvas from image: {canvas_error}")
            
            if img_cvs is not None:
              break
              
          except Exception as e:
            print(f"Error with img selector '{selector}': {e}")
            
      except Exception as e:
        print(f"Error accessing DOM images: {e}")
      
      if img_cvs is None:
        print("ERROR: Could not find video frame canvas anywhere - DOM or API")
        return
    
    print(f"SUCCESS: Found canvas with dimensions {img_cvs.width}x{img_cvs.height}")

    img_ctx = img_cvs.getContext("2d")

    # Initialize state variables if they don't exist
    if not hasattr(state, 'imagePixelsDataImageId'):
      state.imagePixelsDataImageId = None
    if not hasattr(state, 'imagePixelsData'):
      state.imagePixelsData = None
    
    print(f"Canvas dimensions: {img_cvs.width}x{img_cvs.height}")
    
    # Cache frame data to avoid reprocessing the same frame
    # This is especially important for video where users might navigate back and forth
    if state.imagePixelsDataImageId != context.imageId:
      img_data = img_ctx.getImageData(0, 0, img_cvs.width, img_cvs.height).data

      # Reshape flat array of rgba to numpy for OpenCV processing
      state.imagePixelsData = np.array(img_data, dtype=np.uint8).reshape(img_cvs.height, img_cvs.width, 4)
      state.imagePixelsDataImageId = context.imageId
      print(f"Loaded new image data: shape={state.imagePixelsData.shape}, dtype={state.imagePixelsData.dtype}")
      
      # Store original frame data for restore functionality
      if not hasattr(state, 'originalFrameData') or state.originalFrameData is None:
        state.originalFrameData = {}
      state.originalFrameData[context.imageId] = state.imagePixelsData.copy()
      print("Stored original frame data")
    else:
      print("Using cached image data")


    new_img_data = None
    img_arr = state.imagePixelsData

    if mode == 'restore':
      # Restore original frame data for this specific frame (important for video)
      if hasattr(state, 'originalFrameData') and context.imageId in state.originalFrameData:
        original_data = state.originalFrameData[context.imageId]
        new_img_data = original_data.flatten()
        # Update the cached data to the original for consistency
        state.imagePixelsData = original_data.copy()
      else:
        # Fallback to current data if original not available
        new_img_data = img_arr.flatten()
    else:
      # Apply enhancement based on method parameter
      if method == 'clahe':
        # Apply CLAHE with clip limit from slider
        clip_limit = state.SliderAutoId6MqE3.value
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        
        if state.labCheck is False:
          img_gray = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2GRAY)
          enhanced_gray = clahe.apply(img_gray)
          enhanced_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
        else:
          # Convert RGBA to RGB first, then to LAB
          img_rgb = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2RGB)
          img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
          lab_planes = list(cv2.split(img_lab))
          lab_planes[0] = clahe.apply(lab_planes[0])
          img_lab = cv2.merge(lab_planes)
          enhanced_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
          
      else:  # method == 'hist' (default)
        # Apply histogram equalization
        if state.labCheck is False:
          img_gray = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2GRAY)
          enhanced_gray = cv2.equalizeHist(img_gray)
          enhanced_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
        else:
          # Convert RGBA to RGB first, then to LAB
          img_rgb = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2RGB)
          img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
          lab_planes = list(cv2.split(img_lab))
          lab_planes[0] = cv2.equalizeHist(lab_planes[0])
          img_lab = cv2.merge(lab_planes)
          enhanced_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
        
      alpha_channel = img_arr[:, :, 3]
      enhanced_img = np.dstack((enhanced_rgb, alpha_channel))

      new_img_data = enhanced_img.flatten().astype(np.uint8)

    print(f"=== UPDATING CANVAS ===")
    print(f"new_img_data shape: {new_img_data.shape if hasattr(new_img_data, 'shape') else len(new_img_data)}")
    print(f"new_img_data dtype: {new_img_data.dtype if hasattr(new_img_data, 'dtype') else type(new_img_data)}")
    print(f"Canvas dimensions: {img_cvs.width}x{img_cvs.height}")
    print(f"Expected pixels: {img_cvs.width * img_cvs.height * 4}")
    print(f"Actual pixels: {len(new_img_data)}")
    
    pixels_proxy = create_proxy(new_img_data)
    pixels_buf = pixels_proxy.getBuffer("u8clamped")
    new_image_data = ImageData.new(pixels_buf.data, img_cvs.width, img_cvs.height)
    
    print(f"Created ImageData object: {type(new_image_data)}")
    
    # Update the canvas with processed image data
    img_ctx.putImageData(new_image_data, 0, 0)
    print("Canvas updated with new image data")
    
    # For video mode, try different update mechanisms
    print("=== VIDEO MODE CANVAS UPDATE ===")
    
    # Try to update canvas version if it has one
    try:
      if hasattr(img_cvs, 'version'):
        old_version = img_cvs.version
        img_cvs.version += 1
        print(f"Updated canvas version: {old_version} -> {img_cvs.version}")
    except Exception as e:
      print(f"No canvas version to update: {e}")
    
    # Try to update the video state to trigger refresh
    try:
      if hasattr(store.state.videos, 'version'):
        old_video_version = store.state.videos.version
        store.state.videos.version += 1
        print(f"Updated videos.version: {old_video_version} -> {store.state.videos.version}")
      
      # Force trigger a state change on the current imageId
      if hasattr(store.state.videos, 'currentImageId'):
        current_id = store.state.videos.currentImageId
        print(f"Current video imageId: {current_id}")
        # Trigger a reactive update by temporarily changing and restoring
        store.state.videos.currentImageId = current_id + "_temp"
        store.state.videos.currentImageId = current_id
        print("Triggered imageId reactive update")
        
    except Exception as e:
      print(f"Error updating video state: {e}")
    
    # Force a redraw/refresh event
    try:
      from js import Event, window
      
      # Try to dispatch events to trigger refresh
      if hasattr(img_cvs, 'dispatchEvent'):
        # Try multiple event types that might trigger refresh
        event_types = ['redraw', 'update', 'change', 'load']
        for event_type in event_types:
          try:
            event = Event.new(event_type)
            img_cvs.dispatchEvent(event)
            print(f"Dispatched {event_type} event to canvas")
          except:
            pass
      
      # Try window resize event to trigger UI refresh
      resize_event = Event.new('resize')
      window.dispatchEvent(resize_event)
      print("Dispatched window resize event")
        
    except Exception as redraw_error:
      print(f"Could not dispatch refresh events: {redraw_error}")

    pixels_proxy.destroy()
    pixels_buf.release()
    
    print("Frame processing completed successfully")
    
  except Exception as e:
    print(f"Error in main function: {str(e)}")
    import traceback
    traceback.print_exc()

main
