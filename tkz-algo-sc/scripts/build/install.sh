#!/bin/bash

BUILD_DIR=`pwd`
PROFILE=$1
TAR_FILE=$2
INSTLLATION_DIR=$3
USER='tkzappuser'
USER_GROUP='tkzgrp'

showHelp() {
    echo ""
    echo "Valid command is  "
    echo "    install.sh PROFILE TAR_FILE"
    echo "DESCRIPTION "
    echo " This installs build. "
    echo " PROFILE can be [dev | stg | prod] "
    echo " TAR_FILE gz file name "
}

validateInput() {
    if [ "$PROFILE" == "" ]; then
        echo "argument PROFILE type is missing".
        showHelp
        exit
    fi

    if [ "$TAR_FILE" == "" ]; then
        echo "argument TAR_FILE  is missing".
        showHelp
        exit
    fi

}

printEnvironment() {
    echo "PROFILE TYPE: $PROFILE"
    echo "TAR FILE: $TAR_FILE"
    echo "Installation directory is  $INSTLLATION_DIR"
    echo "Build directory is $BUILD_DIR"
}

changeOwnerShip() {
    echo "changing the owner ship to tkzappuser:tkzgrp to $INSTLLATION_DIR"
    chown -R tkzappuser:tkzgrp -R $INSTLLATION_DIR
}

#This functions takes care of installing chitmonks  user portal
install() { 
    echo "Installation of portal started"
    INST_DIR=$INSTLLATION_DIR
    #backup existing application
    mkdir -p $INST_DIR
    #rm -rf $INST_DIR/* !(.env)
    cd $INST_DIR
    tar -xvzf $BUILD_DIR/$TAR_FILE
    #rm -r contracts_templates
    #mv contracts contracts_templates
    echo "Installation is done"
}

#stop the application before install
stop() {
    echo "There is nothing to stop. skipping."
}

#run the application() 
run() {
    echo 'switching to tkzappuser'
    su tkzappuser  -c "echo 'switched to tkzappuser'; cd $INST_DIR; npm i;"
}

checkUser() {
    if [ $(getent group $USER_GROUP) ]; then
        echo "group exists."
    else
        echo "group does not exist. Creating now"
        groupadd -f $USER_GROUP
    fi

    if id -u "$USER" >/dev/null 2>&1; then
        echo 'user exists'
    else
        echo 'user missing, so creating now' 
        useradd $USER
        usermod -a -G $USER_GROUP $USER
       
    fi
}

#check the status of the application

validateInput
printEnvironment
stop
install
changeOwnerShip
run

echo "Installation done."
exit 0
