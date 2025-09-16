from js import ImageData, Object, slyApp
from pyodide.ffi import create_proxy
import numpy as np
import cv2


def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %r" % (attr, getattr(obj, attr)))

def main(mode='process', method='hist'):
  app = slyApp.app
  store = slyApp.store
  app = getattr(app, '$children')[0]

  context = app.context
  state = app.state

  # Video frame handling - access current frame data
  # context.imageId represents the current video frame when in video annotation tool
  cur_img = getattr(store.state.videos.all, str(context.imageId))
  img_src = cur_img.sources[0]
  img_cvs = img_src.imageData

  img_ctx = img_cvs.getContext("2d")

  # Cache frame data to avoid reprocessing the same frame
  # This is especially important for video where users might navigate back and forth
  if state.imagePixelsDataImageId != context.imageId:
    img_data = img_ctx.getImageData(0, 0, img_cvs.width, img_cvs.height).data

    # Reshape flat array of rgba to numpy for OpenCV processing
    state.imagePixelsData = np.array(img_data, dtype=np.uint8).reshape(img_cvs.height, img_cvs.width, 4)
    state.imagePixelsDataImageId = context.imageId
    
    # Store original frame data for restore functionality
    if not hasattr(state, 'originalFrameData') or state.originalFrameData is None:
      state.originalFrameData = {}
    state.originalFrameData[context.imageId] = state.imagePixelsData.copy()


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
        img_lab = cv2.cvtColor(img_arr, cv2.COLOR_RGB2LAB)
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
        img_lab = cv2.cvtColor(img_arr, cv2.COLOR_RGB2LAB)
        lab_planes = list(cv2.split(img_lab))
        lab_planes[0] = cv2.equalizeHist(lab_planes[0])
        img_lab = cv2.merge(lab_planes)
        enhanced_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
      
    alpha_channel = img_arr[:, :, 3]
    enhanced_img = np.dstack((enhanced_rgb, alpha_channel))

    new_img_data = enhanced_img.flatten().astype(np.uint8)

  pixels_proxy = create_proxy(new_img_data)
  pixels_buf = pixels_proxy.getBuffer("u8clamped")
  new_img_data = ImageData.new(pixels_buf.data, img_cvs.width, img_cvs.height)

  img_ctx.putImageData(new_img_data, 0, 0)
  img_src.version += 1

  pixels_proxy.destroy()
  pixels_buf.release()

main
