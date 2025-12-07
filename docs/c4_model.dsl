workspace "Image Grid Viewer" "A C4 model for the Image Grid Viewer desktop application." {

    model {
        # People
        user = person "User" "A researcher or developer who needs to visually compare a set of images." "Person"

        # External Systems
        fileSystem = softwareSystem "File System" "The user's local file system." "External"

        # The System being described
        imageGridViewer = softwareSystem "Image Grid Viewer" "A lightweight desktop tool for displaying a synchronized grid of images." {
            
            # Container within the Image Grid Viewer
            desktopApp = container "Desktop Application" "The standalone GUI application." "Python, PySide6" {

                # Components within the Desktop Application
                cliHandler = component "CLI Handler" "Parses command-line arguments and starts the application." "Python" {
                    tags "Component"
                }
                mainWindow = component "Main Window" "The core GUI window. Manages the grid layout, menus, and status bar. Orchestrates other components." "Python, PySide6" {
                    tags "Component"
                }
                zoomableView = component "Zoomable View" "A custom widget that displays a single image and handles zoom, pan, and pixel inspection." "Python, PySide6" {
                    tags "Component"
                }
                suffixEditor = component "Suffix Editor" "A dialog for creating and editing the image suffix list file." "Python, PySide6" {
                    tags "Component"
                }
                exampleCreator = component "Example Creator" "A utility to generate a sample dataset on the file system." "Python" {
                    tags "Component"
                }
                config = component "Configuration" "Holds shared application settings and constants." "Python" {
                    tags "Component"
                }
            }
        }

        # -------------------------------------------------
        # Relationships
        # -------------------------------------------------

        # Level 1: Context Relationships
        user -> imageGridViewer "Uses" "Views and compares images"
        imageGridViewer -> fileSystem "Reads/Writes" "Image files, suffix lists"

        # Level 2: Container Relationships
        user -> desktopApp "Interacts with" "GUI"
        desktopApp -> fileSystem "Reads/Writes" "Image files, suffix lists"

        # Level 3: Component Relationships
        cliHandler -> mainWindow "Starts and passes arguments to"
        
        mainWindow -> config "Reads" "Settings"
        mainWindow -> zoomableView "Creates and manages a grid of"
        mainWindow -> suffixEditor "Opens"
        mainWindow -> exampleCreator "Triggers"
        mainWindow -> fileSystem "Reads" "Image files based on suffix list"

        suffixEditor -> fileSystem "Reads/Writes" "igridvu_suffix.txt"
        exampleCreator -> fileSystem "Writes" "Sample images and suffix file"
    }

    views {
        # -------------------------------------------------
        # Diagram Views
        # -------------------------------------------------

        systemContext imageGridViewer "SystemContext" "The system context diagram for the Image Grid Viewer." {
            include *
            autolayout lr
        }

        container imageGridViewer "Containers" "The container diagram for the Image Grid Viewer." {
            include *
            autolayout lr
        }

        component desktopApp "Components" "The component diagram for the Desktop Application." {
            include *
            autolayout lr
        }

        # -------------------------------------------------
        # Styling
        # -------------------------------------------------

        styles {
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "Person" {
                shape person
                background #08427b
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "External" {
                background #999999
                color #ffffff
            }
        }
    }
}
