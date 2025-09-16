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
    
    # Video replacement approach - process entire video and replace player source
    print("=== VIDEO REPLACEMENT PROCESSING ===")
    
    # Get the original video file (not individual frames)
    try:
      # Find the source video by looking at the first frame to get the video reference
      current_frame = getattr(store.state.videos.all, str(context.imageId))
      
      # The frame should have a reference to the source video
      if hasattr(current_frame, 'fullStorageUrl'):
        source_video_url = current_frame.fullStorageUrl
        # Extract the base video URL (remove frame-specific parts if any)
        if 'frame=' in source_video_url or 'time=' in source_video_url:
          source_video_url = source_video_url.split('?')[0]  # Remove query params
      elif hasattr(current_frame, 'pathOriginal'):
        source_video_url = f"https://app.supervise.ly{current_frame.pathOriginal}"
        if 'frame=' in source_video_url or 'time=' in source_video_url:
          source_video_url = source_video_url.split('?')[0]
      else:
        print("ERROR: Could not find source video URL")
        return
      
      print(f"Source video URL: {source_video_url}")
      
    except Exception as e:
      print(f"Error getting video URL: {e}")
      return
    
    # Create a unique key for this processing configuration
    config_key = f"{method}_{state.labCheck}_{state.SliderAutoId6MqE3.value if method == 'clahe' else 'hist'}"
    processed_video_key = f"processed_video_{config_key}"
    
    # Store original video URL for restore functionality
    if not hasattr(state, 'originalVideoUrl'):
      state.originalVideoUrl = source_video_url
      print(f"Stored original video URL: {source_video_url}")
    
    if mode == 'restore':
      # Restore original video in player
      print("Restoring original video...")
      try:
        from js import document
        # Find and update video elements
        video_elements = document.querySelectorAll('video')
        img_elements = document.querySelectorAll('img[src*=".mp4"], img[src*="video"]')
        
        updated = False
        for video_elem in video_elements:
          if hasattr(video_elem, 'src'):
            video_elem.src = state.originalVideoUrl
            print(f"Restored video element to: {state.originalVideoUrl}")
            updated = True
            break
            
        # Also check for img elements that might be showing video frames
        for img_elem in img_elements:
          if hasattr(img_elem, 'src'):
            img_elem.src = state.originalVideoUrl
            print(f"Restored img element to: {state.originalVideoUrl}")
            updated = True
            
        if not updated:
          print("Warning: No video elements found to restore")
      except Exception as e:
        print(f"Error restoring video: {e}")
      return
    
    # Check if already processed with current settings
    if hasattr(state, processed_video_key):
      print(f"Using cached processed video for {method}")
      processed_blob_url = getattr(state, processed_video_key)
      try:
        from js import document
        video_elements = document.querySelectorAll('video')
        img_elements = document.querySelectorAll('img[src*=".mp4"], img[src*="video"]')
        
        updated = False
        for video_elem in video_elements:
          if hasattr(video_elem, 'src'):
            video_elem.src = processed_blob_url
            print(f"Updated video element to cached processed version")
            updated = True
            break
            
        for img_elem in img_elements:
          if hasattr(img_elem, 'src'):
            img_elem.src = processed_blob_url
            print(f"Updated img element to cached processed version")
            updated = True
            
        if not updated:
          print("Warning: No video elements found to update")
      except Exception as e:
        print(f"Error updating video: {e}")
      return
    
    # Download and process the entire video
    print("Starting video download and processing...")
    
    try:
      from js import fetch, document, URL, Blob, HTMLVideoElement, HTMLCanvasElement
      import asyncio
      
      print(f"Processing video with {method}")
      if method == 'clahe':
        print(f"CLAHE clip limit: {state.SliderAutoId6MqE3.value}")
      print(f"LAB color space: {state.labCheck}")
      
      # Create a canvas to process the current frame image
      canvas = document.createElement('canvas')
      ctx = canvas.getContext('2d')
      
      # Load and process the current frame
      img = document.createElement('img')
      img.crossOrigin = 'anonymous'
      
      def on_image_load():
        print(f"Frame loaded: {img.naturalWidth}x{img.naturalHeight}")
        
        # Set canvas size to match image
        canvas.width = img.naturalWidth
        canvas.height = img.naturalHeight
        
        # Draw image to canvas
        ctx.drawImage(img, 0, 0)
        
        try:
          # Get image data for processing
          img_data = ctx.getImageData(0, 0, canvas.width, canvas.height)
          img_array = np.array(img_data.data, dtype=np.uint8).reshape(canvas.height, canvas.width, 4)
          
          print(f"Processing frame with {method}...")
          
          # Apply your image processing
          if method == 'clahe':
            clip_limit = state.SliderAutoId6MqE3.value
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
            
            if state.labCheck:
              img_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
              img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
              lab_planes = list(cv2.split(img_lab))
              lab_planes[0] = clahe.apply(lab_planes[0])
              img_lab = cv2.merge(lab_planes)
              enhanced_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
            else:
              img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
              enhanced_gray = clahe.apply(img_gray)
              enhanced_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
          else:  # histogram equalization
            if state.labCheck:
              img_rgb = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
              img_lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB)
              lab_planes = list(cv2.split(img_lab))
              lab_planes[0] = cv2.equalizeHist(lab_planes[0])
              img_lab = cv2.merge(lab_planes)
              enhanced_rgb = cv2.cvtColor(img_lab, cv2.COLOR_LAB2RGB)
            else:
              img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGBA2GRAY)
              enhanced_gray = cv2.equalizeHist(img_gray)
              enhanced_rgb = cv2.cvtColor(enhanced_gray, cv2.COLOR_GRAY2RGB)
          
          # Convert back to RGBA
          alpha_channel = img_array[:, :, 3]
          enhanced_img = np.dstack((enhanced_rgb, alpha_channel))
          
          # Put processed frame back to canvas
          processed_data = enhanced_img.flatten().astype(np.uint8)
          pixels_proxy = create_proxy(processed_data)
          pixels_buf = pixels_proxy.getBuffer("u8clamped")
          new_img_data = ImageData.new(pixels_buf.data, canvas.width, canvas.height)
          ctx.putImageData(new_img_data, 0, 0)
          
          # Convert canvas to data URL (simpler than blob)
          processed_data_url = canvas.toDataURL('image/png')
          setattr(state, processed_video_key, processed_data_url)
          
          print(f"Created processed frame data URL")
          
          # Find and update image/video elements showing the current frame
          all_imgs = document.querySelectorAll('img')
          all_videos = document.querySelectorAll('video')
          
          print(f"Found {len(all_imgs)} img elements and {len(all_videos)} video elements")
          
          updated = False
          for i, img_elem in enumerate(all_imgs):
            if hasattr(img_elem, 'src'):
              print(f"Image {i}: {img_elem.src[:100]}... size: {img_elem.naturalWidth}x{img_elem.naturalHeight}")
              # Try to find the current frame image
              if (str(context.imageId) in img_elem.src or 
                  img_elem.naturalWidth == canvas.width and img_elem.naturalHeight == canvas.height or
                  img_elem.naturalWidth > 400):  # Large images are likely the main frame
                img_elem.src = processed_data_url
                print(f"✓ Updated image element {i} with processed frame")
                updated = True
                break
          
          if not updated:
            # Fallback: update the first large image
            for i, img_elem in enumerate(all_imgs):
              if hasattr(img_elem, 'naturalWidth') and img_elem.naturalWidth > 100:
                img_elem.src = processed_data_url
                print(f"✓ Updated fallback image element {i} with processed frame")
                updated = True
                break
          
          if not updated:
            print("⚠ Warning: Could not find suitable image element to update")
          else:
            print("🎉 Successfully updated image with processed frame!")
          
          pixels_proxy.destroy()
          pixels_buf.release()
          
        except Exception as processing_error:
          print(f"Error during frame processing: {processing_error}")
          import traceback
          traceback.print_exc()
      
      def on_image_error():
        print(f"Failed to load frame image: {source_video_url}")
        print("This might be due to CORS restrictions")
      
      img.onload = on_image_load
      img.onerror = on_image_error
      img.src = source_video_url
      
    except Exception as e:
      print(f"Error in video processing: {e}")
      import traceback
      traceback.print_exc()
      
      # Fallback: just show that processing was attempted
      print(f"Video processing attempted with {method}")
      print("Note: This is a proof-of-concept. Full video processing requires additional implementation.")
    
  except Exception as e:
    print(f"Error in main function: {str(e)}")
    import traceback
    traceback.print_exc()

main
