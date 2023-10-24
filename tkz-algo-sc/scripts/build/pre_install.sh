#!/bin/bash
PROFILE=$1
INSTLLATION_DIR=$2
BACKUP_PATH=$3

showHelp() {
    echo ""
    echo "Valid command is  "
    echo "    pre_install.sh PROFILE INSTLLATION_DIR BACKUP_PATH"
    echo "DESCRIPTION "
    echo " This installs build. "
    echo " PROFILE can be [dev | stg | prod] "
    echo " INSTLLATION_DIR is the directory where BCI Service is installed "
    echo " BACKUP_PATH is the directory where BCI Service is to be backed up "
}

validateInput() {
    if [ "$PROFILE" == "" ]; then
        echo "argument PROFILE type is missing".
        showHelp
        exit
    fi

    if [ "$INSTLLATION_DIR" == "" ]; then
        echo "argument INSTLLATION_DIR  is missing".
        showHelp
        exit
    fi

    if [ "$BACKUP_PATH" == "" ]; then
        echo "argument BACKUP_PATH  is missing".
        showHelp
        exit
    fi

}

printEnvironment() {
    echo "PROFILE TYPE: $PROFILE"
    echo "Installation directory is  $INSTLLATION_DIR"
    echo "Back up directory is $BACKUP_PATH"
}

createInstallDir() {
    echo "Creatating Install Dir if it does not exists"
    if [ -e $INSTLLATION_DIR ]
    then
        echo "Install dir exists"
    else
        echo "Install dir directory doesn't exists, so creating now"
        mkdir -p $INSTLLATION_DIR
    fi
}


backup() {
    mkdir -p $BACKUP_PATH
    backupTarFile=$BACKUP_PATH/bci-`date +%d%b%y-%H%M`.tar.gz

    echo "Taking the backup of $INSTLLATION_DIR"
    echo "Taking the backup to $BACKUP_PATH"

    if [ -d "ls -A $dir" ]
    then
        echo "Install directory is  empty, skipping the backup"
    else 
        #Take backup
        tar --exclude="$INSTLLATION_DIR/node_modules" -cvzf $backupTarFile $INSTLLATION_DIR
    fi
    
}


validateInput
createInstallDir
printEnvironment
backup
