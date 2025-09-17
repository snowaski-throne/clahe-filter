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
  
  img_src = cur_img.sources[0]
  debug_js_object(img_src, "img_src")
  
  img_cvs = img_src.imageData
  debug_js_object(img_cvs, "img_cvs")

  img_ctx = img_cvs.getContext("2d")
  debug_js_object(img_ctx, "img_ctx")

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