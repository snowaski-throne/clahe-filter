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
    # Handle videos - need to find current frame canvas
    print("Processing as VIDEO")
    print("Searching for video frame canvas...")
    
    # 1. Robust canvas detection with retries and timing
    try:
      from js import document, setTimeout, Promise
      import asyncio
      
      def find_video_canvas():
        """Search for video canvas with detailed logging"""
        all_canvases = document.querySelectorAll('canvas')
        print(f"  Searching {len(all_canvases)} canvas elements...")
        
        for i, canvas in enumerate(all_canvases):
          print(f"    Canvas {i}: {canvas.width}x{canvas.height}")
          if canvas.width > 0 and canvas.height > 0:
            print(f"      id='{canvas.id}', class='{canvas.className}'")
            print(f"      style: {canvas.style.cssText}")
            
            # Check for video player characteristics
            is_large = canvas.width > 1000 and canvas.height > 1000
            has_absolute_position = 'position: absolute' in canvas.style.cssText
            has_negative_z = 'z-index: -1' in canvas.style.cssText
            
            print(f"      large_dims: {is_large}, absolute_pos: {has_absolute_position}, negative_z: {has_negative_z}")
            
            if is_large or has_absolute_position or has_negative_z:
              print(f"      ^ FOUND VIDEO CANVAS! {canvas.width}x{canvas.height}")
              return canvas
        return None
      
      # Try immediate search
      print(f"\n1. Searching for video canvas (attempt 1):")
      video_frame_canvas = find_video_canvas()
      
      # If not found, wait a bit and try again
      if not video_frame_canvas:
        print(f"\n1b. Canvas not found immediately, waiting 100ms and trying again...")
        import time
        time.sleep(0.1)  # Wait 100ms
        video_frame_canvas = find_video_canvas()
      
      # Try looking in all possible containers
      if not video_frame_canvas:
        print(f"\n1c. Searching in all container elements...")
        containers = document.querySelectorAll('div, section, article, main')
        for container in containers:
          canvases_in_container = container.querySelectorAll('canvas')
          if len(canvases_in_container) > 0:
            print(f"    Found {len(canvases_in_container)} canvases in container")
            for canvas in canvases_in_container:
              if canvas.width > 500:  # Lower threshold
                print(f"      Found large canvas: {canvas.width}x{canvas.height}")
                video_frame_canvas = canvas
                break
            if video_frame_canvas:
              break
              
      if video_frame_canvas:
        print(f"\n🎯 FOUND VIDEO FRAME CANVAS!")
        print(f"  Dimensions: {video_frame_canvas.width}x{video_frame_canvas.height}")
        print(f"  Style: {video_frame_canvas.style.cssText}")
        
        # Use this canvas for CLAHE processing
        img_cvs = video_frame_canvas
        img_ctx = video_frame_canvas.getContext("2d")
        print("  Setting up for CLAHE processing...")
        
      else:
        print("❌ Still no video frame canvas found after extensive search")
        print("❌ The canvas might be created dynamically or in a different context")
        return
        
    except Exception as e:
      print(f"Error in canvas detection: {e}")
      return
    
    # Continue to CLAHE processing now that we have the video canvas
    
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