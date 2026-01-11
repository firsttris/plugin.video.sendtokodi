#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Example: Using deno_manager with yt-dlp

This example demonstrates how to use the deno_manager module
to configure yt-dlp with Deno JavaScript runtime support.
"""

import sys
import os

# Add the lib directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

from yt_dlp import YoutubeDL
from deno_manager import get_ydl_deno_config

def main():
    """
    Example: Extract a YouTube video with Deno support
    """
    
    # YouTube URL to test
    url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    
    print("=" * 60)
    print("yt-dlp with Deno Integration Example")
    print("=" * 60)
    
    # Basic yt-dlp options
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
    }
    
    # Get Deno configuration
    print("\n1. Configuring Deno JavaScript runtime...")
    deno_config = get_ydl_deno_config(auto_download=True)
    
    if deno_config:
        print("   ✓ Deno configuration obtained:")
        for key, value in deno_config.items():
            print(f"     {key}: {value}")
        
        # Merge Deno config into yt-dlp options
        ydl_opts.update(deno_config)
    else:
        print("   ⚠ Deno not available - extraction may have limited functionality")
        print("   Continuing without Deno...")
    
    # Extract video information
    print(f"\n2. Extracting video info from: {url}")
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            print("\n3. Extraction successful!")
            print("   ✓ Title:", info.get('title', 'N/A'))
            print("   ✓ Duration:", info.get('duration', 'N/A'), "seconds")
            print("   ✓ Uploader:", info.get('uploader', 'N/A'))
            
            # Show available formats
            formats = info.get('formats', [])
            print(f"   ✓ Available formats: {len(formats)}")
            
            # Show some format details
            print("\n   Sample formats:")
            for fmt in formats[:5]:  # Show first 5 formats
                print(f"     - {fmt.get('format_id', '?')}: "
                      f"{fmt.get('format_note', 'N/A')} "
                      f"({fmt.get('ext', 'N/A')}) "
                      f"- vcodec: {fmt.get('vcodec', 'none')}, "
                      f"acodec: {fmt.get('acodec', 'none')}")
            
            print(f"\n   ... and {max(0, len(formats) - 5)} more formats")
            
            print("\n✓ Example completed successfully!")
            return 0
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
