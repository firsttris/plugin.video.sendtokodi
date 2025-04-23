#!/bin/bash
set -e
# this script publishes the addon zip file to the unofficial python2/3 kodi repo

VERSION=$1
REPO_URL=$2
REPO_FOLDER=release_repo

# check if action was triggered in a fork and avoid trying to push. FOR TESTING DISABLED
if [[ $GITHUB_REPOSITORY == "firsttris/plugin.video.sendtokodi" ]]; then
    # clone repo
    git clone https://$REPO_URL $REPO_FOLDER

    # add the plugin zip file
    mv plugin.video.sendtokodi-$VERSION.zip $REPO_FOLDER/plugin.video.sendtokodi/

    # Update repository's addon.xml with the addon's addon.xml
    $GITHUB_WORKSPACE/.github/scripts/update-repo-xml.py --repo-root $REPO_FOLDER
    cd $REPO_FOLDER
    md5sum addon.xml > addon.xml.md5

    # Add new addon zip file, the repo addon.xml, its md5 hash file and then commit and push
    git config --global user.name "github-actions[bot]"
    git config --global user.email "github-actions[bot]@users.noreply.github.com"
    git add .
    git commit -m "CI Update for $VERSION"
    git push --force --quiet "https://firsttris:$TOKEN@$REPO_URL" master
else
    echo "Not in the main repo, build will not be published."
fi