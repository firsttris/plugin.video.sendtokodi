#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for deno_manager module
Run this outside of Kodi to test Deno download and detection
"""

import sys
import os

# Add lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'lib'))

import deno_manager

def test_platform_detection():
    """Test platform detection"""
    print("=" * 60)
    print("Platform Detection Test")
    print("=" * 60)
    
    try:
        platform_info = deno_manager.get_platform_info()
        print("✓ Platform:", platform_info[0])
        print("✓ Architecture:", platform_info[1])
        print("✓ File extension:", platform_info[2])
        print("✓ Binary name:", platform_info[3])
        
        filename = deno_manager.get_deno_filename(platform_info[0], platform_info[1])
        print("✓ Download filename:", filename)
        return True
    except Exception as e:
        print("✗ Error:", str(e))
        return False


def test_deno_detection():
    """Test if Deno is already available"""
    print("\n" + "=" * 60)
    print("Deno Detection Test")
    print("=" * 60)
    
    deno_path = deno_manager.is_deno_available()
    
    if deno_path:
        print("✓ Deno found at:", deno_path)
        return True
    else:
        print("ℹ Deno not found on system")
        return False


def test_deno_paths():
    """Test Deno path configuration"""
    print("\n" + "=" * 60)
    print("Deno Paths Test")
    print("=" * 60)
    
    try:
        deno_dir = deno_manager.get_deno_dir()
        deno_path = deno_manager.get_deno_path()
        
        print("✓ Deno directory:", deno_dir)
        print("✓ Deno binary path:", deno_path)
        print("✓ Directory exists:", os.path.exists(deno_dir))
        print("✓ Binary exists:", os.path.exists(deno_path))
        return True
    except Exception as e:
        print("✗ Error:", str(e))
        return False


def test_ydl_config():
    """Test yt-dlp configuration generation"""
    print("\n" + "=" * 60)
    print("yt-dlp Configuration Test")
    print("=" * 60)
    
    try:
        config = deno_manager.get_ydl_deno_config(auto_download=False)
        
        if config:
            print("✓ Configuration generated:")
            for key, value in config.items():
                print(f"  {key}: {value}")
            return True
        else:
            print("ℹ No configuration (Deno not available)")
            return False
    except Exception as e:
        print("✗ Error:", str(e))
        return False


def test_deno_download():
    """Test Deno download (interactive)"""
    print("\n" + "=" * 60)
    print("Deno Download Test")
    print("=" * 60)
    
    # Check if already available
    if deno_manager.is_deno_available():
        print("ℹ Deno already available, skipping download test")
        print("  To test download, remove the Deno directory:")
        print(" ", deno_manager.get_deno_dir())
        return True
    
    # Ask user if they want to test download
    response = input("\nDeno not found. Download it now? (~100MB) [y/N]: ")
    
    if response.lower() not in ['y', 'yes']:
        print("ℹ Download test skipped")
        return True
    
    print("\nDownloading Deno...")
    try:
        deno_path = deno_manager.ensure_deno_available(auto_download=True)
        
        if deno_path:
            print("✓ Deno downloaded successfully to:", deno_path)
            print("\n✓ Testing Deno binary...")
            
            # Test the binary
            import subprocess
            result = subprocess.run([deno_path, '--version'], 
                                   capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print("✓ Deno version:")
                print(result.stdout)
                return True
            else:
                print("✗ Deno binary test failed")
                return False
        else:
            print("✗ Download failed")
            return False
            
    except Exception as e:
        print("✗ Error:", str(e))
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\nDeno Manager Test Suite")
    print("=" * 60)
    
    tests = [
        ("Platform Detection", test_platform_detection),
        ("Deno Paths", test_deno_paths),
        ("Deno Detection", test_deno_detection),
        ("yt-dlp Config", test_ydl_config),
        ("Deno Download", test_deno_download),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed:", str(e))
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
