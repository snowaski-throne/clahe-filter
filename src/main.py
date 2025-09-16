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
    print("=== DEBUGGING VIDEO MODE ACCESS ===")
    print(f"store.state has videos: {hasattr(store.state, 'videos')}")
    if hasattr(store.state, 'videos'):
      print(f"store.state.videos has all: {hasattr(store.state.videos, 'all')}")
      if hasattr(store.state.videos, 'all'):
        videos_all = store.state.videos.all
        print(f"videos.all type: {type(videos_all)}")
        
        # Try different ways to explore the object
        if hasattr(videos_all, 'keys'):
          print(f"videos.all keys: {list(videos_all.keys())}")
        elif hasattr(videos_all, '__iter__'):
          try:
            # If it's iterable, try to get some elements
            items = list(videos_all)[:5]  # First 5 items only
            print(f"videos.all first items: {items}")
          except:
            print("videos.all is iterable but can't list items")
        
        # Try to access by imageId directly
        try:
          imageId_str = str(context.imageId)
          print(f"Looking for imageId: {imageId_str}")
          if hasattr(videos_all, imageId_str):
            print(f"imageId exists as attribute: True")
          else:
            # Try getattr approach (what we use in the actual code)
            cur_img_test = getattr(videos_all, imageId_str, None)
            print(f"getattr result: {cur_img_test is not None}")
        except Exception as e:
          print(f"Error checking imageId: {e}")
    
    # Video mode access (focused on video only since that's what you're using)
    try:
      cur_img = getattr(store.state.videos.all, str(context.imageId))
      print(f"Found video frame for imageId {context.imageId}")
      print(f"cur_img type: {type(cur_img)}")
      
      # Explore video frame object properties to find the canvas
      print("=== EXPLORING VIDEO FRAME PROPERTIES ===")
      try:
        # Try to list all available properties
        if hasattr(cur_img, 'object_keys'):
          print(f"Available keys: {list(cur_img.object_keys())}")
        
        # Try common property names for video frames
        properties_to_check = ['sources', 'imageData', 'canvas', 'data', 'image', 'frame', 'source', 'cvs']
        for prop in properties_to_check:
          has_prop = hasattr(cur_img, prop)
          print(f"cur_img.{prop}: {has_prop}")
          if has_prop:
            prop_value = getattr(cur_img, prop)
            print(f"  -> type: {type(prop_value)}")
            if hasattr(prop_value, 'width') and hasattr(prop_value, 'height'):
              print(f"  -> dimensions: {prop_value.width}x{prop_value.height}")
      except Exception as e:
        print(f"Error exploring properties: {e}")
      
      # Try direct access to imageData if it exists
      img_cvs = None
      if hasattr(cur_img, 'imageData'):
        img_cvs = cur_img.imageData
        print("Using cur_img.imageData directly")
      elif hasattr(cur_img, 'canvas'):
        img_cvs = cur_img.canvas  
        print("Using cur_img.canvas")
      elif hasattr(cur_img, 'sources') and len(cur_img.sources) > 0:
        # Fallback to original logic if sources exists
        img_src = cur_img.sources[0]
        img_cvs = img_src.imageData
        print("Using cur_img.sources[0].imageData")
      else:
        print("ERROR: Could not find canvas/imageData in video frame object")
        return
      print(f"Final canvas type: {type(img_cvs)}")
      print(f"Final canvas dimensions: {img_cvs.width}x{img_cvs.height}")
      
    except Exception as e:
      print(f"ERROR: Failed to access video frame data: {e}")
      import traceback
      traceback.print_exc()
      return

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
    
    # Store old version to check if it changes
    old_version = img_src.version
    print(f"Current img_src.version: {old_version}")
    
    img_ctx.putImageData(new_image_data, 0, 0)
    
    # For video mode, we might need to trigger additional updates
    print("=== VIDEO MODE SPECIFIC UPDATES ===")
    
    # Update the source version
    old_version = img_src.version
    img_src.version += 1
    print(f"Updated img_src.version: {old_version} -> {img_src.version}")
    
    # Try to trigger video frame refresh
    try:
      if hasattr(cur_img, 'version'):
        cur_img.version += 1
        print(f"Updated cur_img.version: {cur_img.version}")
    except:
      print("No cur_img.version to update")
    
    # Try to update the video state
    try:
      if hasattr(store.state.videos, 'currentImageId'):
        print(f"Current video imageId: {store.state.videos.currentImageId}")
      if hasattr(store.state.videos, 'version'):
        store.state.videos.version += 1
        print(f"Updated videos.version: {store.state.videos.version}")
    except:
      print("No video state version to update")
    
    # Force a redraw if possible
    try:
      if hasattr(img_cvs, 'dispatchEvent'):
        # Create a custom event to trigger redraw
        from js import Event
        redraw_event = Event.new('redraw')
        img_cvs.dispatchEvent(redraw_event)
        print("Dispatched redraw event")
    except Exception as redraw_error:
      print(f"Could not dispatch redraw event: {redraw_error}")

    pixels_proxy.destroy()
    pixels_buf.release()
    
    print("Frame processing completed successfully")
    
  except Exception as e:
    print(f"Error in main function: {str(e)}")
    import traceback
    traceback.print_exc()

main
