#!/bin/bash
set -e

REPO_NAME=$1
REPO_URL=$2

# clone release repo (just needed for the correct addon.xml, TODO decide if addon.xml should be in the main development repo and not the release repo)
cd ..
git clone https://$REPO_URL

# package addon
envsubst < "$REPO_NAME/$ADDON_NAME/addon.template.xml" > "$REPO_NAME/$ADDON_NAME/addon.xml" # addon.xml
cp $REPO_NAME/$ADDON_NAME/addon.xml $ADDON_NAME # copy addon.xml to addon folder
zip -r $REPO_NAME/$ADDON_NAME/$ADDON_NAME-$VERSION.zip $ADDON_NAME -x "*.git*" # create zip