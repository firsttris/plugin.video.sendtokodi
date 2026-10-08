#!/bin/bash
set -e

VERSION=$1

# check if version bump failed (will be "undefined" according to mathieudutour/github-tag-action@v5.6)
if [[ "$VERSION" == "undefined" || -z "$VERSION" ]]; then
    echo "Failed to bump or get version. Abborting build."
    exit 190
fi

# adjust plugin version
$GITHUB_WORKSPACE/.github/scripts/addon_xml_adjuster.py --plugin-version $VERSION

# create zip file. The file needs to include the plugin folder itself
cd ..
# Tests, documentation and development configuration are not part of the add-on.
zip -r "$RUNNER_TEMP/plugin.video.sendtokodi-$VERSION.zip" plugin.video.sendtokodi \
    -x "*.git*" \
       "*/__pycache__/*" \
       "plugin.video.sendtokodi/tests/*" \
       "plugin.video.sendtokodi/docs/*" \
       "plugin.video.sendtokodi/mkdocs.yml" \
       "plugin.video.sendtokodi/requirements-dev.txt" \
       "plugin.video.sendtokodi/requirements-docs.txt" \
       "plugin.video.sendtokodi/pytest.ini" \
       "plugin.video.sendtokodi/.coveragerc" \
       "plugin.video.sendtokodi/.editorconfig" \
       "plugin.video.sendtokodi/.coverage" \
       "plugin.video.sendtokodi/coverage.xml" \
       "plugin.video.sendtokodi/htmlcov/*"
