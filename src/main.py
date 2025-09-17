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
    
    # Search for canvas-like properties in the video object
    print("\nSearching cur_img for canvas properties:")
    all_props = dir(cur_img)
    canvas_props = [prop for prop in all_props if any(term in prop.lower() for term in 
                   ['canvas', 'image', 'source', 'data', 'element', 'frame', 'render', 'display'])]
    print(f"  Potential canvas properties: {canvas_props}")
    
    # Try to find video frame access similar to sources
    video_canvas = None
    video_ctx = None
    
    # Check if video has frames with canvas data for current frame
    try:
      current_frame = context.frame
      print(f"\nLooking for frame {current_frame} data...")
      
      # Check if frames object has frame-specific data
      frame_keys = Object.keys(cur_img.frames) if hasattr(cur_img, 'frames') else []
      print(f"  Available frame keys: {frame_keys}")
      
      if str(current_frame) in frame_keys:
        frame_data = getattr(cur_img.frames, str(current_frame))
        debug_js_object(frame_data, f"frame_{current_frame}")
        
        # Look for canvas in frame data
        if hasattr(frame_data, 'canvas') or hasattr(frame_data, 'imageData'):
          video_canvas = getattr(frame_data, 'canvas', None) or getattr(frame_data, 'imageData', None)
          if video_canvas:
            print(f"  Found canvas in frame data!")
            
    except Exception as e:
      print(f"  Error checking frame data: {e}")
    
    # Check fileMeta for canvas references
    try:
      print(f"\nChecking fileMeta for canvas...")
      if hasattr(cur_img, 'fileMeta'):
        debug_js_object(cur_img.fileMeta, "fileMeta")
        
        # Look for canvas properties in fileMeta
        if hasattr(cur_img.fileMeta, 'canvas') or hasattr(cur_img.fileMeta, 'imageData'):
          video_canvas = getattr(cur_img.fileMeta, 'canvas', None) or getattr(cur_img.fileMeta, 'imageData', None)
          if video_canvas:
            print(f"  Found canvas in fileMeta!")
    except Exception as e:
      print(f"  Error checking fileMeta: {e}")
    
    # Check for any other canvas-like properties
    for prop in canvas_props:
      if not video_canvas:
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
      print("❌ Videos might need a different approach than direct canvas access")
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