"""
Main entry point
Creates an instance of the ODM application
starts the interactive processing workflow
"""

from ODM.app import ODMApplication

if __name__ == "__main__":
    app = ODMApplication()
    app.execute()

#use below for input/output during testing
#C:\SplitTestImages
#C:\Users\ambri\OneDrive - University of Wisconsin - Platteville\Desktop\Drone Stuff\SplitTestOutput

#genreate ground truth polygons
#click and drag and find values within that block



#what we want for the patch we grab want the average from all of the ndvi's
