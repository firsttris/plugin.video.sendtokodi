rm -rf .git/
# LATER envsubst < "addon.template.xml" > "addon.xml"
git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
git config --global user.name "github-actions[bot]"

cd ..
# youtube_dl
wget ${YOUTUBE_DL}
unzip master.zip
cp -R youtube-dl-master/youtube_dl ${ADDON_NAME}
# clone repo
git clone https://${GH_REPO}
git clone https://${GH_REPO_PYTHON3}
# package python 2 addon
envsubst < "${REPO_NAME}/${ADDON_NAME}/addon.template.xml" > "${REPO_NAME}/${ADDON_NAME}/addon.xml" # python 2 addon.xml
cp ${REPO_NAME}/${ADDON_NAME}/addon.xml ${ADDON_NAME} # copy python 2 addon.xml to addon folder
zip -r ${ADDON_NAME}-${VERSION}.zip ${ADDON_NAME} # create zip for python 2
cp ${ADDON_NAME}-${VERSION}.zip ${REPO_NAME}/${ADDON_NAME}/ # copy source code to python 2 repo
# package python 3 addon
envsubst < "${REPO_NAME_PYTHON3}/${ADDON_NAME}/addon.template.xml" > "${REPO_NAME_PYTHON3}/${ADDON_NAME}/addon.xml" #python 3 addon.xml
rm ${ADDON_NAME}/addon.xml # remove previous python 2 addon.xml
cp ${REPO_NAME_PYTHON3}/${ADDON_NAME}/addon.xml ${ADDON_NAME} # copy python 3 addon.xml to addon folder
zip -r ${ADDON_NAME}-${VERSION}.zip ${ADDON_NAME} # create zip for python 3
cp ${ADDON_NAME}-${VERSION}.zip ${REPO_NAME_PYTHON3}/${ADDON_NAME}/ # copy source code to python 3 repo
# commit & push to python 2 repo
cd ${REPO_NAME}/
envsubst < "addon.template.xml" > "addon.xml"
md5sum addon.xml > addon.xml.md5
git add .
git commit -m "CI Update"
git push
# go back one folder
cd ..
# commit & push to python 3 repo
cd ${REPO_NAME_PYTHON3}/
envsubst < "addon.template.xml" > "addon.xml"
md5sum addon.xml > addon.xml.md5
git add .
git commit -m "CI Update"
git push