#!/bin/bash
set -e

VERSION=$1
KODI_TARGET=$2

# check if version bump failed (will be "undefined" according to mathieudutour/github-tag-action@v5.6)
if [[ "$VERSION" == "undefined" || -z "$VERSION" ]]; then
    echo "Failed to bump or get version. Abborting build."
    exit 190
fi

# based on the targeting kodi version different adjustments must be made. Further information here: https://kodi.wiki/view/Addon.xml
# xmlstarlet or a python xml wrapper would be more robust than sed
case $KODI_TARGET in
  "Leia")
    echo -n "TODO"
    $GITHUB_WORKSPACE/.github/scripts/addon_xml_adjuster.py --plugin-version $VERSION --xbmc-python "2.25.0"
    build_folder=Leia
    ;;

  "Matrix" | "Nexus")
    $GITHUB_WORKSPACE/.github/scripts/addon_xml_adjuster.py --plugin-version $VERSION --xbmc-python "3.0.0"
    build_folder=Matrix
    ;;
  *)
    echo -n "Unknown kodi version as target. Aborting build."
    exit 191
    ;;
esac

mkdir $RUNNER_TEMP/${build_folder}
# create zip file. The file needs to include the plugin folder itself  
cd ..
zip -r $RUNNER_TEMP/${build_folder}/plugin.video.sendtokodi-$VERSION.zip plugin.video.sendtokodi -x "*.git*" # create zip
