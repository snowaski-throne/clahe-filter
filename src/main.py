from js import ImageData, Object, slyApp, JSON
from pyodide.ffi import create_proxy
import numpy as np
import cv2


def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))

def debug_js_object(obj, name="object"):
  """Debug JavaScript objects with comprehensive info"""
  print(f"\n=== DEBUG {name} ===")
  
  # Try to get type and basic info
  try:
    print(f"Type: {type(obj)}")
    print(f"Dir: {dir(obj)}")
  except Exception as e:
    print(f"Error getting type/dir: {e}")
  
  # Try Object.keys() for JS objects
  try:
    keys = Object.keys(obj)
    print(f"Object.keys(): {list(keys)}")
    
    # Try to access each key
    for key in keys:
      try:
        value = getattr(obj, key)
        print(f"  {key}: {type(value)} = {value}")
      except Exception as e:
        print(f"  {key}: Error accessing - {e}")
  except Exception as e:
    print(f"Object.keys() failed: {e}")
  
  # Try JSON.stringify for complex objects
  try:
    json_str = JSON.stringify(obj)
    print(f"JSON.stringify(): {json_str}")
  except Exception as e:
    print(f"JSON.stringify() failed: {e}")
  
  # Try vars() for Python objects
  try:
    print(f"vars(): {vars(obj)}")
  except Exception as e:
    print(f"vars() failed: {e}")
  
  print(f"=== END DEBUG {name} ===\n")

def main(mode='process'):
  app = slyApp.app
  store = slyApp.store
  app = getattr(app, '$children')[0]

  context = app.context
  state = app.state

  # store action example
  # appEventEmitter = app.appEventEmitter
  # eventData = Object()
  # eventData.action = 'videos/nextImage'
  # eventData.payload = {}
  # appEventEmitter.emit('store-action', eventData)

  cur_img = getattr(store.state.videos.all, str(context.imageId))
  
  print(f"Processing media ID: {context.imageId}")
  print(f"Current frame: {context.frame}")
  
  # Check if this is a video or image and handle accordingly
  has_sources = hasattr(cur_img, 'sources') and cur_img.sources and len(cur_img.sources) > 0
  is_video = hasattr(cur_img, 'frames') and hasattr(cur_img, 'fileMeta') and getattr(cur_img.fileMeta, 'framesCount', None) is not None
  
  print(f"\nMedia type detection:")
  print(f"  has_sources: {has_sources}")
  print(f"  is_video: {is_video}")
  print(f"  current frame: {context.frame}")
  
  if has_sources:
    # Handle images - use existing logic
    print("Processing as IMAGE")
    img_src = cur_img.sources[0]
    img_cvs = img_src.imageData
    img_ctx = img_cvs.getContext("2d")
    print(f"Image canvas: {img_cvs.width}x{img_cvs.height}")
  
  elif is_video:
    # Handle videos - look for direct canvas access like images
    print("Processing as VIDEO")
    print("Looking for video canvas equivalent to img.sources...")
    
    # Search store.state.videos for video player components (not individual videos)
    print("\nSearching store.state.videos for player components:")
    
    def search_for_canvas_in_object(obj, obj_name, max_depth=3, current_depth=0):
      """Recursively search for canvas objects"""
      if current_depth >= max_depth:
        return None
        
      try:
        # Check if this object is itself a canvas
        if hasattr(obj, 'getContext'):
          print(f"  🎯 FOUND CANVAS in {obj_name}!")
          return obj
          
        # Check if this object has canvas properties
        if hasattr(obj, 'canvas'):
          canvas = getattr(obj, 'canvas')
          if hasattr(canvas, 'getContext'):
            print(f"  🎯 FOUND CANVAS in {obj_name}.canvas!")
            return canvas
            
        if hasattr(obj, 'imageData'):
          img_data = getattr(obj, 'imageData')
          if hasattr(img_data, 'getContext'):
            print(f"  🎯 FOUND CANVAS in {obj_name}.imageData!")
            return img_data
        
        # If this is a JS object, search its properties
        if str(type(obj)) == "<class 'pyodide.ffi.JsProxy'>":
          try:
            keys = Object.keys(obj)
            for key in keys:
              try:
                value = getattr(obj, key)
                # Recursively search if it's another object
                if str(type(value)) == "<class 'pyodide.ffi.JsProxy'>":
                  result = search_for_canvas_in_object(value, f"{obj_name}.{key}", max_depth, current_depth + 1)
                  if result:
                    return result
              except Exception as e:
                pass  # Skip properties we can't access
          except Exception as e:
            pass
            
      except Exception as e:
        pass
        
      return None
    
    # Search through store.state.videos (excluding 'all' since that's the dataset)
    video_canvas = None
    videos_obj = store.state.videos
    videos_keys = [key for key in Object.keys(videos_obj) if key != 'all']  # Skip the dataset
    print(f"  Searching videos keys (excluding 'all'): {videos_keys}")
    
    for key in videos_keys:
      try:
        obj = getattr(videos_obj, key)
        print(f"  Searching videos.{key}: {type(obj)}")
        
        result = search_for_canvas_in_object(obj, f"videos.{key}")
        if result:
          video_canvas = result
          break
          
      except Exception as e:
        print(f"  Error searching videos.{key}: {e}")
    
    # If not found in videos, search broader store.state
    if not video_canvas:
      print(f"\n  Searching broader store.state for player components:")
      store_keys = Object.keys(store.state)
      player_keys = [key for key in store_keys if any(term in key.lower() for term in 
                     ['player', 'canvas', 'render', 'display', 'current', 'active', 'ui'])]
      print(f"  Potential player-related store keys: {player_keys}")
      
      for key in player_keys:
        try:
          obj = getattr(store.state, key)
          print(f"  Searching store.{key}: {type(obj)}")
          
          result = search_for_canvas_in_object(obj, f"store.{key}")
          if result:
            video_canvas = result
            break
            
        except Exception as e:
          print(f"  Error searching store.{key}: {e}")
    
    # Search for canvas-like properties in the individual video object (fallback)
    if not video_canvas:
      print(f"\n  Fallback: Searching cur_img for canvas properties:")
      all_props = dir(cur_img)
      canvas_props = [prop for prop in all_props if any(term in prop.lower() for term in 
                     ['canvas', 'image', 'source', 'data', 'element', 'frame', 'render', 'display'])]
      print(f"  Potential canvas properties: {canvas_props}")
      
      # Try individual video object properties
      for prop in canvas_props:
        try:
          value = getattr(cur_img, prop)
          print(f"  cur_img.{prop}: {type(value)}")
          
          # Check if this could be a canvas
          if hasattr(value, 'getContext'):
            print(f"    ^ This has getContext() - it's a canvas!")
            video_canvas = value
            break
          elif hasattr(value, 'canvas'):
            print(f"    ^ This has a canvas property!")
            video_canvas = getattr(value, 'canvas')
            break
          elif hasattr(value, 'imageData'):
            print(f"    ^ This has imageData property!")
            video_canvas = getattr(value, 'imageData')
            break
            
        except Exception as e:
          print(f"  Error accessing {prop}: {e}")
    
    # Final canvas setup
    
    if video_canvas:
      print(f"\n🎯 FOUND VIDEO CANVAS OBJECT!")
      print(f"  Type: {type(video_canvas)}")
      try:
        print(f"  Dimensions: {video_canvas.width}x{video_canvas.height}")
        img_cvs = video_canvas
        img_ctx = video_canvas.getContext("2d")
        print("  Successfully set up for CLAHE processing!")
      except Exception as e:
        print(f"  Error setting up canvas: {e}")
        return
    else:
      print("❌ No direct video canvas access found")
      print("🔄 Trying alternative approach: create canvas from video frame...")
      
      # Alternative approach: Create our own canvas using video dimensions
      try:
        from js import document
        
        # Get video dimensions from fileMeta
        video_width = cur_img.fileMeta.width
        video_height = cur_img.fileMeta.height
        print(f"  Video dimensions: {video_width}x{video_height}")
        
        # Try to get current frame URL from preview system
        # Videos have preview URLs like: "https://app.supervisely.com/previews/.../videoframe/33p/1/174515916?..."
        frame_url = None
        if hasattr(cur_img, 'preview'):
          # Modify preview URL to get specific frame
          preview_url = cur_img.preview
          print(f"  Base preview URL: {preview_url}")
          
          # The preview URL contains frame info, we might be able to modify it for current frame
          # For now, try using the existing preview URL
          frame_url = preview_url
        
        if frame_url:
          print(f"  Using frame URL: {frame_url}")
          
          # Create canvas with video dimensions
          temp_canvas = document.createElement('canvas')
          temp_canvas.width = video_width
          temp_canvas.height = video_height
          temp_ctx = temp_canvas.getContext('2d')
          
          # Create image element to load the frame
          frame_img = document.createElement('img')
          frame_img.crossOrigin = 'anonymous'  # Allow cross-origin for processing
          
          def on_frame_loaded():
            print("  Frame image loaded successfully!")
            try:
              # Draw the frame to our canvas
              temp_ctx.drawImage(frame_img, 0, 0, video_width, video_height)
              print("  Frame drawn to canvas!")
              
              # Set up for CLAHE processing
              nonlocal img_cvs, img_ctx
              img_cvs = temp_canvas
              img_ctx = temp_ctx
              print("  Canvas ready for CLAHE processing!")
              
            except Exception as e:
              print(f"  Error drawing frame to canvas: {e}")
          
          def on_frame_error():
            print("  Error loading frame image")
          
          # Set up image loading
          frame_img.onload = on_frame_loaded
          frame_img.onerror = on_frame_error
          frame_img.src = frame_url
          
          # Note: This is asynchronous - the frame will load after we return
          # For now, we'll set up with empty canvas
          img_cvs = temp_canvas
          img_ctx = temp_ctx
          print("  Canvas created, frame loading...")
          
        else:
          print("❌ No frame URL available")
          return
          
      except Exception as e:
        print(f"❌ Error creating video canvas: {e}")
        return
    
  else:
    print("ERROR: Unknown media type - neither image nor video format recognized")
    return

  if state.imagePixelsDataImageId != context.imageId:
    img_data = img_ctx.getImageData(0, 0, img_cvs.width, img_cvs.height).data

    # reshape flat array of rgba to numpy
    state.imagePixelsData = np.array(img_data, dtype=np.uint8).reshape(img_cvs.height, img_cvs.width, 4)
    state.imagePixelsDataImageId = context.imageId


  new_img_data = None
  img_arr = state.imagePixelsData

  if mode == 'restore':
    new_img_data = img_arr.flatten()
  else:
    clip_limit = state.SliderAutoId6MqE3.value
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))

    if state.labCheck is False:
      img_gray = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2GRAY)
      cl_img_gray = clahe.apply(img_gray)
      cl_img_rgb = cv2.cvtColor(cl_img_gray, cv2.COLOR_GRAY2RGB)
    else:
      img_lab = cv2.cvtColor(img_arr, cv2.COLOR_RGB2LAB)

      lab_planes = list(cv2.split(img_lab))
      lab_planes[0] = clahe.apply(lab_planes[0])
      img_lab = cv2.merge(lab_planes)

      cl_img_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
      
    alpha_channel = img_arr[:, :, 3]
    cl_img = np.dstack((cl_img_rgb, alpha_channel))

    new_img_data = cl_img.flatten().astype(np.uint8)

  pixels_proxy = create_proxy(new_img_data)
  pixels_buf = pixels_proxy.getBuffer("u8clamped")
  new_img_data = ImageData.new(pixels_buf.data, img_cvs.width, img_cvs.height)

  img_ctx.putImageData(new_img_data, 0, 0)
  img_src.version += 1

  pixels_proxy.destroy()
  pixels_buf.release()

main