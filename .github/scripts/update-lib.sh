#!/bin/bash
set -e
# Updates a single library (stored as plain files, not as a git submodule) by comparing it's local commit (stored in a file) and the latest remote commit  
# In case the remote commit is different, this script clones the remote repo and adds just the desired folder to our repo. 
LIB_NAME=$1    
LIB_GIT_URL=$2
LIB_UPSTREAM_FOLDER=$3
LIB_VERSION_FILE=${GITHUB_WORKSPACE}/lib/${LIB_NAME}_version


commit_upstream=$(git ls-remote $LIB_GIT_URL HEAD | awk '{ print $1 }')
commit_local=$(<${LIB_VERSION_FILE})


if [[ "$commit_upstream" == "$commit_local" ]]; then
    echo "$LIB_NAME is up-to-date."
else
    echo "$LIB_NAME will be updated"
    echo "$commit_local"
    echo "$commit_upstream"
    git clone $LIB_GIT_URL /tmp/$LIB_NAME
    rm -r ${GITHUB_WORKSPACE}/lib/${LIB_NAME}
    mv /tmp/${LIB_NAME}/${LIB_NAME} ${GITHUB_WORKSPACE}/lib/${LIB_NAME}
    echo -n $commit_upstream > $LIB_VERSION_FILE

    # commit here and push outside (one push for all changes, so the following build workflow will only be triggered once)
    git add lib/${LIB_NAME}
    git commit -m "[CI] auto updated lib/${LIB_NAME} to upstream commit $commit_upstream"

    echo "$LIB_NAME succesfully upgraded to upstream commit $commit_upstream and staged for push"
fi
