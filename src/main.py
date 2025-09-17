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

  # Debug comprehensive object information
  debug_js_object(store, "store")
  debug_js_object(store.state, "store.state")
  debug_js_object(store.state.videos, "store.state.videos")
  debug_js_object(context, "context")
  debug_js_object(state, "state")
  
  print(f"context.imageId: {context.imageId}")
  
  # Try to debug store.state.videos.all if it exists
  try:
    debug_js_object(store.state.videos.all, "store.state.videos.all")
  except Exception as e:
    print(f"Error accessing store.state.videos.all: {e}")
  
  cur_img = getattr(store.state.videos.all, str(context.imageId))
  
  # Debug the current image object
  debug_js_object(cur_img, "cur_img")
  
  # Debug frames object for videos
  try:
    debug_js_object(cur_img.frames, "cur_img.frames")
  except Exception as e:
    print(f"Error accessing cur_img.frames: {e}")
  
  # Check context for frame information
  print(f"\nContext frameIndex: {getattr(context, 'frameIndex', 'NOT FOUND')}")
  print(f"Context currentFrame: {getattr(context, 'currentFrame', 'NOT FOUND')}")
  
  # Look for frame-related data in context
  try:
    debug_js_object(context, "context_detailed")
  except Exception as e:
    print(f"Error debugging context: {e}")
  
  # Check if there's frame data in store.state
  try:
    frame_keys = [key for key in Object.keys(store.state) if 'frame' in key.lower()]
    print(f"Store.state keys containing 'frame': {frame_keys}")
    
    for key in frame_keys:
      try:
        debug_js_object(getattr(store.state, key), f"store.state.{key}")
      except Exception as e:
        print(f"Error accessing store.state.{key}: {e}")
  except Exception as e:
    print(f"Error checking store.state for frame data: {e}")
  
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
    debug_js_object(img_src, "img_src")
    
    img_cvs = img_src.imageData
    debug_js_object(img_cvs, "img_cvs")

    img_ctx = img_cvs.getContext("2d")
    debug_js_object(img_ctx, "img_ctx")
  
  elif is_video:
    # Handle videos - need to find current frame canvas
    print("Processing as VIDEO")
    print("Searching for video frame canvas...")
    
    # 1. Check DOM for canvas elements
    try:
      from js import document
      video_canvases = document.querySelectorAll('canvas')
      print(f"\n1. Found {len(video_canvases)} canvas elements in DOM:")
      
      for i, canvas in enumerate(video_canvases):
        if canvas.width > 0 and canvas.height > 0:
          print(f"  Canvas {i}: {canvas.width}x{canvas.height}, id='{canvas.id}', class='{canvas.className}'")
          # Check if this canvas might be the video player
          ctx = canvas.getContext("2d")
          img_data = ctx.getImageData(0, 0, min(10, canvas.width), min(10, canvas.height))
          has_data = any(img_data.data)
          print(f"    Has image data: {has_data}")
    except Exception as e:
      print(f"Error checking DOM canvases: {e}")
    
    # 2. Search store.state for video player objects
    try:
      print(f"\n2. Searching store.state for video/player objects:")
      all_keys = Object.keys(store.state)
      video_keys = [key for key in all_keys if any(term in key.lower() for term in ['video', 'player', 'canvas', 'frame', 'media'])]
      print(f"  Potential video-related keys: {video_keys}")
      
      # Debug store.state.videos in detail
      if 'videos' in video_keys:
        print("\n  DETAILED DEBUG of store.state.videos:")
        debug_js_object(store.state.videos, "store.state.videos")
        
        # Check if videos has current/active properties
        videos_keys = Object.keys(store.state.videos)
        print(f"    videos keys: {videos_keys}")
        
        for key in videos_keys:
          try:
            obj = getattr(store.state.videos, key)
            print(f"    videos.{key}: {type(obj)}")
            if str(type(obj)) == "<class 'pyodide.ffi.JsProxy'>" and key in ['current', 'active', 'player', 'canvas']:
              debug_js_object(obj, f"store.state.videos.{key}")
          except Exception as e:
            print(f"    Error accessing videos.{key}: {e}")
      
      for key in video_keys:
        if key != 'videos':  # Already handled above
          try:
            obj = getattr(store.state, key)
            print(f"  {key}: {type(obj)}")
            if hasattr(obj, 'canvas') or hasattr(obj, 'imageData'):
              debug_js_object(obj, f"store.state.{key}")
          except Exception as e:
            print(f"  Error accessing {key}: {e}")
    except Exception as e:
      print(f"Error searching store.state: {e}")
    
    # 2b. Check for video elements in DOM (not canvas)
    try:
      print(f"\n2b. Checking for <video> elements in DOM:")
      video_elements = document.querySelectorAll('video')
      print(f"  Found {len(video_elements)} video elements:")
      
      for i, video in enumerate(video_elements):
        print(f"    Video {i}: {video.videoWidth}x{video.videoHeight}, currentTime={video.currentTime}")
        print(f"      src: {video.src}")
        print(f"      readyState: {video.readyState}")
        
        # Try to create a canvas from the video
        if video.videoWidth > 0 and video.videoHeight > 0:
          print(f"      ^ This video element has dimensions and might be our target!")
    except Exception as e:
      print(f"Error checking video elements: {e}")
    
    # 3. Look for canvas-related properties on the app object
    try:
      print(f"\n3. Searching app for canvas/video objects:")
      app_keys = Object.keys(app)
      canvas_keys = [key for key in app_keys if any(term in key.lower() for term in ['canvas', 'video', 'player', 'media'])]
      print(f"  Potential canvas-related app keys: {canvas_keys}")
      
      for key in canvas_keys:
        try:
          obj = getattr(app, key)
          print(f"  app.{key}: {type(obj)}")
          if str(type(obj)) == "<class 'pyodide.ffi.JsProxy'>":
            debug_js_object(obj, f"app.{key}")
        except Exception as e:
          print(f"  Error accessing app.{key}: {e}")
    except Exception as e:
      print(f"Error searching app: {e}")
    
    # 4. Check the video object for any canvas-related properties
    try:
      print(f"\n4. Detailed search in cur_img for canvas properties:")
      all_props = dir(cur_img)
      canvas_props = [prop for prop in all_props if any(term in prop.lower() for term in ['canvas', 'image', 'source', 'data', 'element'])]
      print(f"  Canvas-related properties: {canvas_props}")
      
      for prop in canvas_props:
        try:
          value = getattr(cur_img, prop)
          print(f"  cur_img.{prop}: {type(value)} = {value}")
          if hasattr(value, 'getContext'):
            print(f"    ^ This looks like a canvas!")
        except Exception as e:
          print(f"  Error accessing cur_img.{prop}: {e}")
    except Exception as e:
      print(f"Error searching cur_img properties: {e}")
    
    return  # Exit for now until we figure out video frame access
    
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