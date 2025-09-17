from js import ImageData, Object, slyApp, JSON, Date
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

def process_histogram_equalization_with_canvas(img_cvs, img_ctx, app, cur_img, mode='process'):
  """Apply histogram equalization processing to the given canvas"""
  try:
    print(f"\n🎨 Starting Histogram Equalization processing on {img_cvs.width}x{img_cvs.height} canvas...")
    
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
      if state.labCheck is False:
        # Apply histogram equalization to grayscale
        img_gray = cv2.cvtColor(img_arr, cv2.COLOR_RGBA2GRAY)
        eq_img_gray = cv2.equalizeHist(img_gray)
        eq_img_rgb = cv2.cvtColor(eq_img_gray, cv2.COLOR_GRAY2RGB)
      else:
        # Apply histogram equalization to L channel in LAB color space
        img_lab = cv2.cvtColor(img_arr, cv2.COLOR_RGB2LAB)

        lab_planes = list(cv2.split(img_lab))
        lab_planes[0] = cv2.equalizeHist(lab_planes[0])  # Equalize L channel only
        img_lab = cv2.merge(lab_planes)

        eq_img_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
        
      alpha_channel = img_arr[:, :, 3]
      eq_img = np.dstack((eq_img_rgb, alpha_channel))

      new_img_data = eq_img.flatten().astype(np.uint8)

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
    
    print("  ✅ Histogram Equalization processing completed successfully!")
    
  except Exception as e:
    print(f"  ❌ Error in Histogram Equalization processing: {e}")

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
  
  # Enhanced debugging for frame tracking
  print(f"\n🔍 FRAME DEBUGGING:")
  print(f"  Processing media ID: {context.imageId}")
  print(f"  Current frame: {context.frame}")
  
  # Check if we have previous frame tracking
  if not hasattr(state, 'lastProcessedFrame') or not hasattr(state, 'lastProcessedImageId'):
    state.lastProcessedFrame = -1
    state.lastProcessedImageId = -1
    print(f"  Initializing frame tracking")
  
  # Initialize frame-to-image-ID mapping if not exists
  if not hasattr(state, 'frameToImageIdMapping'):
    state.frameToImageIdMapping = None
    print(f"  Initializing frame-to-image-ID mapping")
  
  # Detect frame/video changes
  frame_changed = state.lastProcessedFrame != context.frame
  video_changed = state.lastProcessedImageId != context.imageId
  
  print(f"  Last processed: frame={state.lastProcessedFrame}, imageId={state.lastProcessedImageId}")
  print(f"  Frame changed: {frame_changed}")
  print(f"  Video changed: {video_changed}")
  
  # Update tracking
  state.lastProcessedFrame = context.frame
  state.lastProcessedImageId = context.imageId
  
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
    
    # Process histogram equalization immediately for images
    process_histogram_equalization_with_canvas(img_cvs, img_ctx, app, cur_img, mode)
    
    # Also display processed image in our app interface
    try:
      print("  🖼️ Displaying processed image in app interface...")
      from js import document
      
      # Convert canvas to data URL
      processed_data_url = img_cvs.toDataURL('image/png')
      
      # Update our display elements
      display_img = document.getElementById('processed-frame-display')
      status_div = document.getElementById('processed-frame-status')
      
      if display_img and status_div:
        # Show the processed image
        display_img.src = processed_data_url
        display_img.style.display = 'block'  # Make it visible
        
        # Update status
        status_div.textContent = f"✅ Processed image ({img_cvs.width}x{img_cvs.height})"
        status_div.style.color = '#28a745'  # Green color for success
        
        print(f"    ✅ Updated app display with processed image!")
      else:
        print(f"    ❌ Could not find display elements in app interface")
        
    except Exception as e:
      print(f"  ❌ Error updating app display: {e}")
    
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
    
    # Test frame-level sources approach AND get frame-specific image IDs
    if not video_canvas:
      print(f"\n  Testing frame-level sources approach and extracting image IDs:")
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
          
          # Extract image ID for this frame
          frame_image_id = None
          try:
            # Try common properties for image ID
            if hasattr(frame_obj, 'id'):
              frame_image_id = getattr(frame_obj, 'id')
              print(f"    🆔 Frame image ID (from .id): {frame_image_id}")
            elif hasattr(frame_obj, 'imageId'):
              frame_image_id = getattr(frame_obj, 'imageId')
              print(f"    🆔 Frame image ID (from .imageId): {frame_image_id}")
            elif hasattr(frame_obj, 'entityId'):
              frame_image_id = getattr(frame_obj, 'entityId')
              print(f"    🆔 Frame image ID (from .entityId): {frame_image_id}")
            else:
              # Debug all properties to find image ID
              try:
                frame_keys = Object.keys(frame_obj) if str(type(frame_obj)) == "<class 'pyodide.ffi.JsProxy'>" else dir(frame_obj)
                print(f"    Frame properties: {frame_keys}")
                for key in frame_keys:
                  if 'id' in key.lower():
                    value = getattr(frame_obj, key)
                    print(f"      {key}: {value}")
              except:
                print(f"    Could not get frame properties")
          except Exception as e:
            print(f"    Error extracting frame image ID: {e}")
          
          # Store the image ID for later use in URL generation
          if frame_image_id:
            # Store in global/state for URL generation
            state.currentFrameImageId = frame_image_id
            print(f"    ✅ Stored frame image ID: {frame_image_id}")
          
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
            
        else:
          print(f"    ❌ Could not access frame {current_frame}")
          
          # Try building a complete frame-to-image-ID mapping
          print(f"    🔄 Attempting to build complete frame mapping...")
          try:
            frame_mapping = {}
            
            # Try different access patterns for all frames
            if hasattr(cur_img, 'frames'):
              frames_obj = cur_img.frames
              print(f"      Found frames object: {type(frames_obj)}")
              
              # Deep debug the frames structure
              try:
                print(f"      🔍 DEEP DEBUGGING FRAMES STRUCTURE:")
                
                # Try Object.keys for JavaScript objects
                if str(type(frames_obj)) == "<class 'pyodide.ffi.JsProxy'>":
                  try:
                    frame_keys = Object.keys(frames_obj)
                    print(f"        Object.keys(frames): {list(frame_keys)}")
                    
                    # If Object.keys shows properties, try to access them
                    for key in frame_keys:
                      try:
                        value = getattr(frames_obj, key)
                        print(f"        frames.{key}: {type(value)}")
                        
                        # If this value looks like a collection of frames, explore it
                        if str(type(value)) == "<class 'pyodide.ffi.JsProxy'>":
                          try:
                            sub_keys = Object.keys(value)
                            print(f"          frames.{key} has keys: {list(sub_keys)[:5]}...")
                            
                            # Try to access first few items to see structure
                            for sub_key in list(sub_keys)[:3]:
                              try:
                                sub_value = getattr(value, sub_key)
                                print(f"            frames.{key}.{sub_key}: {type(sub_value)}")
                                
                                # Check if this looks like a frame with an image ID
                                if str(type(sub_value)) == "<class 'pyodide.ffi.JsProxy'>":
                                  sub_sub_keys = Object.keys(sub_value)
                                  id_keys = [k for k in sub_sub_keys if 'id' in k.lower()]
                                  print(f"              ID-like keys: {id_keys}")
                                  
                                  for id_key in id_keys:
                                    try:
                                      id_value = getattr(sub_value, id_key)
                                      print(f"                {id_key}: {id_value}")
                                    except:
                                      pass
                              except Exception as e:
                                print(f"            Error accessing frames.{key}.{sub_key}: {e}")
                          except Exception as e:
                            print(f"          Error exploring frames.{key}: {e}")
                      except Exception as e:
                        print(f"        Error accessing frames.{key}: {e}")
                        
                  except Exception as e:
                    print(f"        Error with Object.keys: {e}")
                
                # Also try array-like access
                try:
                  print(f"        🔍 Trying array-like access:")
                  total_frames = cur_img.fileMeta.framesCount if hasattr(cur_img, 'fileMeta') and hasattr(cur_img.fileMeta, 'framesCount') else 10
                  print(f"        Total frames in video: {total_frames}")
                  
                  for i in range(min(5, total_frames)):  # Try first 5 frames
                    try:
                      frame_item = frames_obj[i]
                      print(f"        frames[{i}]: {type(frame_item)}")
                      
                      if str(type(frame_item)) == "<class 'pyodide.ffi.JsProxy'>":
                        item_keys = Object.keys(frame_item)
                        id_keys = [k for k in item_keys if 'id' in k.lower()]
                        print(f"          frames[{i}] ID keys: {id_keys}")
                        for id_key in id_keys:
                          try:
                            id_value = getattr(frame_item, id_key)
                            print(f"            frames[{i}].{id_key}: {id_value}")
                            frame_mapping[i] = id_value
                          except:
                            pass
                    except Exception as e:
                      print(f"        Error accessing frames[{i}]: {e}")
                        
                except Exception as e:
                  print(f"        Error with array access: {e}")
                    
                print(f"      Built frame mapping with {len(frame_mapping)} entries")
                if len(frame_mapping) > 0:
                  # Show a few examples
                  sample_items = list(frame_mapping.items())[:3]
                  print(f"      Sample mappings: {sample_items}")
                  
                  # Store the mapping and get current frame's image ID
                  state.frameToImageIdMapping = frame_mapping
                  if current_frame in frame_mapping:
                    state.currentFrameImageId = frame_mapping[current_frame]
                    print(f"      ✅ Found image ID for frame {current_frame}: {frame_mapping[current_frame]}")
                  else:
                    print(f"      ❌ Current frame {current_frame} not found in mapping")
                else:
                  print(f"      ❌ No frame mappings could be built")
                  
              except Exception as e:
                print(f"      Error building frame mapping: {e}")
            
          except Exception as e:
            print(f"    Error in frame mapping attempt: {e}")
        
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
          
          # Strategy: Try multiple URL approaches, prioritizing high resolution
          current_frame = context.frame
          frame_urls_to_try = []
          
          import re
          frame_pattern = r'videoframe/([^/]+)/(\d+)/(\d+)'
          match = re.search(frame_pattern, preview_url)
          
          print(f"  🔍 Analyzing preview URL for frame pattern:")
          print(f"    URL: {preview_url}")
          if match:
            quality = match.group(1)
            original_frame_num = int(match.group(2))
            original_image_id = match.group(3)
            print(f"    Found frame pattern: quality={quality}, frame={original_frame_num}, imageId={original_image_id}")
          else:
            print(f"    ❌ No frame pattern found in URL!")
          
          # Get the correct image ID for the current frame
          current_frame_image_id = None
          
          # Try using previously extracted frame image ID first
          if hasattr(state, 'currentFrameImageId') and state.currentFrameImageId:
            current_frame_image_id = state.currentFrameImageId
            print(f"    🆔 Using extracted frame image ID: {current_frame_image_id}")
          
          # Try using frame mapping if available
          elif hasattr(state, 'frameToImageIdMapping') and state.frameToImageIdMapping and current_frame in state.frameToImageIdMapping:
            current_frame_image_id = state.frameToImageIdMapping[current_frame]
            print(f"    🆔 Using frame mapping for image ID: {current_frame_image_id}")
          
          # Try to find frame images - they're separate image entities, not in videos.all
          else:
            print(f"    🔍 Searching for frame images (separate image entities)...")
            try:
              current_video_id = context.imageId
              video_frame_mapping = {}
              
              # Search in multiple possible locations for frame images
              search_locations = []
              
              # 1. Check if there's an images collection in store.state
              if hasattr(store.state, 'images') and hasattr(store.state.images, 'all'):
                search_locations.append(('images.all', store.state.images.all))
              
              # 2. Check if images are in the same videos namespace
              if hasattr(store.state.videos, 'all'):
                search_locations.append(('videos.all', store.state.videos.all))
              
              # 3. Check other top-level store locations
              store_keys = Object.keys(store.state)
              for key in store_keys:
                if 'image' in key.lower() or 'frame' in key.lower():
                  try:
                    obj = getattr(store.state, key)
                    if hasattr(obj, 'all'):
                      search_locations.append((f'{key}.all', obj.all))
                  except:
                    pass
              
              print(f"    Will search in {len(search_locations)} locations: {[loc[0] for loc in search_locations]}")
              
              for location_name, collection in search_locations:
                print(f"    🔍 Searching {location_name}...")
                try:
                  all_keys = Object.keys(collection)
                  print(f"      Total items in {location_name}: {len(all_keys)}")
                  
                  frame_count = 0
                  for key in all_keys:
                    try:
                      item = getattr(collection, key)
                      
                      # Check if this item has properties that indicate it's a video frame
                      if str(type(item)) == "<class 'pyodide.ffi.JsProxy'>":
                        item_props = Object.keys(item)
                        
                        # Look for video-related properties indicating this image belongs to a video
                        video_indicators = ['videoId', 'videoFile', 'parentVideoId', 'parentId', 'video']
                        frame_indicators = ['frame', 'frameIndex', 'frameNumber', 'index']
                        
                        video_id = None
                        frame_num = None
                        
                        # Check for video relationship
                        for prop in video_indicators:
                          if prop in item_props:
                            try:
                              video_id = getattr(item, prop)
                              break
                            except:
                              pass
                        
                        # Check for frame number
                        for prop in frame_indicators:
                          if prop in item_props:
                            try:
                              frame_num = getattr(item, prop)
                              break
                            except:
                              pass
                        
                        # If this image belongs to our current video, add to mapping
                        if video_id == current_video_id and frame_num is not None:
                          video_frame_mapping[frame_num] = key
                          frame_count += 1
                          print(f"        ✅ Found frame {frame_num} → Image ID {key}")
                          
                    except Exception as e:
                      pass  # Skip items we can't read
                  
                  print(f"      Found {frame_count} frames in {location_name}")
                  
                  # If we found frames, break (no need to search other locations)
                  if frame_count > 0:
                    break
                    
                except Exception as e:
                  print(f"      Error searching {location_name}: {e}")
              
              print(f"    🎯 FINAL FRAME MAPPING RESULTS:")
              print(f"      Total frames found: {len(video_frame_mapping)}")
              
              if len(video_frame_mapping) > 0:
                # Show all mappings
                sorted_frames = sorted(video_frame_mapping.items())
                for frame_num, img_id in sorted_frames:
                  print(f"        Frame {frame_num} → Image ID {img_id}")
                
                # Store the mapping for future use
                state.frameToImageIdMapping = video_frame_mapping
                
                # Get the image ID for the current frame
                if current_frame in video_frame_mapping:
                  current_frame_image_id = video_frame_mapping[current_frame]
                  print(f"      ✅ Current frame {current_frame} → Image ID {current_frame_image_id}")
                else:
                  print(f"      ❌ Current frame {current_frame} not found in mapping")
                  # Show available frames for debugging
                  available_frames = sorted(video_frame_mapping.keys())
                  print(f"      Available frames: {available_frames}")
              else:
                print(f"      ❌ No frame images found - they might be loaded dynamically")
                
            except Exception as e:
              print(f"    Error searching for frame images: {e}")
          
          # Final fallback
          if not current_frame_image_id:
            current_frame_image_id = original_image_id if match else context.imageId
            print(f"    🆔 Fallback to original image ID: {current_frame_image_id} (may show wrong frame)")
          
          # Strategy 1: High resolution with correct frame and image ID
          url_high_res = preview_url.replace('resize:fill:150:0:0', f'resize:fill:{video_width}:{video_height}:0')
          if match and current_frame_image_id:
            quality = match.group(1)
            
            print(f"    🎯 FRAME URL GENERATION DETAILS:")
            print(f"       Current context.frame: {current_frame}")
            print(f"       Current frame image ID: {current_frame_image_id}")
            print(f"       Quality: {quality}")
            
            # 1-indexed frame with correct image ID (try this first)
            new_frame_1indexed = current_frame + 1
            url_high_1indexed = re.sub(frame_pattern, f'videoframe/{quality}/{new_frame_1indexed}/{current_frame_image_id}', url_high_res)
            frame_urls_to_try.append(("high_res_1indexed_correct_id", url_high_1indexed))
            print(f"       1-indexed URL: {url_high_1indexed}")
            
            # 0-indexed frame with correct image ID
            new_frame_0indexed = current_frame
            url_high_0indexed = re.sub(frame_pattern, f'videoframe/{quality}/{new_frame_0indexed}/{current_frame_image_id}', url_high_res)
            frame_urls_to_try.append(("high_res_0indexed_correct_id", url_high_0indexed))
            print(f"       0-indexed URL: {url_high_0indexed}")
            
            # Strategy 2: Full resolution with correct frame and image ID
            url_full_res_1indexed = re.sub(r'/resize:fill:\d+:\d+:\d+', '', url_high_1indexed)
            url_full_res_0indexed = re.sub(r'/resize:fill:\d+:\d+:\d+', '', url_high_0indexed)
            frame_urls_to_try.append(("full_res_1indexed_correct_id", url_full_res_1indexed))
            frame_urls_to_try.append(("full_res_0indexed_correct_id", url_full_res_0indexed))
          else:
            # Just high resolution with original frame
            frame_urls_to_try.append(("high_resolution", url_high_res))
          
          # Strategy 3: Fallback to original low-res (last resort - same frame always)
          frame_urls_to_try.append(("original_low_res_fallback", preview_url))
          
          # Add cache-busting timestamps to all URLs to prevent browser caching
          cache_buster = int(Date.new().getTime())  # Current timestamp
          frame_urls_with_cache_busting = []
          
          for strategy, url in frame_urls_to_try:
            # Add cache buster as query parameter
            separator = '&' if '?' in url else '?'
            cache_busted_url = f"{url}{separator}cb={cache_buster}&frame_req={current_frame}"
            frame_urls_with_cache_busting.append((strategy, cache_busted_url))
          
          frame_urls_to_try = frame_urls_with_cache_busting
          
          # Try each URL until one works
          print(f"  Will try {len(frame_urls_to_try)} URL strategies (with cache-busting):")
          for i, (strategy, url) in enumerate(frame_urls_to_try):
            print(f"    {i+1}. {strategy}")
            print(f"        URL: {url}")
          
          frame_url = frame_urls_to_try[0][1]  # Start with the first one
          current_strategy_index = 0
        
        if frame_urls_to_try:
          print(f"  Prepared {len(frame_urls_to_try)} URL strategies to try")
          
          # Create canvas with video dimensions
          temp_canvas = document.createElement('canvas')
          temp_canvas.width = video_width
          temp_canvas.height = video_height
          temp_ctx = temp_canvas.getContext('2d')
          
          # Create image element to load the frame
          frame_img = document.createElement('img')
          frame_img.crossOrigin = 'anonymous'  # Allow cross-origin for processing
          
          def on_frame_loaded(event=None):
            strategy_name = frame_urls_to_try[current_strategy_index][0]
            successful_url = frame_urls_to_try[current_strategy_index][1]
            
            print(f"\n🖼️ IMAGE LOAD SUCCESS:")
            print(f"  Strategy: {strategy_name}")
            print(f"  URL: {successful_url}")
            print(f"  Image dimensions: {frame_img.naturalWidth}x{frame_img.naturalHeight}")
            print(f"  Expected frame: {context.frame}")
            
            try:
              # Clear the canvas first to ensure we're drawing fresh content
              temp_ctx.clearRect(0, 0, video_width, video_height)
              
              # Draw the frame to our canvas
              temp_ctx.drawImage(frame_img, 0, 0, video_width, video_height)
              print(f"  ✅ Frame drawn to canvas ({video_width}x{video_height})")
              
              # Get a sample of the raw image data to verify content is different
              try:
                sample_data = temp_ctx.getImageData(0, 0, min(50, video_width), min(50, video_height))
                pixel_sum = sum(sample_data.data[i] for i in range(0, min(200, len(sample_data.data)), 4))  # Sum red pixels only
                print(f"  🔍 Image content signature (pixel sum): {pixel_sum}")
              except Exception as e:
                print(f"  ⚠️ Could not get content signature: {e}")
              
              # Set up for CLAHE processing
              img_cvs = temp_canvas
              img_ctx = temp_ctx
              print("  Canvas ready for Histogram Equalization processing!")
              
              # Continue with histogram equalization processing now that frame is loaded
              process_histogram_equalization_with_canvas(img_cvs, img_ctx, app, cur_img, mode)
              
              # After histogram equalization processing, display processed frame in our app interface
              try:
                print("  🖼️ Displaying processed frame in app interface...")
                
                # Convert processed canvas to data URL
                processed_data_url = temp_canvas.toDataURL('image/png')
                
                # Add a timestamp to the processed image URL to prevent caching
                processed_data_url_with_timestamp = f"{processed_data_url}#t={Date.new().getTime()}"
                
                # Update our display elements
                display_img = document.getElementById('processed-frame-display')
                status_div = document.getElementById('processed-frame-status')
                
                if display_img and status_div:
                  # Show the processed image
                  display_img.src = processed_data_url_with_timestamp
                  display_img.style.display = 'block'  # Make it visible
                  
                  # Update status with more details
                  status_div.textContent = f"✅ Processed frame {context.frame} ({video_width}x{video_height}) - Strategy: {strategy_name}"
                  status_div.style.color = '#28a745'  # Green color for success
                  
                  print(f"    ✅ Updated app display with processed frame (strategy: {strategy_name})!")
                else:
                  print(f"    ❌ Could not find display elements in app interface")
                  
              except Exception as e:
                print(f"  ❌ Error updating app display: {e}")
              
            except Exception as e:
              print(f"  ❌ Error drawing frame to canvas: {e}")
          
          def on_frame_error(event=None):
            nonlocal current_strategy_index
            failed_strategy = frame_urls_to_try[current_strategy_index][0]
            failed_url = frame_urls_to_try[current_strategy_index][1]
            
            print(f"\n❌ IMAGE LOAD FAILED:")
            print(f"  Failed strategy: {failed_strategy}")
            print(f"  Failed URL: {failed_url}")
            print(f"  Frame: {context.frame}")
            
            current_strategy_index += 1
            
            if current_strategy_index < len(frame_urls_to_try):
              strategy, next_url = frame_urls_to_try[current_strategy_index]
              print(f"  🔄 Trying fallback strategy {current_strategy_index + 1}: {strategy}")
              print(f"  🎯 Next URL: {next_url}")
              frame_img.src = next_url  # Try the next URL
            else:
              print("  💀 All URL strategies failed - cannot process video")
              print(f"  Attempted {len(frame_urls_to_try)} strategies for frame {context.frame}")
          
          # Set up image loading with fallback mechanism
          frame_img.onload = on_frame_loaded
          frame_img.onerror = on_frame_error
          
          # Start with the first strategy
          strategy_name, first_url = frame_urls_to_try[0]
          print(f"\n🚀 STARTING IMAGE LOAD:")
          print(f"  Strategy 1: {strategy_name}")
          print(f"  Frame: {current_frame}")
          print(f"  URL: {first_url}")
          print(f"  Cache buster: cb={cache_buster}")
          frame_img.src = first_url
          
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