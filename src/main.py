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
    
    # Proof of concept: Video replacement approach
    print("Starting video replacement proof-of-concept...")
    
    try:
      from js import fetch, document, URL, Blob
      import time
      
      print(f"Will process entire video with {method}")
      if method == 'clahe':
        print(f"CLAHE clip limit: {state.SliderAutoId6MqE3.value}")
      print(f"LAB color space: {state.labCheck}")
      
      # For now, create a simple demonstration
      # In production, this would download and process the full video
      
      print("📥 Simulating video download and processing...")
      
      # Create a modified URL to simulate processing
      # In reality, you'd process the actual video frames here
      processed_video_url = f"{source_video_url}?processed={method}&lab={state.labCheck}&clip={state.SliderAutoId6MqE3.value if method == 'clahe' else 0}&timestamp={int(time.time())}"
      
      # Cache the processed video URL
      setattr(state, processed_video_key, processed_video_url)
      
      print("🔄 Replacing video player source...")
      
      # Find and replace video player sources
      video_elements = document.querySelectorAll('video')
      iframe_elements = document.querySelectorAll('iframe')
      img_elements = document.querySelectorAll('img')
      
      print(f"Found {len(video_elements)} video, {len(iframe_elements)} iframe, {len(img_elements)} img elements")
      
      updated = False
      
      # Try to update video elements
      for i, video_elem in enumerate(video_elements):
        if hasattr(video_elem, 'src') and video_elem.src:
          old_src = video_elem.src
          video_elem.src = processed_video_url
          print(f"✅ Updated video element {i}: {old_src[:50]}... -> {processed_video_url[:50]}...")
          updated = True
      
      # Try to update iframe elements (video might be in an iframe)
      for i, iframe_elem in enumerate(iframe_elements):
        if hasattr(iframe_elem, 'src') and iframe_elem.src:
          if 'video' in iframe_elem.src or '.mp4' in iframe_elem.src:
            old_src = iframe_elem.src
            iframe_elem.src = processed_video_url
            print(f"✅ Updated iframe element {i}: {old_src[:50]}... -> {processed_video_url[:50]}...")
            updated = True
      
      # Try to update img elements that might be displaying video frames
      for i, img_elem in enumerate(img_elements):
        if hasattr(img_elem, 'src') and img_elem.src:
          if '.mp4' in img_elem.src or 'video' in img_elem.src or img_elem.naturalWidth > 400:
            old_src = img_elem.src
            img_elem.src = processed_video_url
            print(f"✅ Updated img element {i}: {old_src[:50]}... -> {processed_video_url[:50]}...")
            updated = True
            break  # Only update the first large image
      
      if updated:
        print("🎉 Successfully replaced video player source!")
        print(f"📌 Cached processed video as: {processed_video_key}")
        print("💡 Note: This is a proof-of-concept. In production, the video would be fully processed.")
      else:
        print("⚠️ Warning: Could not find video player elements to update")
        print("📋 Available elements to inspect:")
        for i, elem in enumerate(video_elements):
          if hasattr(elem, 'src'):
            print(f"  Video {i}: {elem.src[:100]}...")
        for i, elem in enumerate(img_elements[:5]):  # Show first 5 images
          if hasattr(elem, 'src'):
            print(f"  Image {i}: {elem.src[:100]}... ({elem.naturalWidth}x{elem.naturalHeight})")
      
      # For full implementation, you would:
      # 1. fetch(source_video_url) to download the video
      # 2. Process each frame with OpenCV
      # 3. Reconstruct the video from processed frames
      # 4. Create a blob URL for the processed video
      # 5. Replace the video player source with the processed video blob URL
      
      print("✨ Video replacement framework ready for full implementation!")
      
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
