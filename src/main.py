from js import ImageData, Object, slyApp, JSON, Date
from pyodide.ffi import create_proxy
import numpy as np
import cv2
import supervisely as sly


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

def get_video_frame_using_api(video_id, frame_index, api_instance):
  """Get actual video frame data using Supervisely VideoAnnotation API"""
  try:
    print(f"  🔄 Fetching frame {frame_index} using VideoAnnotation API...")
    
    # Download video annotation (contains frame metadata)
    ann_json = api_instance.video.annotation.download(video_id)
    
    # Get project meta for VideoAnnotation conversion
    video_info = api_instance.video.get_info_by_id(video_id)
    project_id = video_info.project_id
    project_meta = sly.ProjectMeta.from_json(api_instance.project.get_meta(project_id))
    
    # Convert to VideoAnnotation object
    ann = sly.VideoAnnotation.from_json(ann_json, project_meta, key_id_map=sly.KeyIdMap())
    
    print(f"    ✅ Video annotation loaded: {len(ann.figures)} figures")
    
    # Method 1: Try to get frame image directly from API
    try:
      # Get frame image from video
      frame_image_np = api_instance.video.frame.download_np(video_id, frame_index)
      print(f"    ✅ Downloaded frame {frame_index} as numpy array: {frame_image_np.shape}")
      return frame_image_np, True
      
    except Exception as e:
      print(f"    ❌ Could not download frame directly: {e}")
    
    # Method 2: Try alternative frame access methods
    try:
      # Check if frame has associated image entities
      for figure in ann.figures:
        if figure.frame_index == frame_index:
          print(f"    Found figure at frame {frame_index}: {figure.video_object.obj_class.name}")
          # Could potentially extract frame data from figure metadata
      
      print(f"    ⚠️ Frame {frame_index} annotation available but no direct image access")
      return None, False
      
    except Exception as e:
      print(f"    ❌ Error accessing frame annotation: {e}")
      return None, False
    
  except Exception as e:
    print(f"  ❌ Error in VideoAnnotation API access: {e}")
    return None, False

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
    # Handle videos using Supervisely VideoAnnotation API approach  
    print("Processing as VIDEO")
    print("🎯 Using Supervisely VideoAnnotation API approach (not URL manipulation)")
    print("   Reference: https://developer.supervisely.com/app-development/apps-with-gui/video-labeling-tool-app")
    
    # Get basic video info
    video_width = cur_img.fileMeta.width
    video_height = cur_img.fileMeta.height
    current_frame = context.frame
    
    print(f"\nVideo info:")
    print(f"  Dimensions: {video_width}x{video_height}")
    print(f"  Total frames: {cur_img.fileMeta.framesCount}")
    print(f"  Current frame: {current_frame}")
    
    # Try to find the video player's canvas in the DOM
    print(f"\n🎯 Looking for video player's current frame canvas in DOM...")
    
    try:
      from js import document
      
      # Look for video player elements using common selectors
      video_selectors = [
        'video',
        'canvas[class*="video"]',
        'canvas[class*="player"]', 
        'canvas[id*="video"]',
        'canvas[id*="player"]',
        '.video-canvas',
        '.player-canvas'
      ]
      
      found_video_element = None
      for selector in video_selectors:
        try:
          elements = document.querySelectorAll(selector)
          if elements.length > 0:
            print(f"  Found {elements.length} elements matching '{selector}'")
            for i in range(elements.length):
              element = elements[i]
              print(f"    Element {i}: {element.tagName} - {element.className}")
              
              # Check if this element has video-like properties
              if element.tagName.lower() == 'canvas' and hasattr(element, 'getContext'):
                print(f"      Canvas size: {element.width}x{element.height}")
                if element.width == video_width and element.height == video_height:
                  print(f"      ✅ Canvas matches video dimensions!")
                  found_video_element = element
                  break
              elif element.tagName.lower() == 'video':
                print(f"      HTML5 video element found")
                found_video_element = element
                break
                  
        except Exception as e:
          print(f"  Error searching for '{selector}': {e}")
        
        if found_video_element:
          break
    
      # Process the found video element
      if found_video_element:
        print(f"\n🎯 FOUND VIDEO ELEMENT!")
        
        # Create canvas for processing
        temp_canvas = document.createElement('canvas')
        temp_canvas.width = video_width
        temp_canvas.height = video_height
        temp_ctx = temp_canvas.getContext('2d')
        
        if found_video_element.tagName.lower() == 'video':
          print("  Found HTML5 video element - extracting current frame...")
          # Draw current video frame to canvas
          temp_ctx.drawImage(found_video_element, 0, 0, video_width, video_height)
        elif found_video_element.tagName.lower() == 'canvas':
          print("  Found video canvas element - copying content...")
          # Copy canvas content
          temp_ctx.drawImage(found_video_element, 0, 0)
        
        img_cvs = temp_canvas
        img_ctx = temp_ctx
        
        print("  ✅ Video element set up for processing!")
        
        # Process the current frame
        process_histogram_equalization_with_canvas(img_cvs, img_ctx, app, cur_img, mode)
        
        # Display in our app interface
        try:
          print("  🖼️ Displaying processed frame in app interface...")
          
          processed_data_url = img_cvs.toDataURL('image/png')
          processed_data_url_with_timestamp = f"{processed_data_url}#t={Date.new().getTime()}"
          
          display_img = document.getElementById('processed-frame-display')
          status_div = document.getElementById('processed-frame-status')
          
          if display_img and status_div:
            display_img.src = processed_data_url_with_timestamp
            display_img.style.display = 'block'
            
            status_div.textContent = f"✅ Processed frame {current_frame} ({video_width}x{video_height}) - Direct video element"
            status_div.style.color = '#28a745'
            
            print(f"    ✅ Updated app display with processed frame!")
          else:
            print(f"    ❌ Could not find display elements in app interface")
            
        except Exception as e:
          print(f"  ❌ Error updating app display: {e}")
        
        return
        
      else:
        print("❌ Could not find video player elements in DOM")
        print("🔄 Attempting VideoAnnotation API access...")
        
        # Try to access frame using Supervisely VideoAnnotation API
        try:
          # Initialize Supervisely API
          print("  Initializing Supervisely API...")
          
          # Get API credentials from app context or environment
          api = None
          try:
            # Method 1: Try to get API from Supervisely app context
            if hasattr(slyApp, 'api'):
              api = slyApp.api
              print("    ✅ Using API from slyApp.api")
            elif hasattr(app, 'api'):
              api = app.api
              print("    ✅ Using API from app.api")
            elif hasattr(context, 'api'):
              api = context.api
              print("    ✅ Using API from context.api")
            
            # Method 2: Try global supervisely API access for client-side apps
            elif hasattr(slyApp, 'g') and hasattr(slyApp.g, 'api'):
              api = slyApp.g.api
              print("    ✅ Using global API from slyApp.g.api")
            
            # Method 3: Initialize API with hardcoded credentials
            else:
              # Hardcoded Supervisely API credentials
              SERVER_ADDRESS = "https://app.supervisely.com"
              API_TOKEN = "zerPjM0yd0UzBXi9EpyaVOjxoiFazNMMSvtWVlS88CL9E5boXbhWMH9k2p32iq5rM9eZ7bAROaf0dCcNNqzk5hmXz67yHFDfkkKqEtXVw8rQLv0YgbhvV2TkA4GOPKYf"  # Replace with your actual token
              TEAM_ID = 110016
              WORKSPACE_ID = 124618
              
              api = sly.Api(server_address=SERVER_ADDRESS, token=API_TOKEN)
              print("    ✅ Initialized API with hardcoded credentials")
              print(f"    Team ID: {TEAM_ID}, Workspace ID: {WORKSPACE_ID}")
              
          except Exception as e:
            print(f"    ❌ Could not initialize API: {e}")
            api = None
          
          frame_image_np = None
          api_success = False
          
          if api:
            video_id = context.imageId  # The video ID
            frame_image_np, api_success = get_video_frame_using_api(video_id, current_frame, api)
          
          if api_success and frame_image_np is not None:
            print(f"  🎯 SUCCESS: Got actual frame {current_frame} from VideoAnnotation API!")
            
            # Convert numpy array to canvas
            temp_canvas = document.createElement('canvas')
            temp_canvas.width = video_width
            temp_canvas.height = video_height
            temp_ctx = temp_canvas.getContext('2d')
            
            # Convert numpy array to ImageData
            if len(frame_image_np.shape) == 3:
              # Add alpha channel if missing
              if frame_image_np.shape[2] == 3:
                alpha_channel = np.full((frame_image_np.shape[0], frame_image_np.shape[1], 1), 255, dtype=np.uint8)
                frame_image_np = np.concatenate([frame_image_np, alpha_channel], axis=2)
            
            # Flatten and create ImageData
            flat_data = frame_image_np.flatten()
            pixels_proxy = create_proxy(flat_data)
            pixels_buf = pixels_proxy.getBuffer("u8clamped")
            frame_image_data = ImageData.new(pixels_buf.data, video_width, video_height)
            
            # Draw to canvas
            temp_ctx.putImageData(frame_image_data, 0, 0)
            
            # Clean up
            pixels_proxy.destroy()
            pixels_buf.release()
            
            img_cvs = temp_canvas
            img_ctx = temp_ctx
            
            print(f"    ✅ Frame {current_frame} converted to canvas for processing!")
            
          else:
            print(f"  ⚠️ VideoAnnotation API not available - using placeholder")
            
            # Create placeholder when API access fails
            temp_canvas = document.createElement('canvas')
            temp_canvas.width = video_width  
            temp_canvas.height = video_height
            temp_ctx = temp_canvas.getContext('2d')
            
            # Fill with placeholder
            temp_ctx.fillStyle = '#f0f0f0'
            temp_ctx.fillRect(0, 0, video_width, video_height)
            temp_ctx.fillStyle = '#333'
            temp_ctx.font = '24px Arial'
            temp_ctx.textAlign = 'center'
            temp_ctx.fillText(f"Frame {current_frame}", video_width/2, video_height/2 - 12)
            temp_ctx.fillText(f"(API Access Needed)", video_width/2, video_height/2 + 12)
            
            img_cvs = temp_canvas
            img_ctx = temp_ctx
            
            print(f"  Created placeholder canvas for frame {current_frame}")
          
          # Process the frame (real or placeholder)
          process_histogram_equalization_with_canvas(img_cvs, img_ctx, app, cur_img, mode)
          
          # Display in our app interface
          try:
            processed_data_url = img_cvs.toDataURL('image/png')
            processed_data_url_with_timestamp = f"{processed_data_url}#t={Date.new().getTime()}"
            
            display_img = document.getElementById('processed-frame-display')
            status_div = document.getElementById('processed-frame-status')
            
            if display_img and status_div:
              display_img.src = processed_data_url_with_timestamp
              display_img.style.display = 'block'
              
              if api_success:
                status_div.textContent = f"✅ Processed REAL frame {current_frame} ({video_width}x{video_height}) - VideoAnnotation API"
                status_div.style.color = '#28a745'  # Green for success
              else:
                status_div.textContent = f"📝 Processed placeholder for frame {current_frame} - API access needed"
                status_div.style.color = '#ffc107'  # Warning color
              
              print(f"    ✅ Updated app display!")
            else:
              print(f"    ❌ Could not find display elements")
              
          except Exception as e:
            print(f"  ❌ Error updating app display: {e}")
          
          return
          
        except Exception as e:
          print(f"  ❌ Error in VideoAnnotation API approach: {e}")
          return
        
    except Exception as e:
      print(f"❌ Error accessing video elements: {e}")
      return
  
  else:
    print("ERROR: Unknown media type - neither image nor video format recognized")
    return

main