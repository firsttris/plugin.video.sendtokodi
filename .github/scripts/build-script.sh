REPO_NAME=$1
REPO_URL=$2

set -e # if one command fails, abort the whole build and release process

# create init in libs 
touch lib/youtubeDL/__init__.py
touch lib/ytDLP/__init__.py

# clone repo
cd ..
git clone https://$REPO_URL

# package addon
envsubst < "$REPO_NAME/$ADDON_NAME/addon.template.xml" > "$REPO_NAME/$ADDON_NAME/addon.xml" # addon.xml
cp $REPO_NAME/$ADDON_NAME/addon.xml $ADDON_NAME # copy addon.xml to addon folder
zip -r $ADDON_NAME-$VERSION.zip $ADDON_NAME  -x "*.git*" # create zip
cp $ADDON_NAME-$VERSION.zip $REPO_NAME/$ADDON_NAME/ # copy source code to repo

# commit & push if the ci was triggered by the main repo (diables trying to release for forks)
if [[ $GITHUB_REPOSITORY == "firsttris/plugin.video.sendtokodi" ]]; then
    cd $REPO_NAME/
    envsubst < "addon.template.xml" > "addon.xml"
    md5sum addon.xml > addon.xml.md5
    git add .
    git commit -m "CI Update"
    git push --force --quiet "https://firsttris:$TOKEN@$REPO_URL" master
else 
    echo "Not in the main repo, build will not be released."
fi