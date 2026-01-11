#!/bin/bash
# Verification script for Deno integration

echo "=========================================="
echo "SendToKodi Deno Integration Verification"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "service.py" ]; then
    echo "❌ Error: Must run from plugin.video.sendtokodi directory"
    exit 1
fi

echo "✓ In correct directory"
echo ""

# Check if required files exist
echo "Checking required files..."
FILES=(
    "lib/deno_manager.py"
    "resources/settings.xml"
    "resources/language/resource.language.en_gb/strings.po"
    "docs/DENO_INTEGRATION.md"
    "test_deno_manager.py"
    "example_deno_usage.py"
)

MISSING=0
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ❌ Missing: $file"
        MISSING=$((MISSING + 1))
    fi
done

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "❌ $MISSING file(s) missing"
    exit 1
fi

echo ""
echo "✓ All required files present"
echo ""

# Check Python syntax
echo "Checking Python syntax..."
python3 -m py_compile lib/deno_manager.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ deno_manager.py"
else
    echo "  ❌ deno_manager.py has syntax errors"
    exit 1
fi

python3 -m py_compile service.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ service.py"
else
    echo "  ❌ service.py has syntax errors"
    exit 1
fi

python3 -m py_compile test_deno_manager.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ test_deno_manager.py"
else
    echo "  ❌ test_deno_manager.py has syntax errors"
    exit 1
fi

python3 -m py_compile example_deno_usage.py 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ example_deno_usage.py"
else
    echo "  ❌ example_deno_usage.py has syntax errors"
    exit 1
fi

echo ""
echo "✓ All Python files have valid syntax"
echo ""

# Check if key strings are present in settings
echo "Checking settings configuration..."
if grep -q "deno_autodownload" resources/settings.xml; then
    echo "  ✓ deno_autodownload setting present"
else
    echo "  ❌ deno_autodownload setting missing"
    exit 1
fi

if grep -q "youtube_suppress_js_warning" resources/settings.xml; then
    echo "  ✓ youtube_suppress_js_warning setting present"
else
    echo "  ❌ youtube_suppress_js_warning setting missing"
    exit 1
fi

echo ""
echo "✓ Settings configured correctly"
echo ""

# Check if language strings are present
echo "Checking language strings..."
if grep -q "#32023" resources/language/resource.language.en_gb/strings.po; then
    echo "  ✓ String #32023 (Deno auto-download) present"
else
    echo "  ❌ String #32023 missing"
    exit 1
fi

if grep -q "#32024" resources/language/resource.language.en_gb/strings.po; then
    echo "  ✓ String #32024 (JS warning) present"
else
    echo "  ❌ String #32024 missing"
    exit 1
fi

echo ""
echo "✓ Language strings configured correctly"
echo ""

# Check service.py integration
echo "Checking service.py integration..."
if grep -q "from deno_manager import get_ydl_deno_config" service.py; then
    echo "  ✓ deno_manager import present"
else
    echo "  ❌ deno_manager import missing"
    exit 1
fi

if grep -q "deno_autodownload" service.py; then
    echo "  ✓ deno_autodownload usage present"
else
    echo "  ❌ deno_autodownload usage missing"
    exit 1
fi

if grep -q "js_runtimes" lib/deno_manager.py; then
    echo "  ✓ js_runtimes configuration present"
else
    echo "  ❌ js_runtimes configuration missing"
    exit 1
fi

echo ""
echo "✓ service.py integration complete"
echo ""

# Test deno_manager module import
echo "Testing module imports..."
python3 -c "import sys; sys.path.insert(0, 'lib'); import deno_manager; print('  ✓ deno_manager imports successfully')" 2>&1
if [ $? -ne 0 ]; then
    echo "  ❌ deno_manager import failed"
    exit 1
fi

echo ""
echo "✓ Module imports working"
echo ""

# Summary
echo "=========================================="
echo "✓ All verification checks passed!"
echo "=========================================="
echo ""
echo "Integration is ready. Next steps:"
echo ""
echo "1. Test outside Kodi:"
echo "   python3 test_deno_manager.py"
echo ""
echo "2. Test with yt-dlp:"
echo "   python3 example_deno_usage.py"
echo ""
echo "3. Install in Kodi and test with YouTube URLs"
echo ""
echo "For more information, see:"
echo "  - docs/DENO_INTEGRATION.md"
echo ""
