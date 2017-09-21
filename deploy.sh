eval "$(ssh-agent -s)" # Start the ssh agent
echo "$GH_TOKEN" > deploy_key.pem
chmod 600 deploy_key.pem
ssh-add deploy_key.pem
git config user.name "Travis-CI"
git config user.email "travis@teufel-it.de"
cd repository.sendtokodi/
git add .
git commit -m "Travis-CI Update"
git push