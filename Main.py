"""
Main entry point
Creates an instance of the ODM application
starts the interactive processing workflow
"""

from ODM.app import ODMApplication

if __name__ == "__main__":
    app = ODMApplication()
    app.execute()

