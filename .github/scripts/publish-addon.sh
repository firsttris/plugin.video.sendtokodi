#!/bin/bash
set -e
# Publish the addon to the python2/3 kodi repo. 
# This script needs build-addon to be run shortly before (so the repos are cloned and the addons are built)

REPO_NAME=$1
REPO_URL=$2
if [[ $GITHUB_REPOSITORY == "firsttris/plugin.video.sendtokodi" ]]; then
    # add the created zip file, commit and push
    cd $REPO_NAME/
    # Update repository addon xml to include the latest version of sendtokodi
    envsubst < "addon.template.xml" > "addon.xml"  
    md5sum addon.xml > addon.xml.md5
    # Add new addon zip file and repo addon.xml, its md5 hash file then commit and push
    git add .
    git commit -m "CI Update"
    git push --force --quiet "https://firsttris:$TOKEN@$REPO_URL" master
else 
    echo "Not in the main repo, build will not be released."
fi 
