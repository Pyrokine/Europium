#!/bin/bash

venv_folder=".venv"

# Function to create a virtual environment
create_venv() {
    if [ -d "$venv_folder" ]; then
        echo "Virtual environment already exists. Aborting creation."
    else
        echo "Creating virtual environment..."
        python3 -m venv "$venv_folder"
        echo "Virtual environment created successfully."
    fi
}

# Function to activate the virtual environment
activate_venv() {
    if [ -d "$venv_folder" ]; then
        source "$venv_folder/bin/activate"
        if [ $? -eq 0 ]; then
            echo "Virtual environment activated. Use 'deactivate' to exit."
        else
            echo "Failed to activate the virtual environment."
        fi
    else
        echo "Virtual environment does not exist. Use 'create' to create one."
    fi
}


# Function to deactivate the virtual environment
deactivate_venv() {
    deactivate
    echo "Virtual environment deactivated."
}

# Function to remove the virtual environment
remove_venv() {
    if [ -d "$venv_folder" ]; then
        echo "Removing virtual environment..."
        rm -rf "$venv_folder"
        echo "Virtual environment removed successfully."
    else
        echo "Virtual environment does not exist."
    fi
}

# Function to remove the virtual environment
install_venv() {
    activate_venv
    pip3 install -r ./requirements.txt
}

# Main script
venv() {
    case "$1" in
        "create"|"c")
            create_venv
            ;;
        "activate"|"a")
            activate_venv
            ;;
        "deactivate"|"d")
            deactivate_venv
            ;;
        "remove"|"r")
            remove_venv
            ;;
        "install"|"i")
            install_venv
            ;;
        *)
            echo "Usage: $0 {create|activate|deactivate|remove|install}"
            echo "Usage: $0 {c     |a       |d         |r     |i      }"
            return 1
            ;;
    esac
}
