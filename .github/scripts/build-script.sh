REPO_NAME=$1
REPO_URL=$2

touch lib/youtubeDL/__init__.py

cd ..
# clone repo
git clone https://$REPO_URL

# package addon
envsubst < "$REPO_NAME/$ADDON_NAME/addon.template.xml" > "$REPO_NAME/$ADDON_NAME/addon.xml" # addon.xml
cp $REPO_NAME/$ADDON_NAME/addon.xml $ADDON_NAME # copy addon.xml to addon folder
zip -r $ADDON_NAME-$VERSION.zip $ADDON_NAME # create zip
cp $ADDON_NAME-$VERSION.zip $REPO_NAME/$ADDON_NAME/ # copy source code to repo

# commit & push
cd $REPO_NAME/
envsubst < "addon.template.xml" > "addon.xml"
md5sum addon.xml > addon.xml.md5
git add .
git commit -m "CI Update"
git push --force --quiet "https://firsttris:$TOKEN@$REPO_URL" master