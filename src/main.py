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

def process_clahe_with_canvas(img_cvs, img_ctx, app, cur_img, mode='process'):
  """Apply CLAHE processing to the given canvas"""
  try:
    print(f"\n🎨 Starting CLAHE processing on {img_cvs.width}x{img_cvs.height} canvas...")
    
    context = app.context
    state = app.state
    
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
    
    # For images, increment version to trigger refresh
    try:
      img_src = cur_img.sources[0] if hasattr(cur_img, 'sources') and cur_img.sources else None
      if img_src:
        img_src.version += 1
        print("  ✅ Image version incremented for refresh")
    except:
      print("  ℹ️ No image version to increment (video processing)")

    pixels_proxy.destroy()
    pixels_buf.release()
    
    print("  ✅ CLAHE processing completed successfully!")
    
  except Exception as e:
    print(f"  ❌ Error in CLAHE processing: {e}")

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
    
    # Process CLAHE immediately for images
    process_clahe_with_canvas(img_cvs, img_ctx, app, cur_img, mode)
    return
  
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
    
    # Test frame-level sources approach (like images but per frame)
    if not video_canvas:
      print(f"\n  Testing frame-level sources approach:")
      try:
        current_frame = context.frame
        print(f"  Trying cur_img[{current_frame}].sources...")
        
        # Try accessing the specific frame
        frame_obj = None
        try:
          # Try numeric indexing
          frame_obj = cur_img[current_frame]
          print(f"    cur_img[{current_frame}]: {type(frame_obj)}")
        except:
          try:
            # Try string indexing
            frame_obj = cur_img[str(current_frame)]
            print(f"    cur_img['{current_frame}']: {type(frame_obj)}")
          except:
            try:
              # Try accessing from frames property
              frame_obj = getattr(cur_img.frames, str(current_frame))
              print(f"    cur_img.frames['{current_frame}']: {type(frame_obj)}")
            except:
              print(f"    ❌ Could not access frame {current_frame}")
        
        if frame_obj:
          print(f"    ✅ Found frame object: {type(frame_obj)}")
          
          # Check if frame has sources like images do
          if hasattr(frame_obj, 'sources'):
            sources = getattr(frame_obj, 'sources')
            print(f"    ✅ Frame has sources: {type(sources)}, length: {len(sources) if hasattr(sources, '__len__') else 'unknown'}")
            
            if sources and len(sources) > 0:
              frame_src = sources[0]
              print(f"    ✅ Frame source[0]: {type(frame_src)}")
              
              if hasattr(frame_src, 'imageData'):
                video_canvas = frame_src.imageData
                print(f"    🎯 FOUND FRAME CANVAS! {type(video_canvas)}")
              else:
                print(f"    ❌ Frame source has no imageData")
            else:
              print(f"    ❌ Frame sources is empty")
          else:
            print(f"    ❌ Frame has no sources property")
            # Debug what the frame object does have
            try:
              frame_keys = Object.keys(frame_obj) if str(type(frame_obj)) == "<class 'pyodide.ffi.JsProxy'>" else dir(frame_obj)
              print(f"    Frame properties: {frame_keys}")
            except:
              print(f"    Could not get frame properties")
        
      except Exception as e:
        print(f"  Error testing frame-level approach: {e}")
    
    # Search for canvas-like properties in the individual video object (final fallback)
    if not video_canvas:
      print(f"\n  Final fallback: Searching cur_img for canvas properties:")
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
          preview_url = cur_img.preview
          print(f"  Base preview URL: {preview_url}")
          
          # Modify URL for current frame and full resolution
          current_frame = context.frame
          
          # Replace resolution (150:0:0) with video dimensions (480:360)
          # Replace frame number with current frame
          modified_url = preview_url
          
          # Fix resolution - replace resize:fill:150:0:0 with actual video dimensions
          if 'resize:fill:150:0:0' in modified_url:
            modified_url = modified_url.replace('resize:fill:150:0:0', f'resize:fill:{video_width}:{video_height}:0')
          
          # Try to adjust frame number - the URL might have format like videoframe/33p/1/
          # We need to replace the frame number (1) with current_frame
          import re
          frame_pattern = r'videoframe/([^/]+)/(\d+)/'
          match = re.search(frame_pattern, modified_url)
          if match:
            quality = match.group(1)  # e.g., "33p"
            original_frame = int(match.group(2))  # e.g., "1"
            
            # Try different frame indexing strategies
            # Strategy 1: 1-indexed (context.frame=0 -> URL frame=1)
            new_frame_1indexed = current_frame + 1
            # Strategy 2: 0-indexed (context.frame=0 -> URL frame=0)  
            new_frame_0indexed = current_frame
            
            # For frame 0, try both strategies
            if current_frame == 0:
              # Try 0-indexed first
              new_frame = new_frame_0indexed
              print(f"  Trying 0-indexed: frame {current_frame} -> URL frame {new_frame}")
            else:
              # For other frames, use 1-indexed
              new_frame = new_frame_1indexed
              print(f"  Using 1-indexed: frame {current_frame} -> URL frame {new_frame}")
              
            modified_url = re.sub(frame_pattern, f'videoframe/{quality}/{new_frame}/', modified_url)
            print(f"  Adjusted frame from {original_frame} to {new_frame} for context.frame={current_frame}")
          else:
            print(f"  Could not find frame pattern in URL")
          
          frame_url = modified_url
          print(f"  Modified URL: {frame_url}")
        
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
          
          def on_frame_loaded(event=None):
            print("  Frame image loaded successfully!")
            try:
              # Draw the frame to our canvas
              temp_ctx.drawImage(frame_img, 0, 0, video_width, video_height)
              print("  Frame drawn to canvas!")
              
              # Set up for CLAHE processing
              img_cvs = temp_canvas
              img_ctx = temp_ctx
              print("  Canvas ready for CLAHE processing!")
              
              # Continue with CLAHE processing now that frame is loaded
              process_clahe_with_canvas(img_cvs, img_ctx, app, cur_img, mode)
              
            except Exception as e:
              print(f"  Error drawing frame to canvas: {e}")
          
          def on_frame_error(event=None):
            print("  ❌ Error loading frame image - cannot process video")
          
          # Set up image loading
          frame_img.onload = on_frame_loaded
          frame_img.onerror = on_frame_error
          frame_img.src = frame_url
          
          print("  Canvas created, waiting for frame to load...")
          return  # Exit here - processing continues in onload callback
          
        else:
          print("❌ No frame URL available")
          return
          
      except Exception as e:
        print(f"❌ Error creating video canvas: {e}")
        return
    
  else:
    print("ERROR: Unknown media type - neither image nor video format recognized")
    return

main