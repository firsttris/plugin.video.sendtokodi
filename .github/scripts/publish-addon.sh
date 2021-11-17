#!/bin/bash
set -e
# Publish the addon to the python2/3 kodi repo. 
# This script needs build-addon to be run shortly before in the same job.

REPO_NAME=$1
REPO_URL=$2
if [[ $GITHUB_REPOSITORY == "firsttris/plugin.video.sendtokodi" ]]; then
    # add the created zip file, commit and push
    cd $REPO_NAME/
    envsubst < "addon.template.xml" > "addon.xml"
    md5sum addon.xml > addon.xml.md5
    git add .
    git commit -m "CI Update"
    git push --force --quiet "https://firsttris:$TOKEN@$REPO_URL" master
else 
    echo "Not in the main repo, build will not be released."
fi 
